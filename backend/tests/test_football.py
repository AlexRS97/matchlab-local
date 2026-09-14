from datetime import UTC, date, datetime

import httpx
import pytest

from app.core.config import Settings
from app.core.exceptions import QuotaExceeded
from app.db.connection import Database
from app.providers.api_football.normalization import normalize_fixture
from app.providers.api_football.provider import ApiFootballProvider
from app.providers.transport import ProviderTransport
from app.providers.usage import ApiUsageTracker
from app.repositories.fixture_repository import FixtureRepository


def raw_fixture(kickoff="2026-09-11T22:30:00+00:00"):
    return {
        "fixture": {"id": 1, "date": kickoff, "status": {"short": "NS"}},
        "league": {"id": 140, "name": "La Liga", "country": "Spain", "season": 2026},
        "teams": {"home": {"id": 1, "name": "Barcelona"}, "away": {"id": 2, "name": "Madrid"}},
        "goals": {"home": None, "away": None},
    }


def test_madrid_midnight_and_dst():
    db = Database(":memory:")
    repo = FixtureRepository(db)
    repo.save(normalize_fixture(raw_fixture(), datetime.now(UTC)))
    assert not repo.for_date(date(2026, 9, 11))
    assert len(repo.for_date(date(2026, 9, 12))) == 1
    repo.save(normalize_fixture(raw_fixture("2026-10-25T23:30:00+00:00"), datetime.now(UTC)))
    assert len(repo.for_date(date(2026, 10, 26))) == 1
    db.close()


async def test_fixtures_request_uses_timezone_and_cache():
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(200, json={"response": [raw_fixture()], "errors": []})

    db = Database(":memory:")
    client = httpx.AsyncClient(
        base_url="https://test.local", transport=httpx.MockTransport(respond)
    )
    provider = ApiFootballProvider(Settings(_env_file=None, api_football_key="test"), db, client)
    assert len(await provider.get_fixtures(date(2026, 9, 12))) == 1
    await provider.get_fixtures(date(2026, 9, 12))
    assert len(calls) == 1
    assert calls[0].url.params["timezone"] == "Europe/Madrid"
    await provider.transport.close()
    db.close()


async def test_429_persists_quota_and_circuit():
    db = Database(":memory:")
    client = httpx.AsyncClient(
        base_url="https://test.local",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(429, headers={"Retry-After": "120"})
        ),
    )
    tracker = ApiUsageTracker(db, "test", 100)
    transport = ProviderTransport("test", db, client, tracker)
    with pytest.raises(QuotaExceeded):
        await transport.request("GET", "/fixtures")
    assert tracker.status()["requests_today"] == 1
    assert transport.status()["circuit_until"] > datetime.now(UTC)
    assert ApiUsageTracker(db, "test", 100).status()["requests_remaining"] == 99
    await client.aclose()
    db.close()
