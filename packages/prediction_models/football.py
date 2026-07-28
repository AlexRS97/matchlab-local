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


@dataclass(frozen=True)
class AdvancedAnalysis:
    market_probabilities: list[dict[str, float | str]]
    score_matrix: list[dict[str, float | int]]
    goal_bands: list[dict[str, float | str]]
    outcome_uncertainty: float
    result_clarity: float
    home_expected_points: float
    away_expected_points: float
    favorite: str
    favorite_probability: float


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
    likely_scores: list[dict[str, float | str]] = [
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


def _fair_odds(probability: float) -> float | None:
    if probability <= 0:
        return None
    return round(1 / probability, 2)


def _market(
    key: str,
    category: str,
    selection: str,
    probability: float,
) -> dict[str, float | str]:
    probability = round(max(0.0, min(1.0, probability)), 4)
    fair_odds = _fair_odds(probability)
    result: dict[str, float | str] = {
        "key": key,
        "category": category,
        "selection": selection,
        "probability": probability,
    }
    if fair_odds is not None:
        result["fair_odds"] = fair_odds
    return result


def build_advanced_analysis(
    home_expected_goals: float,
    away_expected_goals: float,
    home_expected_corners: float | None,
    away_expected_corners: float | None,
    *,
    max_goals: int = 10,
) -> AdvancedAnalysis:
    """Derive explainable markets and visualisation data from the stored goal rates.

    This intentionally remains a pure calculation. It can therefore enrich old predictions
    without a database migration and always uses the same assumptions as ``build_prediction``.
    """

    home_rate = max(0.15, min(home_expected_goals, 4.5))
    away_rate = max(0.15, min(away_expected_goals, 4.5))
    total_rate = home_rate + away_rate
    home_distribution = [_poisson_probability(value, home_rate) for value in range(max_goals + 1)]
    away_distribution = [_poisson_probability(value, away_rate) for value in range(max_goals + 1)]

    score_probabilities: list[tuple[int, int, float]] = []
    home_win = draw = away_win = 0.0
    for home_goals, home_probability in enumerate(home_distribution):
        for away_goals, away_probability in enumerate(away_distribution):
            probability = home_probability * away_probability
            score_probabilities.append((home_goals, away_goals, probability))
            if home_goals > away_goals:
                home_win += probability
            elif home_goals == away_goals:
                draw += probability
            else:
                away_win += probability

    result_mass = home_win + draw + away_win
    home_win, draw, away_win = (
        home_win / result_mass,
        draw / result_mass,
        away_win / result_mass,
    )

    def total_under(maximum: int) -> float:
        return sum(_poisson_probability(value, total_rate) for value in range(maximum + 1))

    under_1_5 = total_under(1)
    under_2_5 = total_under(2)
    under_3_5 = total_under(3)
    home_scores = 1 - math.exp(-home_rate)
    away_scores = 1 - math.exp(-away_rate)
    btts = home_scores * away_scores

    markets = [
        _market("home_win", "Resultado", "Victoria local", home_win),
        _market("draw", "Resultado", "Empate", draw),
        _market("away_win", "Resultado", "Victoria visitante", away_win),
        _market("home_or_draw", "Doble oportunidad", "Local o empate", home_win + draw),
        _market("away_or_draw", "Doble oportunidad", "Visitante o empate", away_win + draw),
        _market("home_or_away", "Doble oportunidad", "Local o visitante", home_win + away_win),
        _market("over_1_5", "Goles totales", "Más de 1,5", 1 - under_1_5),
        _market("under_1_5", "Goles totales", "Menos de 1,5", under_1_5),
        _market("over_2_5", "Goles totales", "Más de 2,5", 1 - under_2_5),
        _market("under_2_5", "Goles totales", "Menos de 2,5", under_2_5),
        _market("over_3_5", "Goles totales", "Más de 3,5", 1 - under_3_5),
        _market("under_3_5", "Goles totales", "Menos de 3,5", under_3_5),
        _market("btts_yes", "Ambos marcan", "Sí", btts),
        _market("btts_no", "Ambos marcan", "No", 1 - btts),
        _market("home_over_0_5", "Goles por equipo", "Local marca", home_scores),
        _market("away_over_0_5", "Goles por equipo", "Visitante marca", away_scores),
        _market("home_clean_sheet", "Portería a cero", "Local", 1 - away_scores),
        _market("away_clean_sheet", "Portería a cero", "Visitante", 1 - home_scores),
    ]

    if home_expected_corners is not None and away_expected_corners is not None:
        corner_rate = max(0.1, home_expected_corners + away_expected_corners)
        for threshold in (7, 8, 9, 10):
            over = 1 - _negative_binomial_cdf(threshold, corner_rate)
            line = f"{threshold + 0.5:.1f}".replace(".", ",")
            markets.extend(
                [
                    _market(
                        f"corners_over_{threshold}_5",
                        "Córners totales",
                        f"Más de {line}",
                        over,
                    ),
                    _market(
                        f"corners_under_{threshold}_5",
                        "Córners totales",
                        f"Menos de {line}",
                        1 - over,
                    ),
                ]
            )

    max_common_score_probability = max(
        probability
        for home_goals, away_goals, probability in score_probabilities
        if home_goals <= 4 and away_goals <= 4
    )
    score_matrix = [
        {
            "home_goals": home_goals,
            "away_goals": away_goals,
            "probability": round(probability, 4),
            "relative_intensity": round(
                probability / max_common_score_probability,
                4,
            ),
        }
        for home_goals, away_goals, probability in score_probabilities
        if home_goals <= 4 and away_goals <= 4
    ]

    goal_bands: list[dict[str, float | str]] = [
        {"label": "0–1 goles", "probability": round(under_1_5, 4)},
        {"label": "2–3 goles", "probability": round(under_3_5 - under_1_5, 4)},
        {"label": "4+ goles", "probability": round(1 - under_3_5, 4)},
    ]

    probabilities = (home_win, draw, away_win)
    entropy = -sum(probability * math.log(probability) for probability in probabilities)
    normalized_entropy = entropy / math.log(3)
    favorite_index = max(range(3), key=lambda index: probabilities[index])
    favorite = ("home", "draw", "away")[favorite_index]

    return AdvancedAnalysis(
        market_probabilities=markets,
        score_matrix=score_matrix,
        goal_bands=goal_bands,
        outcome_uncertainty=round(normalized_entropy, 4),
        result_clarity=round(1 - normalized_entropy, 4),
        home_expected_points=round(3 * home_win + draw, 2),
        away_expected_points=round(3 * away_win + draw, 2),
        favorite=favorite,
        favorite_probability=round(probabilities[favorite_index], 4),
    )
