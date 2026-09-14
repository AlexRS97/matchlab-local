from app.models.base import StatisticalModel
from app.models.corners.home_away import CornerHomeAwayModel
from app.models.corners.negative_binomial import CornerNegativeBinomialModel
from app.models.corners.poisson import CornerPoissonModel
from app.models.corners.recent_form import CornerRecentFormModel
from app.models.ensemble import combine
from app.services.features import Features


class CornerEnsemble:
    def __init__(self, weights: dict[str, float]):
        self.weights = weights
        self.models: list[StatisticalModel] = [
            CornerNegativeBinomialModel(),
            CornerPoissonModel(),
            CornerRecentFormModel(),
            CornerHomeAwayModel(),
        ]

    def predict(self, features: Features):
        return combine([model.predict(features) for model in self.models], self.weights)
