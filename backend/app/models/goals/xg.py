import numpy as np

from app.models.common import goal_output, unavailable
from app.services.features import Features, mean


class GoalXGModel:
    name = "xg"

    def predict(self, f: Features):
        home = [m for m in f.home_split if m.xg is not None and m.xga is not None]
        away = [m for m in f.away_split if m.xg is not None and m.xga is not None]
        if min(len(home), len(away)) < 3:
            return unavailable(self.name, "xG/xGA reales insuficientes en casa/fuera")
        return goal_output(
            self.name,
            np.sqrt((mean(home, "xg") or 0) * (mean(away, "xga") or 0)),
            np.sqrt((mean(away, "xg") or 0) * (mean(home, "xga") or 0)),
            home_sample=len(home),
            away_sample=len(away),
            source="api_football.expected_goals",
        )
