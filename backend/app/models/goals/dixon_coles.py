import numpy as np
from scipy.optimize import minimize_scalar

from app.models.goals.poisson import GoalPoissonModel
from app.services.features import Features


class DixonColesModel:
    """Local, regularized Dixon–Coles low-score correction; not a global league fit."""

    name = "dixon_coles"

    def predict(self, f: Features):
        result = GoalPoissonModel().predict(f)
        result.name = self.name
        if result.status != "available":
            return result
        unique = {m.fixture_id: m for m in f.home + f.away}
        scores = [
            (m.goals_for, m.goals_against) if m.is_home else (m.goals_against, m.goals_for)
            for m in unique.values()
        ]
        h, a = np.asarray(scores, dtype=float).T
        lh, la = max(0.1, float(h.mean())), max(0.1, float(a.mean()))
        th, ta = result.expected_home, result.expected_away
        assert th is not None and ta is not None
        lower = max(-0.3, -1 / max(lh, la, th, ta) + 0.001)
        upper = min(0.3, 1 / max(lh * la, th * ta) - 0.001)

        def loss(rho):
            tau = np.ones(len(h))
            tau[(h == 0) & (a == 0)] = 1 - lh * la * rho
            tau[(h == 0) & (a == 1)] = 1 + lh * rho
            tau[(h == 1) & (a == 0)] = 1 + la * rho
            tau[(h == 1) & (a == 1)] = 1 - rho
            return -float(np.log(tau).sum()) + 20 * rho * rho

        fit = minimize_scalar(loss, bounds=(lower, upper), method="bounded")
        rho = float(fit.x) if fit.success else 0.0
        # Four mass adjustments sum to zero. Marginals and expectations are preserved.
        delta = float(np.exp(-th - ta) * th * ta * rho)
        p = result.probabilities
        p["OVER_0_5_GOALS"] += delta
        p["OVER_1_5_GOALS"] -= delta
        p["BTTS_YES"] -= delta
        p["BTTS_NO"] = 1 - p["BTTS_YES"]
        matrix = result.diagnostics["score_matrix"]
        for home, away, adjustment in [
            (0, 0, -delta),
            (0, 1, delta),
            (1, 0, delta),
            (1, 1, -delta),
        ]:
            matrix[home][away] += adjustment
        result.diagnostics.update(
            rho=rho, fit_samples=len(scores), method="local_regularized_low_score_correction"
        )
        distribution = result.diagnostics["total_distribution"]
        distribution[0] -= delta
        distribution[1] += 2 * delta
        distribution[2] -= delta
        return result
