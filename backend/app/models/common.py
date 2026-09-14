import numpy as np
from scipy.stats import poisson

from app.domain.market import GOAL_MARKETS, Market
from app.domain.prediction import ModelOutput


def unavailable(name: str, reason: str) -> ModelOutput:
    return ModelOutput(name=name, status="unavailable", reason=reason)


def weights(size: int) -> np.ndarray:
    return np.array([1.0 if i < 5 else 0.6 if i < 10 else 0.3 for i in range(size)])


def goal_output(name: str, home: float, away: float, **diagnostics) -> ModelOutput:
    home, away = float(np.clip(home, 0.05, 6)), float(np.clip(away, 0.05, 6))
    total = home + away
    btts = float((1 - np.exp(-home)) * (1 - np.exp(-away)))
    probabilities = {
        m.value: float(poisson.sf(int(m.line), total)) for m in GOAL_MARKETS if m.line is not None
    }
    probabilities[Market.BTTS_YES.value], probabilities[Market.BTTS_NO.value] = btts, 1 - btts
    return ModelOutput(
        name=name,
        probabilities=probabilities,
        expected_home=home,
        expected_away=away,
        diagnostics=diagnostics,
    )


def shrink(value: float, baseline: float, sample: int, prior: int = 5) -> float:
    return (value * sample + baseline * prior) / (sample + prior)
