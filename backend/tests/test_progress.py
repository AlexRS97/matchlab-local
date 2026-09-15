import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import numpy as np
import pytest

from app.core.config import Settings, read_config
from app.db.connection import Database
from app.domain.market import Market
from app.jobs.progress import JobProgress
from app.learning.service import LearningService
from app.services.runtime import AnalyticsRuntime


def test_progress_waits_for_publication_and_keeps_failure_visible():
    job = {}
    tracker = JobProgress(job, [("data", "Datos"), ("save", "Guardar")])
    tracker.start("data")
    assert job["progress"]["indeterminate"]
    tracker.update(2, 4, "Dos archivos revisados")
    before = job["progress"]
    tracker.end()
    assert before["steps"][0]["status"] == "running"  # Published snapshots are immutable.
    tracker.start("save", 1)
    tracker.update(1)
    assert job["progress"]["percent"] < 100
    tracker.fail("No se pudo escribir")
    assert job["progress"]["percent"] < 100
    assert job["progress"]["steps"][-1]["status"] == "failed"


async def test_refresh_reports_missing_source_instead_of_success():
    db = Database(":memory:")
    runtime = AnalyticsRuntime(
        Settings(_env_file=None, duckdb_path=":memory:", enable_scheduler=False), db
    )
    runtime.start_refresh(datetime.now(UTC).date())
    await runtime.task
    assert runtime.job["progress"]["percent"] == 100  # All checks finished, with unavailable data.
    assert runtime.job["status"] == "partial"
    assert runtime.job["errors"]
    assert runtime.job["progress"]["steps"][0]["status"] == "warning"
    await runtime.close()
    db.close()


async def test_history_updates_without_training_and_exposes_intermediate_counts(
    tmp_path, monkeypatch
):
    db = Database(":memory:")
    service = LearningService(db, tmp_path)
    service.config["automatic_training"] = False
    entered, release = asyncio.Event(), asyncio.Event()

    async def update(leagues, seasons, progress, on_progress):
        on_progress(1, 4, "1/4 archivos")
        entered.set()
        await release.wait()
        on_progress(4, 4, "4/4 archivos")
        return {"errors": [], "stored_matches": 0}

    service.historical.update = update
    train = Mock()
    monkeypatch.setattr("app.learning.training.train", train)
    service.start()
    await entered.wait()
    assert service.job["running"] and service.job["progress"]["percent"] == 25
    release.set()
    await service.task
    assert service.job["status"] == "complete"
    assert service.job["progress"]["percent"] == 100
    train.assert_not_called()
    service.historical.update = AsyncMock(side_effect=RuntimeError("Descarga interrumpida"))
    service.start()
    await service.task
    assert service.job["status"] == "failed" and service.job["progress"]["percent"] < 100
    await service.close()
    db.close()


async def test_automatic_review_reuses_current_models_and_waits_for_new_analysis(
    tmp_path, monkeypatch
):
    from app.learning.training import TRAINING_PHASES

    db = Database(":memory:")
    service = LearningService(db, tmp_path)
    service.config["automatic_training"] = True
    report = {
        "created_at": datetime.now(UTC).isoformat(),
        "dataset": {"historical_matches": 2000, "source_revision": "old"},
        "models": {},
    }
    monkeypatch.setattr(service, "report", lambda: report)
    revision = "old"

    async def historical(*args):
        return {"errors": [], "stored_matches": 2000, "source_revision": revision}

    service.historical.update = historical
    trained = Mock()
    monkeypatch.setattr("app.learning.training.train", trained)
    await service.update()
    trained.assert_not_called()
    assert not service.job["models_updated"] and service.job["progress"]["percent"] == 100

    def train(db, directory, config, progress, tracker):
        for key, _ in TRAINING_PHASES:
            tracker.start(key)
            tracker.end()
        return report

    trained.side_effect = train
    entered, release = asyncio.Event(), asyncio.Event()

    async def apply_models(progress):
        entered.set()
        await release.wait()

    service.on_trained = apply_models
    revision = "corrected"
    service.start()
    await entered.wait()
    assert service.job["running"] and service.job["progress"]["percent"] < 100
    release.set()
    await service.task
    assert service.job["models_updated"] and service.job["progress"]["percent"] == 100
    trained.assert_called_once()
    await service.close()
    db.close()


def test_all_five_training_families_emit_progress_before_publishing(tmp_path, monkeypatch):
    pytest.importorskip("torch")
    from app.learning.training import TRAINING_PHASES, train

    db = Database(":memory:")
    service = LearningService(db, tmp_path)
    rng = np.random.default_rng(42)
    count = 1500

    def dataset(db, output, embargo, progress, on_progress):
        np.savez(
            output,
            x=rng.normal(size=(count, 8)).astype(np.float32),
            sequences=rng.normal(size=(count, 10, 4)).astype(np.float32),
            y=np.column_stack([rng.integers(0, n, count) for n in (7, 2, 21)]),
            dates=np.arange(count) * 86400,
            baseline=np.full((count, len(Market)), 0.5),
        )
        on_progress(count, count, "Muestra de prueba preparada")
        return {"rows": count, "historical_matches": count, "markets": [m.value for m in Market]}

    monkeypatch.setattr("app.learning.training.build_dataset", dataset)
    config = {**read_config("learning"), "trees": 3, "deep_epochs": 2, "threads": 1}
    snapshots = []
    job = {}
    tracker = JobProgress(job, TRAINING_PHASES)
    original = tracker.publish

    def publish():
        original()
        snapshots.append(job["progress"])

    tracker.publish = publish
    report = train(db, tmp_path, config, lambda _: None, tracker)
    assert all(m["status"] == "trained" for m in report["models"].values())
    assert len(report["provenance"]["code_sha256"]) == 64
    assert report["provenance"]["packages"]["torch"]
    percentages = [s["percent"] for s in snapshots]
    assert percentages == sorted(percentages) and percentages[-1] == 100
    assert any("época 1/2" in s["detail"] for s in snapshots)
    assert any("objetivo goals" in s["detail"] for s in snapshots)
    assert (tmp_path / "current.json").exists()
    assert service.report()["run_id"] == report["run_id"]
    service.temporary.cleanup()
    db.close()
