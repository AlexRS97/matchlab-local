from datetime import UTC, datetime

import httpx
import pytest

from app.core.config import Settings
from app.core.exceptions import ProviderError
from app.db.connection import Database
from app.domain.odds import Bookmaker, ProviderEvent
from app.providers.betfair.provider import BetfairProvider
from app.providers.betfair.session import BetfairSession
from app.providers.pulsescore.provider import PulseScoreProvider


async def test_pulsescore_documented_schema_and_pagination():
    now = datetime.now(UTC)
    requests = []

    def respond(request):
        requests.append(request)
        page = int(request.url.params.get("page", "1"))
        return httpx.Response(
            200,
            json={
                "hasNextPage": page == 1,
                "events": [
                    {
                        "eventId": str(page),
                        "home": "PSG",
                        "away": "Lyon",
                        "league": "Ligue 1",
                        "startTime": now.isoformat(),
                        "live": False,
                        "markets": [
                            {
                                "canonicalMarket": "OVER_UNDER",
                                "period": "FULL_TIME",
                                "isActive": True,
                                "selections": [
                                    {
                                        "canonicalOutcome": "OVER",
                                        "line": 2.5,
                                        "odds": 1.8,
                                        "isActive": True,
                                    },
                                    {
                                        "canonicalOutcome": "UNDER",
                                        "line": 2.5,
                                        "odds": 2.0,
                                        "isActive": True,
                                    },
                                    {
                                        "canonicalOutcome": "OVER",
                                        "line": 3.5,
                                        "odds": 3.0,
                                        "isActive": False,
                                    },
                                ],
                            }
                        ],
                    }
                ],
            },
        )

    db = Database(":memory:")
    provider = PulseScoreProvider(
        Settings(_env_file=None, pulsescore_api_key="test"),
        db,
        httpx.AsyncClient(base_url="https://test.local", transport=httpx.MockTransport(respond)),
    )
    provider.enabled_bookmakers = {Bookmaker.BET365}
    provider.transport.min_interval = 0
    events = await provider.get_events(now.astimezone(provider.settings.timezone).date())
    assert len(events) == 2
    assert len(events[0].odds) == 2
    assert requests[0].url.path == "/api/v3/bet365/events"
    assert provider.transport.usage.status()["requests_today"] == 2
    await provider.transport.close()
    db.close()


def test_betfair_back_lay_and_suspended():
    now = datetime.now(UTC)
    event = ProviderEvent(
        provider="betfair",
        bookmaker=Bookmaker.BETFAIR,
        provider_event_id="1",
        home_team="A",
        away_team="B",
        competition="C",
        kickoff_utc=now,
    )
    catalogue = {
        "description": {"marketType": "OVER_UNDER_25"},
        "marketName": "Over/Under 2.5 Goals",
        "runners": [{"selectionId": 1, "runnerName": "Over 2.5 Goals"}],
    }
    book = {
        "status": "OPEN",
        "inplay": False,
        "isMarketDataDelayed": True,
        "runners": [
            {
                "selectionId": 1,
                "status": "ACTIVE",
                "ex": {
                    "availableToBack": [{"price": 1.6, "size": 5}],
                    "availableToLay": [{"price": 1.62, "size": 4}],
                },
            }
        ],
    }
    odds = BetfairProvider.normalize_market(catalogue, book, event, now)[0]
    assert odds.decimal_odds == odds.best_back_price == 1.6
    assert odds.best_lay_price == 1.62
    assert odds.is_delayed
    assert (
        BetfairProvider.normalize_market(catalogue, {**book, "status": "SUSPENDED"}, event, now)
        == []
    )


async def test_betfair_session_and_read_allowlist():
    requests = []

    def login(request):
        requests.append(request)
        return httpx.Response(200, json={"status": "SUCCESS", "token": "session-secret"})

    settings = Settings(
        _env_file=None,
        betfair_app_key="app-secret",
        betfair_username="user",
        betfair_password="pass",
        betfair_identity_domain="betfair.es",
    )
    session = BetfairSession(settings, httpx.AsyncClient(transport=httpx.MockTransport(login)))
    headers = await session.headers()
    assert headers["X-Authentication"] == "session-secret"
    assert requests[0].url.host == "identitysso.betfair.es"
    assert len(requests) == 1
    await session.headers()
    assert len(requests) == 1
    db = Database(":memory:")
    provider = BetfairProvider(settings, db, session=session)
    with pytest.raises(ProviderError, match="solo lectura"):
        await provider.rpc("unknown-operation", {})
    await provider.transport.close()
    await session.close()
    db.close()
