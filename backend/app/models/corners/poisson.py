from app.models.common import unavailable
from app.models.corners.common import output, rates, samples
from app.services.features import Features


class CornerPoissonModel:
    name = "poisson"

    def predict(self, f: Features):
        home, away, _, _ = samples(f)
        if min(len(home), len(away)) < 5:
            return unavailable(
                self.name, "Mínimo de 5 partidos con córners por equipo no alcanzado"
            )
        return output(self.name, *rates(home, away))
