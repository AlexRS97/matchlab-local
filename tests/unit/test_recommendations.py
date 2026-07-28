from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

from football_api.services.recommendations import build_recommendations


def _prediction(**overrides):
    values = {
        "confidence": 0.8,
        "data_quality": "alta",
        "home_win_probability": 0.6,
        "draw_probability": 0.22,
        "away_win_probability": 0.18,
        "over_2_5_probability": 0.58,
        "btts_probability": 0.55,
        "over_8_5_corners_probability": 0.62,
        "over_9_5_corners_probability": 0.52,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_value_requires_price_advantage() -> None:
    odd = SimpleNamespace(
        selection="Home",
        decimal_odds=Decimal("2.00"),
        bookmaker="Test",
        captured_at=datetime.now(UTC),
    )
    recommendations = build_recommendations(_prediction(), [odd])
    assert recommendations[0].kind == "valor"
    assert recommendations[0].selection == "Home"
    assert recommendations[0].expected_value == 0.0933
    assert recommendations[0].conservative_probability == 0.5467
    assert recommendations[0].fair_odds == 1.83
    assert recommendations[0].probability_edge == 0.0467


def test_small_raw_edge_is_rejected_after_confidence_adjustment() -> None:
    odd = SimpleNamespace(
        selection="Home",
        decimal_odds=Decimal("1.75"),
        bookmaker="Test",
        captured_at=datetime.now(UTC),
    )

    recommendations = build_recommendations(_prediction(confidence=0.62), [odd])

    assert all(item.kind != "valor" for item in recommendations)


def test_low_quality_returns_no_recommendation() -> None:
    assert build_recommendations(_prediction(confidence=0.4, data_quality="baja"), []) == []
