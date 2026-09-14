from app.models.base import StatisticalModel
from app.models.ensemble import combine
from app.models.goals.dixon_coles import DixonColesModel
from app.models.goals.external import ExternalPredictionModel
from app.models.goals.home_away import GoalHomeAwayModel
from app.models.goals.negative_binomial import GoalNegativeBinomialModel
from app.models.goals.poisson import GoalPoissonModel
from app.models.goals.recent_form import GoalRecentFormModel
from app.models.goals.xg import GoalXGModel
from app.services.features import Features


class GoalEnsemble:
    def __init__(self, weights: dict[str, float]):
        self.weights = weights
        self.models: list[StatisticalModel] = [
            GoalPoissonModel(),
            DixonColesModel(),
            GoalNegativeBinomialModel(),
            GoalRecentFormModel(),
            GoalHomeAwayModel(),
            GoalXGModel(),
            ExternalPredictionModel(),
        ]

    def predict(self, features: Features):
        return combine([model.predict(features) for model in self.models], self.weights)
