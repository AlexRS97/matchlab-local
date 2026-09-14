from pydantic import BaseModel, Field


class ModelOutput(BaseModel):
    name: str
    status: str = "available"
    reason: str | None = None
    probabilities: dict[str, float] = Field(default_factory=dict)
    expected_home: float | None = None
    expected_away: float | None = None
    diagnostics: dict = Field(default_factory=dict)


class EnsembleOutput(BaseModel):
    probabilities: dict[str, float] = Field(default_factory=dict)
    models: list[ModelOutput] = Field(default_factory=list)
    weights: dict[str, dict[str, float]] = Field(default_factory=dict)
    consensus: dict[str, dict] = Field(default_factory=dict)
    expected_home: float | None = None
    expected_away: float | None = None
    expected_total: float | None = None
