import pytest

from prediction_models.football import build_prediction


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

