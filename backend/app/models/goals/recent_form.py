import numpy as np

from app.domain.fixture import MatchObservation
from app.domain.market import GOAL_MARKETS, Market
from app.models.common import goal_output, unavailable, weights
from app.services.features import Features


class GoalRecentFormModel:
    name = "recent_form"

    def predict(self, f: Features):
        if min(len(f.home), len(f.away)) < 5:
            return unavailable(self.name, "Forma reciente insuficiente")

        def average(matches, stat):
            return float(
                np.average([getattr(m, stat) for m in matches], weights=weights(len(matches)))
            )

        home = np.sqrt(average(f.home, "goals_for") * average(f.away, "goals_against"))
        away = np.sqrt(average(f.away, "goals_for") * average(f.home, "goals_against"))

        def shot_trend(matches):
            adjustments = []
            for field in ("shots", "shots_on_target"):
                valid = [m for m in matches if getattr(m, field) is not None]
                if len(valid) >= 5:
                    baseline = float(np.mean([getattr(m, field) for m in valid]))
                    if baseline > 0:
                        adjustments.append(
                            float(np.clip(average(valid, field) / baseline, 0.9, 1.1))
                        )
            return float(np.mean(adjustments)) if adjustments else 1.0

        home *= shot_trend(f.home)
        away *= shot_trend(f.away)
        result = goal_output(self.name, home, away, method="weighted beta-binomial shrinkage")
        # Each historical fixture contributes once, including a shared H2H fixture.
        observations: dict[int, tuple[MatchObservation, float]] = {}
        for sample in (f.home, f.away):
            for obs, weight in zip(sample, weights(len(sample)), strict=True):
                if obs.fixture_id not in observations or weight > observations[obs.fixture_id][1]:
                    observations[obs.fixture_id] = (obs, weight)
        total_weight = sum(weight for _, weight in observations.values())
        for market in GOAL_MARKETS:
            if market == Market.BTTS_NO:
                continue
            success = sum(
                weight
                * (
                    obs.goals_for > 0 and obs.goals_against > 0
                    if market == Market.BTTS_YES
                    else obs.goals_for + obs.goals_against > (market.line or 0)
                )
                for obs, weight in observations.values()
            )
            # Two effective prior observations prevent tiny samples producing 0 or 1.
            result.probabilities[market.value] = (
                success + 2 * result.probabilities[market.value]
            ) / (total_weight + 2)
        result.probabilities[Market.BTTS_NO] = 1 - result.probabilities[Market.BTTS_YES]
        result.diagnostics["shots_sample"] = sum(
            m.shots is not None for m, _ in observations.values()
        )
        result.diagnostics["shots_on_target_sample"] = sum(
            m.shots_on_target is not None for m, _ in observations.values()
        )
        return result
