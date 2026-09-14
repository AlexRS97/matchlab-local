import math


def fair_odds(probability: float | None) -> float | None:
    if probability is None or probability == 0:
        return None
    if not math.isfinite(probability) or not 0 < probability <= 1:
        raise ValueError("Probabilidad fuera de rango")
    return 1 / probability


def implied_probability(odds: float) -> float:
    if not math.isfinite(odds) or odds <= 1:
        raise ValueError("Cuota decimal no válida")
    return 1 / odds


def devig(first: float, second: float) -> tuple[float, float]:
    a, b = implied_probability(first), implied_probability(second)
    return a / (a + b), b / (a + b)


def expected_value(probability: float, odds: float) -> float:
    if not math.isfinite(probability) or not 0 <= probability <= 1:
        raise ValueError("Probabilidad fuera de rango")
    implied_probability(odds)
    return probability * odds - 1
