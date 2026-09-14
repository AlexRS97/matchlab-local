from datetime import UTC, datetime, timedelta

from app.domain.market import Market
from app.domain.settings import UserSettings
from app.services.ranking_service import RankingService


def row(fixture_id, probability, odds, ev):
    quote = {"decimal_odds": odds, "stale": False, "edge": 0.1, "ev": ev}
    return {
        "fixture_id": fixture_id,
        "status": "NOT_STARTED",
        "kickoff_utc": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        "country": "Spain",
        "league_id": 140,
        "prediction": {
            "goals": {"probabilities": {"OVER_2_5_GOALS": probability}},
            "quality": {"score": 80},
            "confidence": {"OVER_2_5_GOALS": {"score": 80}},
        },
        "markets": {
            "OVER_2_5_GOALS": {
                "best": quote,
                "quotes": {"BET365": quote, "BETFAIR": None, "WINAMAX": None},
            }
        },
    }


def test_rank_probability_then_confidence_not_ev():
    rows = [row(1, 0.72, 1.5, 0.08), row(2, 0.7, 3, 1.1), row(3, 0.9, 1.2, 0.08)]
    service = RankingService()
    result = service.rank(rows, Market.OVER_2_5_GOALS, UserSettings())
    assert [r["fixture"]["fixture_id"] for r in result] == [1, 2]
    assert service.rank(rows, Market.OVER_2_5_GOALS, UserSettings(), bookmaker="BETFAIR") == []
    rows[0]["status"] = "LIVE"
    assert [
        r["fixture"]["fixture_id"]
        for r in service.rank(rows, Market.OVER_2_5_GOALS, UserSettings())
    ] == [2]
