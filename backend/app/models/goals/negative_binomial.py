import numpy as np
from scipy.stats import nbinom, poisson

from app.domain.market import GOAL_MARKETS
from app.models.goals.poisson import GoalPoissonModel
from app.services.features import Features


class GoalNegativeBinomialModel:
    name = "negative_binomial"

    def predict(self, f: Features):
        result = GoalPoissonModel().predict(f)
        result.name = self.name
        if result.status != "available":
            return result
        rates = [result.expected_home, result.expected_away]
        distributions, zeros, parameters = [], [], []
        for matches, rate in zip((f.home + f.away, f.away + f.home), rates, strict=True):
            values = [m.goals_for for m in matches[:20]] + [m.goals_against for m in matches[20:]]
            mean = max(0.05, float(np.mean(values)))
            variance = float(np.var(values, ddof=1))
            excess = max(0, (variance - mean) / mean**2) * len(values) / (len(values) + 20)
            assert rate is not None
            dist = nbinom(1 / excess, 1 / (1 + rate * excess)) if excess > 0.01 else poisson(rate)
            distributions.append(dist.pmf(np.arange(6)))
            zeros.append(float(dist.pmf(0)))
            parameters.append(excess)
        total = np.convolve(*distributions)
        for market in GOAL_MARKETS:
            if market.line is not None:
                result.probabilities[market.value] = float(1 - total[: int(market.line) + 1].sum())
        result.probabilities["BTTS_YES"] = (1 - zeros[0]) * (1 - zeros[1])
        result.probabilities["BTTS_NO"] = 1 - result.probabilities["BTTS_YES"]
        result.diagnostics = {
            "overdispersion": parameters,
            "method": "shrunken_independent_goal_marginals",
        }
        return result
