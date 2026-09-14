from datetime import UTC, datetime

import httpx
from fastapi.testclient import TestClient
from test_models import features

from app.core.config import Settings
from app.db.connection import Database
from app.domain.odds import Bookmaker
from app.main import create_app
from app.providers.pulsescore.provider import PulseScoreProvider
from app.providers.transport import ProviderTransport
from app.providers.usage import ApiUsageTracker


async def test_provider_failure_returns_original_cached_timestamp_and_error():
    db = Database(":memory:")
    failing = False

    def handler(request):
        return httpx.Response(503 if failing else 200, json={"data": "old"})

    transport = ProviderTransport(
        "test",
        db,
        httpx.AsyncClient(base_url="https://test.local", transport=httpx.MockTransport(handler)),
        ApiUsageTracker(db, "test", 100),
        attempts=1,
    )
    await transport.request("GET", "/events", ttl=60)
    original = transport.last_response_at
    db.execute("UPDATE analysis_cache SET expires_at=current_timestamp - INTERVAL '1 second'")
    failing = True
    assert await transport.request("GET", "/events", ttl=60) == {"data": "old"}
    assert transport.last_stale and transport.last_response_at == original
    assert transport.status()["last_error"]
    await transport.close()
    db.close()


async def test_pulsescore_btts_raw_name_is_not_misclassified_as_team_total():
    db = Database(":memory:")
    provider = PulseScoreProvider(Settings(_env_file=None), db)
    event = provider.normalize(
        {
            "eventId": "x",
            "home": "A",
            "away": "B",
            "startTime": datetime.now(UTC).isoformat(),
            "markets": [
                {
                    "canonicalMarket": "BOTH_TEAMS_TO_SCORE",
                    "rawName": "Both Teams to Score",
                    "period": "FULL_TIME",
                    "isActive": True,
                    "selections": [{"canonicalOutcome": "YES", "isActive": True, "odds": 1.8}],
                }
            ],
        },
        Bookmaker.BET365,
        datetime.now(UTC),
    )
    assert len(event.odds) == 1 and event.odds[0].selection == "YES"
    assert provider.effective_interval(5) > 5
    await provider.transport.close()
    db.close()


def test_cross_site_mutations_rejected_and_secrets_not_returned():
    settings = Settings(
        _env_file=None,
        duckdb_path=":memory:",
        enable_scheduler=False,
        api_football_key="hidden-api-key",
    )
    with TestClient(create_app(settings)) as client:
        assert (
            client.post(
                "/api/learning/train", headers={"Origin": "https://untrusted.example"}
            ).status_code
            == 403
        )
        assert (
            client.post("/api/refresh", headers={"Origin": "https://untrusted.example"}).status_code
            == 403
        )
        data = (
            client.get("/api/settings").text
            + client.get("/api/providers/status").text
            + client.get("/api/learning/status").text
        )
        assert "hidden-api-key" not in data
        assert client.get("/api/learning/status").json()["historical_matches"] == 0


def test_manual_odds_do_not_change_football_probability_and_settlement_is_once():
    settings = Settings(_env_file=None, duckdb_path=":memory:", enable_scheduler=False)
    with TestClient(create_app(settings)) as client:
        r = client.app.state.runtime
        f = features()
        r.fixtures.save(f.fixture)
        r.stats.save_matches(f.home + f.away)
        before = r.prediction_service.calculate(f.fixture)
        body = {
            "fixture_id": f.fixture.fixture_id,
            "bookmaker": "BET365",
            "market": "OVER_2_5_GOALS",
            "line": 2.5,
            "odds": 1.9,
        }
        response = client.post("/api/odds/manual", json=body)
        assert response.status_code == 201, response.text
        after = r.prediction_service.calculate(f.fixture)
        assert before["goals"] == after["goals"]
        day = f.fixture.kickoff_utc.astimezone(settings.timezone).date()
        rows = r.dashboard.rows(day, r.user_settings.get())
        r.performance.record(rows)
        r.performance.record(rows)
        finished = f.fixture.model_copy(
            update={
                "status": "FINISHED",
                "home_goals": 2,
                "away_goals": 1,
                "home_corners": 5,
                "away_corners": 6,
            }
        )
        r.performance.settle(finished)
        r.performance.settle(finished)
        metrics = r.performance.metrics()
        over = next(m for m in metrics if m["market"] == "OVER_2_5_GOALS")
        assert over["number_predictions"] == over["settled_predictions"] == 1
        assert over["roi"] > 0
