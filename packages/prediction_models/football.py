import math
from dataclasses import dataclass


@dataclass(frozen=True)
class PredictionResult:
    home_expected_goals: float
    away_expected_goals: float
    home_expected_corners: float | None
    away_expected_corners: float | None
    home_win_probability: float
    draw_probability: float
    away_win_probability: float
    over_2_5_probability: float
    btts_probability: float
    over_8_5_corners_probability: float | None
    over_9_5_corners_probability: float | None
    likely_scores: list[dict[str, float | str]]


def _poisson_probability(value: int, rate: float) -> float:
    return math.exp(-rate) * (rate**value) / math.factorial(value)


def _negative_binomial_cdf(max_value: int, mean: float, dispersion: float = 7.0) -> float:
    if mean <= 0:
        return 1.0
    probability = dispersion / (dispersion + mean)
    total = 0.0
    for value in range(max_value + 1):
        coefficient = math.gamma(value + dispersion) / (
            math.gamma(dispersion) * math.factorial(value)
        )
        total += coefficient * (probability**dispersion) * ((1 - probability) ** value)
    return min(total, 1.0)


def build_prediction(
    home_expected_goals: float,
    away_expected_goals: float,
    home_expected_corners: float | None,
    away_expected_corners: float | None,
    max_goals: int = 8,
) -> PredictionResult:
    home_expected_goals = max(0.15, min(home_expected_goals, 4.5))
    away_expected_goals = max(0.15, min(away_expected_goals, 4.5))
    score_probabilities: list[tuple[str, float]] = []
    home_win = draw = away_win = over_2_5 = btts = 0.0

    for home_goals in range(max_goals + 1):
        home_probability = _poisson_probability(home_goals, home_expected_goals)
        for away_goals in range(max_goals + 1):
            probability = home_probability * _poisson_probability(
                away_goals, away_expected_goals
            )
            score_probabilities.append((f"{home_goals}-{away_goals}", probability))
            if home_goals > away_goals:
                home_win += probability
            elif home_goals == away_goals:
                draw += probability
            else:
                away_win += probability
            if home_goals + away_goals >= 3:
                over_2_5 += probability
            if home_goals > 0 and away_goals > 0:
                btts += probability

    mass = home_win + draw + away_win
    home_win, draw, away_win = (home_win / mass, draw / mass, away_win / mass)
    over_2_5 /= mass
    btts /= mass
    likely_scores = [
        {"score": score, "probability": round(probability, 4)}
        for score, probability in sorted(
            score_probabilities, key=lambda item: item[1], reverse=True
        )[:3]
    ]

    over_8_5 = over_9_5 = None
    if home_expected_corners is not None and away_expected_corners is not None:
        total_corners = max(0.1, home_expected_corners + away_expected_corners)
        over_8_5 = 1 - _negative_binomial_cdf(8, total_corners)
        over_9_5 = 1 - _negative_binomial_cdf(9, total_corners)

    return PredictionResult(
        home_expected_goals=round(home_expected_goals, 2),
        away_expected_goals=round(away_expected_goals, 2),
        home_expected_corners=(
            round(home_expected_corners, 2) if home_expected_corners is not None else None
        ),
        away_expected_corners=(
            round(away_expected_corners, 2) if away_expected_corners is not None else None
        ),
        home_win_probability=round(home_win, 4),
        draw_probability=round(draw, 4),
        away_win_probability=round(away_win, 4),
        over_2_5_probability=round(over_2_5, 4),
        btts_probability=round(btts, 4),
        over_8_5_corners_probability=round(over_8_5, 4) if over_8_5 is not None else None,
        over_9_5_corners_probability=round(over_9_5, 4) if over_9_5 is not None else None,
        likely_scores=likely_scores,
    )
