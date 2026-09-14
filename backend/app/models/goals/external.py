from app.domain.market import GOAL_MARKETS
from app.domain.prediction import ModelOutput
from app.models.common import unavailable
from app.services.features import Features


class ExternalPredictionModel:
    name = "external"

    def predict(self, f: Features):
        # API-Football's 1X2 percentages and textual under_over advice are not O2.5 probabilities.
        valid = {
            key: value
            for key, value in f.external.get("market_probabilities", {}).items()
            if key in {m.value for m in GOAL_MARKETS}
            and isinstance(value, (int, float))
            and 0 <= value <= 1
        }
        if not valid:
            return unavailable(
                self.name, "El proveedor no facilita probabilidades documentadas de estos mercados"
            )
        return ModelOutput(name=self.name, probabilities=valid, diagnostics={"source": "external"})
