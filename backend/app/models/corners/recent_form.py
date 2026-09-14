import numpy as np

from app.domain.market import CORNER_MARKETS
from app.models.common import unavailable, weights
from app.models.corners.common import output, samples
from app.services.features import Features


class CornerRecentFormModel:
    name = "recent_form"

    def predict(self, f: Features):
        home, away, _, _ = samples(f)
        if min(len(home), len(away)) < 5:
            return unavailable(self.name, "Forma reciente de córners insuficiente")

        def average(matches, name):
            return float(
                np.average([getattr(m, name) for m in matches], weights=weights(len(matches)))
            )

        h = np.sqrt(average(home, "corners_for") * average(away, "corners_against"))
        a = np.sqrt(average(away, "corners_for") * average(home, "corners_against"))
        result = output(self.name, float(h), float(a))
        observations: dict = {}
        for group in (home, away):
            for obs, weight in zip(group, weights(len(group)), strict=True):
                if obs.fixture_id not in observations or weight > observations[obs.fixture_id][1]:
                    observations[obs.fixture_id] = (obs, weight)
        weight_sum = sum(weight for obs, weight in observations.values())
        for market in CORNER_MARKETS:
            successes = sum(
                weight * (obs.corners_for + obs.corners_against > market.line)
                for obs, weight in observations.values()
            )
            result.probabilities[market.value] = (
                successes + 2 * result.probabilities[market.value]
            ) / (weight_sum + 2)
        return result
