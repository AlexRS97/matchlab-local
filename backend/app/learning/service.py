import asyncio
import hashlib
import json
import logging
import tempfile
import threading
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np

from app.core.config import read_config
from app.core.resources import resolve_threads
from app.db.connection import Database, encode
from app.jobs.progress import JobProgress
from app.learning.features import Preprocessor, sequences, vectorize
from app.providers.football_data.provider import LEAGUES, FootballDataProvider

log = logging.getLogger("matchlab")


class LearningService:
    def __init__(self, db: Database, directory: Path | None = None):
        self.db, self.config = db, read_config("learning")
        self.config["threads"] = resolve_threads(self.config.get("threads"))
        self.temporary = (
            tempfile.TemporaryDirectory(prefix="matchlab-test-") if db.path == ":memory:" else None
        )
        root = Path(self.temporary.name) if self.temporary else Path(db.path).resolve().parent
        self.directory = directory or root / "models"
        self.historical = FootballDataProvider(db, root / "historical")
        self.task: asyncio.Task | None = None
        self.job: dict = {"running": False, "phase": "idle", "errors": []}
        self.lock = threading.RLock()
        self.loaded_id: str | None = None
        self.loaded: dict = {}
        self.tracker: JobProgress | None = None
        self.inference_cache: OrderedDict[str, dict] = OrderedDict()
        self.report_cache: tuple | None = None
        self.on_trained: Callable[[Callable[..., None]], Awaitable[None]] | None = None

    def training_due(self, report, count, revision, now=None) -> bool:
        now = now or datetime.now(UTC)
        if report is None:
            return True
        age = now - datetime.fromisoformat(report["created_at"])
        trained_revision = report["dataset"].get("source_revision")
        return (
            age >= timedelta(days=self.config["maximum_model_age_days"])
            or bool(revision and trained_revision and revision != trained_revision)
            or (
                age >= timedelta(days=self.config["retrain_days"])
                and count - report["dataset"]["historical_matches"]
                >= self.config["minimum_new_samples"]
            )
        )

    def report(self) -> dict | None:
        pointer = self.directory / "current.json"
        if not pointer.exists():
            return None
        signature = (pointer.stat().st_mtime_ns, pointer.stat().st_size)
        if self.report_cache and self.report_cache[0] == signature:
            return self.report_cache[1]
        run_id = json.loads(pointer.read_text(encoding="utf-8"))["run_id"]
        if len(run_id) != 32 or any(c not in "0123456789abcdef" for c in run_id):
            raise ValueError("Identificador de modelo inválido")
        report = json.loads((self.directory / run_id / "report.json").read_text(encoding="utf-8"))
        # Published runs are immutable. The atomic pointer is the cache invalidation boundary.
        self.report_cache = (signature, report)
        return report

    def status(self):
        last = self.db.query("SELECT payload FROM settings WHERE key='learning_update'")
        report = self.report()
        count = self.db.query("SELECT count(*) AS n FROM historical_matches")[0]["n"]
        age = (
            (datetime.now(UTC) - datetime.fromisoformat(report["created_at"])).days
            if report
            else None
        )
        new = max(0, count - report["dataset"]["historical_matches"]) if report else count
        revision = self.historical.repository.revision()
        trained_revision = report["dataset"].get("source_revision") if report else None
        changed = revision != trained_revision if revision and trained_revision else None
        return {
            "config": self.config,
            "job": self.job,
            "report": report,
            "historical_matches": count,
            "data_health": {
                "coverage": self.historical.repository.coverage(),
                "new_matches": new,
                "model_age_days": age,
                "source_revision": revision,
                "data_changed": changed,
                "training_recommended": self.training_due(report, count, revision),
                "provenance_available": bool(report and report.get("provenance")),
            },
            "last_update": json.loads(last[0]["payload"]) if last else None,
        }

    def progress(self, message):
        self.job["phase"] = message
        log.info("learning_progress", extra={"phase": message})

    def start(self, force_train=False):
        if self.task and not self.task.done():
            return self.job
        self.prepare_job(force_train)
        self.task = asyncio.create_task(self.update(force_train))
        return self.job

    def prepare_job(self, force_train=False):
        self.job = {
            "running": True,
            "status": "running",
            "phase": "Actualizando histórico",
            "errors": [],
            "kind": "training" if force_train else "history",
            "started_at": datetime.now(UTC).isoformat(),
        }
        phases = [("history", "Actualizar datos históricos")]
        if force_train or self.config["automatic_training"]:
            from app.learning.training import TRAINING_PHASES

            phases += TRAINING_PHASES
            if self.on_trained:
                phases += [("analysis", "Aplicar los modelos a la jornada")]
        self.tracker = JobProgress(self.job, phases)

    async def update(self, force_train=False):
        if not self.job["running"]:
            self.prepare_job(force_train)
        tracker = self.tracker
        assert tracker is not None
        try:
            seasons = list(self.config["seasons"])
            now = datetime.now(UTC)
            start_year = now.year if now.month >= 7 else now.year - 1
            current = f"{start_year % 100:02d}{(start_year + 1) % 100:02d}"
            if current not in seasons:
                seasons.append(current)
            tracker.start("history")
            update = await self.historical.update(
                self.config["leagues"], seasons, self.progress, tracker.update
            )
            self.job["errors"] = update["errors"]
            tracker.end("Algunas fuentes no están disponibles" if update["errors"] else "")
            self.db.execute(
                "INSERT OR REPLACE INTO settings VALUES ('learning_update',?)",
                [encode({**update, "timestamp": now.isoformat()})],
            )
            report = self.report()
            due = self.training_due(
                report, update["stored_matches"], update.get("source_revision"), now
            )
            if force_train or (due and self.config["automatic_training"]):
                from app.learning.training import train

                self.job["kind"] = "training"
                report = await asyncio.to_thread(
                    train, self.db, self.directory, self.config, self.progress, tracker
                )
                self.job["errors"].extend(
                    f"{name}: {model['error']}"
                    for name, model in report["models"].items()
                    if model["status"] == "failed"
                )
                self.job["models_updated"] = True
                if self.on_trained:
                    tracker.start("analysis", detail="Recalculando con la versión recién guardada")
                    await self.on_trained(tracker.update)
                    tracker.end()
            else:
                self.job["models_updated"] = False
                for step in tracker.steps:
                    if step["status"] == "pending":
                        step["label"] = {
                            "dataset": "Histórico comprobado",
                            "evaluation": "Evaluación guardada vigente",
                            "publish": "Versión guardada vigente",
                            "analysis": "Análisis con la versión vigente",
                        }.get(step["key"], f"Modelo {step['key'].upper()} vigente")
                        tracker.start(
                            step["key"],
                            detail="No corresponde reentrenar; se conserva el modelo actual",
                        )
                        tracker.end()
            self.job["status"] = "partial" if self.job["errors"] else "complete"
            self.progress("Actualización completada")
        except Exception as exc:
            self.job["status"] = "failed"
            self.job["errors"].append(f"{type(exc).__name__}: {str(exc)[:300]}")
            tracker.fail(self.job["errors"][-1])
            self.progress("Actualización con errores; revisa los avisos")
            log.exception("learning_failed")
        finally:
            self.job["running"] = False
            self.job["finished_at"] = datetime.now(UTC).isoformat()

    def daily_tick(self, now: datetime, timezone):
        if not self.config["enabled"] or (self.task and not self.task.done()):
            return
        local = now.astimezone(timezone)
        if local.hour < self.config["daily_update_hour"]:
            return
        if self.job.get("finished_at") and now - datetime.fromisoformat(
            self.job["finished_at"]
        ) < timedelta(hours=1):
            return
        last = self.db.query("SELECT payload FROM settings WHERE key='learning_update'")
        if (
            last
            and datetime.fromisoformat(json.loads(last[0]["payload"])["timestamp"])
            .astimezone(timezone)
            .date()
            >= local.date()
        ):
            return
        self.start()

    def predict(self, features) -> dict:
        report = self.report()
        unavailable = {
            "status": "unavailable",
            "reason": "Todavía no hay modelos entrenados",
            "models": {},
        }
        if not report or not self.config["enabled"]:
            return unavailable
        now = datetime.now(UTC)
        created = datetime.fromisoformat(report["created_at"])
        if created >= features.fixture.kickoff_utc or now - created > timedelta(
            days=self.config["maximum_model_age_days"]
        ):
            return {**unavailable, "reason": "Modelo posterior al partido o caducado"}
        leagues = [LEAGUES[code][0] for code in report["config"]["leagues"]]
        if (
            features.fixture.league_id not in leagues
            or min(len(features.home), len(features.away)) < 5
        ):
            return {**unavailable, "reason": "Liga o muestra fuera de la cobertura entrenada"}
        league = str(features.fixture.league_id)
        statistical = report.get("league_statistics", {}).get(league, {})
        unavailable = {
            **unavailable,
            "run_id": report["run_id"],
            "statistical_selection": statistical,
        }
        raw = vectorize(features)
        if (~np.isfinite(raw)).mean() > 0.15:
            return {
                **unavailable,
                "reason": "Faltan demasiadas estadísticas para la cobertura entrenada",
            }
        from app.learning.evaluation import market_probabilities
        from app.learning.trees import TreeModels

        raw_sequence = sequences(features)
        cache_key = (
            report["run_id"]
            + ":"
            + league
            + ":"
            + hashlib.sha256(raw.tobytes() + raw_sequence.tobytes()).hexdigest()
        )
        with self.lock:
            if cache_key in self.inference_cache:
                self.inference_cache.move_to_end(cache_key)
                return deepcopy(self.inference_cache[cache_key])
            if self.loaded_id != report["run_id"]:
                directory = self.directory / report["run_id"]
                state = json.loads((directory / "preprocessor.json").read_text(encoding="utf-8"))
                self.prep = Preprocessor(**state["static"])
                self.seq_prep = Preprocessor(**state["sequence"])
                loaded = {}
                for family, metadata in report["models"].items():
                    if metadata["status"] != "trained":
                        continue
                    if family in ("mlp", "gru"):
                        from app.learning.deep import DeepModel

                        loaded[family] = DeepModel.load(family, directory / family)
                    else:
                        loaded[family] = TreeModels.load(family, directory / family)
                self.loaded, self.loaded_id = loaded, report["run_id"]
                self.inference_cache.clear()
            x = self.prep.transform(raw[None, :])
            seq = self.seq_prep.transform(raw_sequence[None, :, :])
            predictions = {
                family: {
                    market: float(p[0])
                    for market, p in market_probabilities(
                        model.predict(x, seq), report["models"][family]["temperatures"]
                    ).items()
                }
                for family, model in self.loaded.items()
            }
            result = {
                "status": "available",
                "run_id": report["run_id"],
                "models": predictions,
                "champions": {
                    **report["champions"],
                    **report.get("league_champions", {}).get(league, {}),
                },
                "statistical_selection": statistical,
                "trained_at": report["created_at"],
            }
            self.inference_cache[cache_key] = deepcopy(result)
            if len(self.inference_cache) > 512:
                self.inference_cache.popitem(last=False)
            return result

    async def close(self):
        if self.task and not self.task.done():
            # Do not close DuckDB while a training thread is still using it.
            await self.task
        if self.temporary:
            self.temporary.cleanup()
