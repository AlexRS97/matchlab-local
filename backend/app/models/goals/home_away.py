import numpy as np

from app.models.common import goal_output, unavailable
from app.services.features import Features, mean


class GoalHomeAwayModel:
    name = "home_away"

    def predict(self, f: Features):
        if min(len(f.home_split), len(f.away_split)) < 3:
            return unavailable(self.name, "Se necesitan 3 partidos por cada split casa/fuera")
        home = np.sqrt(
            (mean(f.home_split, "goals_for") or 0) * (mean(f.away_split, "goals_against") or 0)
        )
        away = np.sqrt(
            (mean(f.away_split, "goals_for") or 0) * (mean(f.home_split, "goals_against") or 0)
        )
        return goal_output(
            self.name, home, away, home_sample=len(f.home_split), away_sample=len(f.away_split)
        )
