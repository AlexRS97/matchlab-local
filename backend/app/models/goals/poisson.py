import numpy as np
from scipy.stats import poisson

from app.models.common import goal_output, shrink, unavailable
from app.services.features import Features, mean


class GoalPoissonModel:
    name = "poisson"

    def predict(self, f: Features):
        if min(len(f.home), len(f.away)) < 5:
            return unavailable(self.name, "Se necesitan al menos 5 partidos previos por equipo")
        pool = f.home + f.away
        baseline = mean(pool, "goals_for") or 0.05
        league_h = max(0.05, f.league["home_goals"]) if f.league else baseline
        league_a = max(0.05, f.league["away_goals"]) if f.league else baseline

        def profile(recent, split, stat, base):
            all_rate = shrink(mean(recent, stat) or 0, base, len(recent))
            if not split:
                return all_rate
            return 0.4 * all_rate + 0.6 * shrink(mean(split, stat) or 0, base, len(split))

        home_attack = profile(f.home, f.home_split, "goals_for", league_h) / league_h
        away_defence = profile(f.away, f.away_split, "goals_against", league_h) / league_h
        away_attack = profile(f.away, f.away_split, "goals_for", league_a) / league_a
        home_defence = profile(f.home, f.home_split, "goals_against", league_a) / league_a
        result = goal_output(
            self.name,
            league_h * home_attack * away_defence,
            league_a * away_attack * home_defence,
            baseline_source="league" if f.league else "observed_team_pool",
            home_attack=home_attack,
            away_attack=away_attack,
            home_defence=home_defence,
            away_defence=away_defence,
        )
        matrix = np.outer(
            poisson.pmf(np.arange(7), result.expected_home),
            poisson.pmf(np.arange(7), result.expected_away),
        )
        result.diagnostics["score_matrix"] = matrix.tolist()
        result.diagnostics["residual_tail"] = max(0.0, 1 - float(matrix.sum()))
        rate = (result.expected_home or 0) + (result.expected_away or 0)
        result.diagnostics["total_distribution"] = [
            float(poisson.pmf(i, rate)) for i in range(5)
        ] + [float(poisson.sf(4, rate))]
        return result
