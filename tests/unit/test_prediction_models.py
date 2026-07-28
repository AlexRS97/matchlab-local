import pytest

from prediction_models.football import build_advanced_analysis, build_prediction


def test_probabilities_form_a_complete_result_distribution() -> None:
    prediction = build_prediction(1.6, 1.1, 5.4, 4.2)

    result_mass = (
        prediction.home_win_probability
        + prediction.draw_probability
        + prediction.away_win_probability
    )
    assert result_mass == pytest.approx(1.0, abs=0.001)
    assert prediction.home_win_probability > prediction.away_win_probability
    assert len(prediction.likely_scores) == 3


def test_corner_tail_probabilities_are_ordered() -> None:
    prediction = build_prediction(1.2, 1.0, 5.2, 4.6)

    assert prediction.over_8_5_corners_probability is not None
    assert prediction.over_9_5_corners_probability is not None
    assert prediction.over_8_5_corners_probability >= prediction.over_9_5_corners_probability


def test_corner_predictions_are_omitted_without_data() -> None:
    prediction = build_prediction(1.2, 1.0, None, None)

    assert prediction.home_expected_corners is None
    assert prediction.over_8_5_corners_probability is None


def test_extreme_goal_rates_are_bounded() -> None:
    prediction = build_prediction(99, -1, None, None)

    assert prediction.home_expected_goals == 4.5
    assert prediction.away_expected_goals == 0.15


def test_advanced_markets_are_coherent_and_include_fair_odds() -> None:
    analysis = build_advanced_analysis(1.65, 1.05, 5.2, 4.4)
    markets = {item["key"]: item for item in analysis.market_probabilities}

    assert markets["home_or_draw"]["probability"] == pytest.approx(
        markets["home_win"]["probability"] + markets["draw"]["probability"],
        abs=0.001,
    )
    assert markets["over_1_5"]["probability"] >= markets["over_2_5"]["probability"]
    assert markets["over_2_5"]["probability"] >= markets["over_3_5"]["probability"]
    assert markets["home_win"]["fair_odds"] == pytest.approx(
        1 / markets["home_win"]["probability"],
        abs=0.02,
    )
    assert "corners_over_9_5" in markets


def test_goal_bands_and_score_heatmap_are_ready_for_visualisation() -> None:
    analysis = build_advanced_analysis(1.4, 1.2, None, None)

    assert sum(item["probability"] for item in analysis.goal_bands) == pytest.approx(
        1.0,
        abs=0.001,
    )
    assert len(analysis.score_matrix) == 25
    assert max(item["relative_intensity"] for item in analysis.score_matrix) == 1
    assert 0 <= analysis.outcome_uncertainty <= 1
    assert 0 <= analysis.result_clarity <= 1
    assert analysis.home_expected_points <= 3
    assert analysis.away_expected_points <= 3
