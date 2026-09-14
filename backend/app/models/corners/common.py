import numpy as np
from scipy.stats import nbinom, poisson

from app.domain.market import CORNER_MARKETS
from app.domain.prediction import ModelOutput
from app.services.features import Features, mean


def samples(f: Features):
    return tuple(
        [m for m in group if m.corners_for is not None and m.corners_against is not None]
        for group in (f.home, f.away, f.home_split, f.away_split)
    )


def rates(home, away) -> tuple[float, float]:
    return (
        float(np.sqrt((mean(home, "corners_for") or 0) * (mean(away, "corners_against") or 0))),
        float(np.sqrt((mean(away, "corners_for") or 0) * (mean(home, "corners_against") or 0))),
    )


def output(name: str, home: float, away: float, variance: float | None = None) -> ModelOutput:
    total = max(0.01, home + away)
    overdispersed = variance is not None and variance > total * 1.10
    dispersion = total**2 / (variance - total) if overdispersed and variance is not None else None
    probabilities = {
        m.value: float(nbinom.sf(int(m.line or 0), dispersion, dispersion / (dispersion + total)))
        if dispersion
        else float(poisson.sf(int(m.line or 0), total))
        for m in CORNER_MARKETS
    }
    return ModelOutput(
        name=name,
        expected_home=home,
        expected_away=away,
        probabilities=probabilities,
        diagnostics={
            "distribution": "negative_binomial" if dispersion else "poisson",
            "variance": variance,
            "dispersion": dispersion,
            "overdispersed": overdispersed,
        },
    )
