from typing import Protocol

from app.domain.prediction import ModelOutput
from app.services.features import Features


class StatisticalModel(Protocol):
    name: str

    def predict(self, features: Features) -> ModelOutput: ...
