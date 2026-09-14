import numpy as np

from app.models.common import unavailable
from app.models.corners.common import output, rates, samples
from app.services.features import Features


class CornerNegativeBinomialModel:
    name = "negative_binomial"

    def predict(self, f: Features):
        home, away, _, _ = samples(f)
        if min(len(home), len(away)) < 5:
            return unavailable(
                self.name, "Muestra de córners insuficiente para estimar la dispersión"
            )
        unique = {m.fixture_id: m for m in home + away}
        totals = [m.corners_for + m.corners_against for m in unique.values()]
        result = output(self.name, *rates(home, away), variance=float(np.var(totals, ddof=1)))
        result.diagnostics["sample_size"] = len(totals)
        return result
