from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from test_models import features

from app.core.config import Settings
from app.db.connection import Database
from app.domain.market import Market
from app.domain.odds import Bookmaker, NormalizedOdds
from app.jobs.daily import DailyAnalysis
from app.repositories.odds_repository import OddsRepository
from app.services.runtime import AnalyticsRuntime


def test_daily_schedule_rollover_and_dst_are_madrid_based():
    db = Database(":memory:")
    service = DailyAnalysis(db, ZoneInfo("Europe/Madrid"))
    early = datetime(2026, 10, 25, 4, 30, tzinfo=UTC)  # 05:30 after the DST switch
    assert not service.due(early)
    assert service.status(early)["next_scheduled_at"] == "2026-10-25T06:00:00+01:00"
    now = early + timedelta(hours=1)
    assert service.due(now)
    service.record(
        {
            "date": "2026-10-25",
            "started_at": now.isoformat(),
            "finished_at": now.isoformat(),
            "errors": [],
        },
        5,
        4,
    )
    assert not service.due(now)
    assert service.due(now + timedelta(days=1))
    db.close()


def test_before_daily_hour_does_not_mark_morning_cycle_complete():
    db = Database(":memory:")
    service = DailyAnalysis(db, ZoneInfo("Europe/Madrid"))
    early = datetime(2026, 9, 14, 0, tzinfo=UTC)
    service.record(
        {
            "date": "2026-09-14",
            "started_at": early.isoformat(),
            "finished_at": early.isoformat(),
            "errors": [],
        },
        2,
        2,
    )
    assert service.last() is None
    assert service.due(early + timedelta(hours=5))
    db.close()


async def test_daily_refresh_recalculates_and_records_status():
    db = Database(":memory:")
    settings = Settings(_env_file=None, duckdb_path=":memory:", enable_scheduler=False)
    runtime = AnalyticsRuntime(settings, db)
    f = features()
    # Use a fixed later pre-match time so this integration test also works near midnight.
    runtime.fixtures.save(f.fixture)
    runtime.stats.save_matches(f.home + f.away)
    first = runtime.prediction_service.calculate(f.fixture)
    later = datetime.now(UTC) + timedelta(seconds=1)
    second = runtime.prediction_service.calculate(f.fixture, now=later, force=True)
    assert second["timestamp"] != first["timestamp"]
    assert second["goals"]["probabilities"] == first["goals"]["probabilities"]
    await runtime.close()
    db.close()


async def test_new_models_recalculate_journey_without_rewriting_first_forecast(monkeypatch):
    import asyncio

    db = Database(":memory:")
    runtime = AnalyticsRuntime(
        Settings(_env_file=None, duckdb_path=":memory:", enable_scheduler=False), db
    )
    f = features()
    runtime.fixtures.save(f.fixture)
    runtime.stats.save_matches(f.home + f.away)
    # Keep the test independent of whether the fixture falls past local midnight.
    monkeypatch.setattr(runtime.fixtures, "for_date", lambda _: [f.fixture])
    today = datetime.now(runtime.settings.timezone).date()
    first = runtime.prediction_service.calculate(f.fixture)
    runtime.performance.record(runtime.dashboard.rows(today, runtime.user_settings.get()))
    original = db.query("SELECT * FROM prediction_results ORDER BY market")
    assert original
    progress = []
    async with runtime.refresh_lock:
        task = asyncio.create_task(runtime.reanalyse_after_training(lambda *x: progress.append(x)))
        await asyncio.sleep(0)
        assert not task.done() and not progress
    await task
    latest = runtime.predictions.latest(f.fixture.fixture_id)
    assert latest["timestamp"] > first["timestamp"]
    assert progress[0][:2] == (1, 1)
    assert db.query("SELECT * FROM prediction_results ORDER BY market") == original
    assert db.query("SELECT * FROM daily_rankings WHERE date=?", [today])
    await runtime.close()
    db.close()


async def test_daily_request_is_queued_if_another_date_is_running():
    import asyncio

    db = Database(":memory:")
    runtime = AnalyticsRuntime(
        Settings(_env_file=None, duckdb_path=":memory:", enable_scheduler=False), db
    )
    entered = asyncio.Event()
    release = asyncio.Event()
    calls = []

    async def pipeline(target):
        calls.append(target)
        if len(calls) == 1:
            entered.set()
            await release.wait()

    runtime.pipeline.run = pipeline
    today = datetime.now(runtime.settings.timezone).date()
    runtime.start_refresh(today + timedelta(days=1))
    await entered.wait()
    runtime.start_refresh(today, force_analysis=True)
    assert today in runtime.pending_refresh
    release.set()
    await runtime.task
    await asyncio.sleep(0)
    if runtime.task:
        await runtime.task
    assert calls == [today + timedelta(days=1), today]
    assert runtime.daily.last()["date"] == str(today)
    await runtime.close()
    db.close()


def test_suspended_selection_is_removed_without_deleting_price_history():
    db = Database(":memory:")
    repo = OddsRepository(db)
    now = datetime.now(UTC)
    price = NormalizedOdds(
        fixture_id=1,
        provider="pulsescore",
        bookmaker=Bookmaker.BET365,
        provider_event_id="1",
        market=Market.OVER_2_5_GOALS,
        line=2.5,
        selection="OVER",
        decimal_odds=1.6,
        timestamp=now - timedelta(minutes=2),
    )
    repo.save([price])
    repo.save_board(1, "pulsescore", "BET365", now - timedelta(minutes=1), [price])
    assert len(repo.current(1)) == 1
    repo.save_board(1, "pulsescore", "BET365", now, [])
    assert repo.current(1) == [] and len(repo.history(1)) == 1
    assert len(repo.current(1, before=now - timedelta(seconds=30))) == 1
    db.close()
