"""Contratos Pydantic expuestos por la API; no contienen reglas de negocio."""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TeamSummary(BaseModel):
    id: int
    name: str
    logo_url: str | None = None


class CompetitionSummary(BaseModel):
    id: int
    name: str
    country: str | None = None
    logo_url: str | None = None
    is_friendly: bool = False
    region: str = "Mundo"
    priority: int = 0


class RecommendationResponse(BaseModel):
    market: str
    selection: str
    probability: float
    confidence: float
    rating: str
    kind: str
    rationale: str
    decimal_odds: float | None = None
    bookmaker: str | None = None
    expected_value: float | None = None
    conservative_probability: float | None = None
    fair_odds: float | None = None
    probability_edge: float | None = None
    signal_score: float = 0.0


class TeamInsightResponse(BaseModel):
    team_id: int
    team_name: str
    venue: str
    expected_goals: float
    win_probability: float
    avoid_defeat_probability: float
    summary: str


class MarketProbabilityResponse(BaseModel):
    key: str
    category: str
    selection: str
    probability: float = Field(ge=0, le=1)
    fair_odds: float | None = None


class ScoreMatrixCellResponse(BaseModel):
    home_goals: int = Field(ge=0)
    away_goals: int = Field(ge=0)
    probability: float = Field(ge=0, le=1)
    relative_intensity: float = Field(ge=0, le=1)


class GoalBandResponse(BaseModel):
    label: str
    probability: float = Field(ge=0, le=1)


class PredictionResponse(BaseModel):
    id: int
    generated_at: datetime
    model_version: str
    home_expected_goals: float
    away_expected_goals: float
    total_expected_goals: float
    home_expected_corners: float | None
    away_expected_corners: float | None
    total_expected_corners: float | None
    home_win_probability: float
    draw_probability: float
    away_win_probability: float
    over_2_5_probability: float
    btts_probability: float
    over_8_5_corners_probability: float | None
    over_9_5_corners_probability: float | None
    confidence: float
    data_quality: str
    likely_scores: list[dict[str, Any]]
    explanation: list[str]
    recommendations: list[RecommendationResponse] = Field(default_factory=list)
    team_insights: list[TeamInsightResponse] = Field(default_factory=list)
    market_probabilities: list[MarketProbabilityResponse] = Field(default_factory=list)
    score_matrix: list[ScoreMatrixCellResponse] = Field(default_factory=list)
    goal_bands: list[GoalBandResponse] = Field(default_factory=list)
    outcome_uncertainty: float = Field(ge=0, le=1)
    result_clarity: float = Field(ge=0, le=1)
    home_expected_points: float = Field(ge=0, le=3)
    away_expected_points: float = Field(ge=0, le=3)
    favorite: str
    favorite_probability: float = Field(ge=0, le=1)
    signal_strength: float = Field(ge=0, le=1)


class FixtureResponse(BaseModel):
    id: int
    provider_id: int
    kickoff_at: datetime
    status: str
    status_long: str | None
    round_name: str | None
    venue_name: str | None
    home_goals: int | None
    away_goals: int | None
    home_team: TeamSummary
    away_team: TeamSummary
    competition: CompetitionSummary
    prediction: PredictionResponse | None = None


class DailyAnalysisResponse(BaseModel):
    date: date
    timezone: str
    total_fixtures: int
    analyzed_fixtures: int
    high_confidence_fixtures: int
    recommended_fixtures: int
    demo_mode: bool
    automatic_refresh: bool
    automatic_refresh_minutes: int
    last_updated_at: datetime | None = None
    fixtures: list[FixtureResponse]


class TeamFormMatch(BaseModel):
    fixture_id: int
    kickoff_at: datetime
    opponent: str
    venue: str
    goals_for: int
    goals_against: int
    result: str


class TeamFormResponse(BaseModel):
    team: TeamSummary
    matches: list[TeamFormMatch]


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    target_date: date
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    api_calls: int
    fixtures_found: int
    predictions_generated: int
    message: str | None
    error_detail: str | None


class JobQueuedResponse(BaseModel):
    task_id: str
    status: str = "queued"


class DataQualityResponse(BaseModel):
    date: date
    fixtures: int
    with_prediction: int
    with_corner_prediction: int
    high_quality: int
    coverage_percentage: float = Field(ge=0, le=100)
