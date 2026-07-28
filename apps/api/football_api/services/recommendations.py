"""Traducción conservadora de probabilidades a señales explicables para la interfaz."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from football_api.models import Fixture, OddsSnapshot, Prediction


@dataclass(frozen=True)
class Recommendation:
    """Señal informativa; solo representa valor cuando existe una cuota verificable."""

    market: str
    selection: str
    probability: float
    confidence: float
    rating: str
    kind: str
    rationale: str
    decimal_odds: float | None = None
    bookmaker: str | None = None
    expected_value: float | None = None
    conservative_probability: float | None = None
    fair_odds: float | None = None
    probability_edge: float | None = None
    signal_score: float = 0.0


@dataclass(frozen=True)
class TeamInsight:
    team_id: int
    team_name: str
    venue: str
    expected_goals: float
    win_probability: float
    avoid_defeat_probability: float
    summary: str


def _best_current_odds(odds: list[OddsSnapshot]) -> dict[str, OddsSnapshot]:
    if not odds:
        return {}
    latest = max(item.captured_at for item in odds)
    current = [item for item in odds if item.captured_at >= latest - timedelta(minutes=10)]
    best: dict[str, OddsSnapshot] = {}
    for item in current:
        existing = best.get(item.selection)
        if existing is None or item.decimal_odds > existing.decimal_odds:
            best[item.selection] = item
    return best


def build_recommendations(
    prediction: Prediction,
    odds: list[OddsSnapshot],
) -> list[Recommendation]:
    """Ordena mercados y exige ventaja mínima sobre una probabilidad conservadora."""
    if prediction.confidence < 0.55 or prediction.data_quality == "baja":
        return []

    candidates = [
        ("Resultado", "Home", prediction.home_win_probability),
        ("Resultado", "Draw", prediction.draw_probability),
        ("Resultado", "Away", prediction.away_win_probability),
        ("Goles", "Over 2.5", prediction.over_2_5_probability),
        ("Goles", "Under 2.5", 1 - prediction.over_2_5_probability),
        ("Ambos marcan", "BTTS Yes", prediction.btts_probability),
        ("Ambos marcan", "BTTS No", 1 - prediction.btts_probability),
    ]
    if prediction.over_8_5_corners_probability is not None:
        candidates.extend(
            [
                ("Córners", "Over 8.5", prediction.over_8_5_corners_probability),
                ("Córners", "Under 8.5", 1 - prediction.over_8_5_corners_probability),
            ]
        )
    if prediction.over_9_5_corners_probability is not None:
        candidates.extend(
            [
                ("Córners", "Over 9.5", prediction.over_9_5_corners_probability),
                ("Córners", "Under 9.5", 1 - prediction.over_9_5_corners_probability),
            ]
        )

    strongest_by_market: dict[str, tuple[str, float]] = {}
    for market, selection, probability in candidates:
        existing = strongest_by_market.get(market)
        if existing is None or probability > existing[1]:
            strongest_by_market[market] = (selection, probability)

    best_odds = _best_current_odds(odds)
    results: list[Recommendation] = []
    for market, (selection, probability) in strongest_by_market.items():
        neutral_probability = 1 / 3 if market == "Resultado" else 0.5
        conservative_probability = neutral_probability + (
            probability - neutral_probability
        ) * prediction.confidence
        fair_odds = 1 / conservative_probability
        signal_score = conservative_probability * prediction.confidence
        odd = best_odds.get(selection)
        if odd is not None:
            decimal_odd = float(odd.decimal_odds)
            implied_probability = 1 / decimal_odd
            probability_edge = conservative_probability - implied_probability
            expected_value = conservative_probability * decimal_odd - 1
            if (
                expected_value >= 0.04
                and probability_edge >= 0.025
                and conservative_probability >= 0.42
            ):
                rating = (
                    "fuerte"
                    if prediction.confidence >= 0.75 and expected_value >= 0.08
                    else "moderada"
                )
                results.append(
                    Recommendation(
                        market=market,
                        selection=selection,
                        probability=round(probability, 4),
                        confidence=prediction.confidence,
                        rating=rating,
                        kind="valor",
                        decimal_odds=decimal_odd,
                        bookmaker=odd.bookmaker,
                        expected_value=round(expected_value, 4),
                        conservative_probability=round(conservative_probability, 4),
                        fair_odds=round(fair_odds, 2),
                        probability_edge=round(probability_edge, 4),
                        signal_score=round(signal_score, 4),
                        rationale=(
                            "La probabilidad conservadora, ajustada por confianza, supera "
                            "la probabilidad implícita de la mejor cuota capturada."
                        ),
                    )
                )
                continue
        threshold = 0.64 if market != "Resultado" else 0.48
        if probability >= threshold and prediction.confidence >= 0.62:
            results.append(
                Recommendation(
                    market=market,
                    selection=selection,
                    probability=round(probability, 4),
                    confidence=prediction.confidence,
                    rating="tendencia",
                    kind="tendencia",
                    conservative_probability=round(conservative_probability, 4),
                    fair_odds=round(fair_odds, 2),
                    signal_score=round(signal_score, 4),
                    rationale=(
                        "Tendencia estadística: la cuota justa es orientativa y falta "
                        "una cuota válida para confirmar valor."
                    ),
                )
            )

    return sorted(
        results,
        key=lambda item: (
            item.kind == "valor",
            item.expected_value or 0,
            item.signal_score,
        ),
        reverse=True,
    )[:3]


def build_team_insights(fixture: Fixture, prediction: Prediction) -> list[TeamInsight]:
    """Resume el perfil de cada equipo sin introducir cálculos nuevos."""

    home_avoid = prediction.home_win_probability + prediction.draw_probability
    away_avoid = prediction.away_win_probability + prediction.draw_probability
    return [
        TeamInsight(
            team_id=fixture.home_team.id,
            team_name=fixture.home_team.name,
            venue="local",
            expected_goals=prediction.home_expected_goals,
            win_probability=prediction.home_win_probability,
            avoid_defeat_probability=round(home_avoid, 4),
            summary=(
                f"{fixture.home_team.name} genera {prediction.home_expected_goals:.2f} "
                f"goles esperados y tiene {home_avoid:.0%} de probabilidad de no perder."
            ),
        ),
        TeamInsight(
            team_id=fixture.away_team.id,
            team_name=fixture.away_team.name,
            venue="visitante",
            expected_goals=prediction.away_expected_goals,
            win_probability=prediction.away_win_probability,
            avoid_defeat_probability=round(away_avoid, 4),
            summary=(
                f"{fixture.away_team.name} genera {prediction.away_expected_goals:.2f} "
                f"goles esperados y tiene {away_avoid:.0%} de probabilidad de no perder."
            ),
        ),
    ]
