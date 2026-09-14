from datetime import UTC, datetime, timedelta

import pytest
from test_models import features

from app.db.connection import Database
from app.domain.market import Market
from app.domain.odds import Bookmaker, NormalizedOdds, ProviderEvent
from app.repositories.odds_repository import OddsRepository
from app.services.fixture_matcher import FixtureMatcher
from app.services.odds_math import devig, expected_value, fair_odds, implied_probability
from app.services.odds_service import OddsService


def quote(book=Bookmaker.BET365, odds=1.55, **kwargs):
    return NormalizedOdds(
        provider="pulsescore",
        bookmaker=book,
        fixture_id=1,
        provider_event_id="a",
        market=Market.OVER_2_5_GOALS,
        line=2.5,
        selection="OVER",
        decimal_odds=odds,
        timestamp=datetime.now(UTC),
        **kwargs,
    )


def test_math():
    assert fair_odds(0.72) == pytest.approx(1.3888888889)
    assert fair_odds(None) is None
    assert implied_probability(2) == 0.5
    assert sum(devig(1.9, 1.9)) == 1
    assert expected_value(0.72, 1.55) == pytest.approx(0.116)


def test_best_missing_stale_and_devig():
    db = Database(":memory:")
    repository = OddsRepository(db)
    first = quote()
    under = first.model_copy(update={"selection": "UNDER", "decimal_odds": 2.5})
    stale = quote(Bookmaker.WINAMAX, 2).model_copy(
        update={"timestamp": datetime.now(UTC) - timedelta(hours=1)}
    )
    repository.save([first, under, stale])
    result = OddsService(repository).compare(1, Market.OVER_2_5_GOALS, 0.72)
    assert result["best_bookmaker"] == "BET365"
    assert result["quotes"]["BETFAIR"] is None
    assert result["quotes"]["BET365"]["devig_status"] == "DEVIGGED"
    assert result["quotes"]["WINAMAX"]["stale"]
    assert result["quotes"]["WINAMAX"]["devig_status"] == "NOT_DEVIGGED"
    repository.save(
        [first.model_copy(update={"decimal_odds": 1.7, "timestamp": datetime.now(UTC)})]
    )
    assert len(repository.history(1)) == 4
    db.close()


def test_matching_aliases_time_competition_and_ambiguity():
    db = Database(":memory:")
    matcher = FixtureMatcher(db)
    fixture = features().fixture.model_copy(
        update={
            "home_team": "Paris Saint-Germain",
            "away_team": "Manchester United",
            "league_name": "Champions League",
        }
    )
    event = ProviderEvent(
        provider="pulsescore",
        bookmaker=Bookmaker.BET365,
        provider_event_id="a",
        home_team="PSG",
        away_team="Man Utd",
        competition="UEFA Champions League",
        kickoff_utc=fixture.kickoff_utc,
    )
    assert matcher.match(event, [fixture]).fixture_id == fixture.fixture_id
    assert matcher.search("PSG", fixture)
    assert (
        matcher.match(
            event.model_copy(update={"kickoff_utc": fixture.kickoff_utc + timedelta(hours=3)}),
            [fixture],
        ).fixture_id
        is None
    )
    assert (
        matcher.match(event, [fixture, fixture.model_copy(update={"fixture_id": 2})]).fixture_id
        is None
    )
    assert (
        matcher.match(event.model_copy(update={"home_team": "PSG Women"}), [fixture]).fixture_id
        is None
    )
    assert (
        matcher.match(event.model_copy(update={"competition": "Friendly"}), [fixture]).fixture_id
        is None
    )
    db.close()
