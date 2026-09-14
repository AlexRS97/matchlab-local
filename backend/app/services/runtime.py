import asyncio
import logging
from datetime import UTC, date, datetime

from app.core.config import Settings
from app.core.exceptions import ProviderError
from app.db.connection import Database, encode
from app.domain.odds import Bookmaker
from app.jobs.daily import DailyAnalysis
from app.jobs.pipeline import RefreshPipeline
from app.jobs.progress import JobProgress
from app.jobs.scheduler import Scheduler
from app.learning.service import LearningService
from app.providers.api_football.provider import ApiFootballProvider
from app.providers.betfair.provider import BetfairProvider
from app.providers.manual.provider import ManualOddsProvider
from app.providers.pulsescore.provider import PulseScoreProvider
from app.repositories.fixture_repository import FixtureRepository
from app.repositories.odds_repository import OddsRepository
from app.repositories.predictions_repository import PredictionsRepository
from app.repositories.stats_repository import StatsRepository
from app.services.dashboard_service import DashboardService
from app.services.fixture_matcher import FixtureMatcher
from app.services.fixture_service import FixtureService
from app.services.odds_refresh_service import OddsRefreshService
from app.services.odds_service import OddsService
from app.services.performance_service import PerformanceService
from app.services.prediction_service import PredictionService
from app.services.settings_service import SettingsService
from app.services.team_stats_service import TeamStatsService

log = logging.getLogger("matchlab")


class AnalyticsRuntime:
    def __init__(self, settings: Settings, db: Database):
        self.settings, self.db = settings, db
        self.football = ApiFootballProvider(settings, db)
        self.fixtures = FixtureRepository(db, settings.app_timezone)
        self.stats = StatsRepository(db)
        self.predictions = PredictionsRepository(db)
        self.learning = LearningService(db)
        self.prediction_service = PredictionService(self.stats, self.predictions, self.learning)
        self.user_settings = SettingsService(db, settings)
        self.matcher = FixtureMatcher(db)
        self.odds = OddsRepository(db)
        self.odds_service = OddsService(self.odds)
        self.dashboard = DashboardService(
            self.fixtures, self.predictions, self.odds_service, settings
        )
        self.betfair = BetfairProvider(settings, db)
        self.pulsescore = PulseScoreProvider(settings, db)
        self.manual = ManualOddsProvider(self.odds, self.fixtures)
        self.odds_refresh = OddsRefreshService(
            self.betfair, self.pulsescore, self.odds, self.matcher
        )
        self.fixture_service = FixtureService(self.football, self.fixtures)
        self.team_service = TeamStatsService(self.football, self.stats)
        self.performance = PerformanceService(db)
        self.pipeline = RefreshPipeline(self)
        self.daily = DailyAnalysis(db, settings.timezone)
        self.scheduler = Scheduler(self)
        self.refresh_lock = asyncio.Lock()
        self.task: asyncio.Task | None = None
        self.pending_refresh: dict[date, bool] = {}
        self.requested_dates: dict[date, datetime] = {}
        self.job: dict = {"running": False, "errors": [], "completed": 0, "total": 0}
        self.progress: JobProgress | None = None
        self.odds_job: dict = {"running": False, "errors": [], "kind": "odds"}

    def start_refresh(self, target: date, force_analysis: bool = False) -> dict:
        if self.task and not self.task.done():
            if target.isoformat() != self.job.get("date") or (
                force_analysis and not self.job.get("force_analysis")
            ):
                self.pending_refresh[target] = force_analysis or self.pending_refresh.get(
                    target, False
                )
            return self.job
        now = datetime.now(UTC)
        daily_due = target == now.astimezone(self.settings.timezone).date() and self.daily.due(now)
        self.job = {
            "running": True,
            "date": target.isoformat(),
            "errors": [],
            "completed": 0,
            "total": 0,
            "started_at": now.isoformat(),
            "force_analysis": force_analysis or daily_due,
            "status": "running",
            "kind": "fixtures",
        }
        self.progress = JobProgress(
            self.job,
            [
                ("fixtures", "Partidos de la jornada"),
                ("form", "Forma reciente"),
                ("standings", "Clasificación y ligas"),
                ("stats", "Tiros, xG y córners"),
                ("context", "H2H y contexto"),
                ("models", "Probabilidades y análisis"),
                ("odds", "Cuotas de las casas"),
                ("results", "Resultados y rankings"),
            ],
        )
        self.requested_dates[target] = datetime.now(UTC)
        self.task = asyncio.create_task(self.refresh(target))
        self.task.add_done_callback(self._next_refresh)
        return self.job

    def _next_refresh(self, task):
        if self.pending_refresh and not task.cancelled():
            target = next(iter(self.pending_refresh))
            self.start_refresh(target, self.pending_refresh.pop(target))

    async def refresh(self, target: date):
        try:
            async with self.refresh_lock:
                await self.pipeline.run(target)
                self.job["status"] = "partial" if self.job["errors"] else "complete"
        except asyncio.CancelledError:
            self.job["status"] = "cancelled"
            self.job["errors"].append("Actualización interrumpida al cerrar la aplicación")
            raise
        except ProviderError as exc:
            self.job["status"] = "failed"
            self.job["errors"].append(str(exc))
        except Exception as exc:
            self.job["status"] = "failed"
            self.job["errors"].append(f"Error interno de actualización: {type(exc).__name__}")
            log.error("refresh_failed", extra={"error": type(exc).__name__})
        finally:
            if self.progress and self.job["status"] in {"failed", "cancelled"}:
                self.progress.fail(self.job["errors"][-1])
            self.job["running"] = False
            self.job["errors"] = list(dict.fromkeys(self.job["errors"]))
            self.job["finished_at"] = datetime.now(UTC).isoformat()
            self.db.execute(
                "INSERT OR REPLACE INTO settings VALUES ('last_refresh', ?)", [encode(self.job)]
            )
            if target == datetime.now(self.settings.timezone).date():
                fixtures = self.fixtures.for_date(target)
                analysed = sum(
                    bool(
                        (self.predictions.latest(f.fixture_id, before=f.kickoff_utc) or {})
                        .get("goals", {})
                        .get("probabilities")
                    )
                    for f in fixtures
                )
                self.daily.record(self.job, len(fixtures), analysed)

    async def refresh_odds(self, target: date, provider: str):
        self.odds_job = {
            "running": True,
            "status": "running",
            "errors": [],
            "kind": "odds",
            "started_at": datetime.now(UTC).isoformat(),
        }
        progress = JobProgress(self.odds_job, [("odds", f"Actualizar {provider}")])
        progress.start("odds", detail=f"Consultando {provider}")
        try:
            async with self.refresh_lock:
                errors = await self.odds_refresh.refresh(
                    target,
                    self.fixtures.for_date(target),
                    self.user_settings.get(),
                    only=provider,
                    progress=progress,
                )
                self.odds_job["errors"] = errors
                self.job["errors"] = list(dict.fromkeys(self.job["errors"] + errors))
            progress.end(" · ".join(errors))
            self.odds_job["status"] = "partial" if errors else "complete"
        except asyncio.CancelledError:
            self.odds_job["status"] = "cancelled"
            progress.fail("Interrumpido al cerrar MatchLab")
            raise
        except Exception as exc:
            self.odds_job["status"] = "failed"
            self.odds_job["errors"] = [f"Actualización interrumpida: {type(exc).__name__}"]
            progress.fail(self.odds_job["errors"][0])
            raise
        finally:
            self.odds_job["running"] = False
            self.odds_job["finished_at"] = datetime.now(UTC).isoformat()

    async def close(self):
        self.pending_refresh.clear()
        await self.scheduler.close()
        await self.learning.close()
        if self.task and not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        await self.football.transport.close()
        await self.betfair.transport.close()
        await self.betfair.session.close()
        await self.pulsescore.transport.close()

    def bookmaker_status(self):
        minutes = self.user_settings.get().odds_stale_minutes
        return [
            {
                "bookmaker": book.value,
                "available_prices": self.db.query(
                    "SELECT count(DISTINCT fixture_id) AS n FROM odds_snapshots WHERE bookmaker=? AND timestamp>current_timestamp - ? * INTERVAL '1 minute'",
                    [book.value, minutes],
                )[0]["n"],
            }
            for book in Bookmaker
        ]
