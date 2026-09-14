from app.models.common import unavailable
from app.models.corners.common import output, rates, samples
from app.services.features import Features


class CornerHomeAwayModel:
    name = "home_away"

    def predict(self, f: Features):
        _, _, home, away = samples(f)
        if min(len(home), len(away)) < 3:
            return unavailable(self.name, "Mínimo de 3 partidos con córners por split no alcanzado")
        return output(self.name, *rates(home, away))
