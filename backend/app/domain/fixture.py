from datetime import datetime
from enum import StrEnum

from pydantic import AwareDatetime, BaseModel, Field


class FixtureStatus(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    LIVE = "LIVE"
    FINISHED = "FINISHED"
    POSTPONED = "POSTPONED"
    CANCELLED = "CANCELLED"


class Fixture(BaseModel):
    fixture_id: int
    provider: str = "api_football"
    provider_fixture_id: str
    kickoff_utc: AwareDatetime
    country: str
    league_id: int
    league_name: str
    season: int
    home_team_id: int
    home_team: str
    away_team_id: int
    away_team: str
    status: FixtureStatus
    source_status: str = "NS"
    home_goals: int | None = Field(None, ge=0)
    away_goals: int | None = Field(None, ge=0)
    home_corners: float | None = Field(None, ge=0)
    away_corners: float | None = Field(None, ge=0)
    updated_at: AwareDatetime

    def prematch(self, now: datetime) -> bool:
        return self.status == FixtureStatus.NOT_STARTED and self.kickoff_utc > now


class MatchObservation(BaseModel):
    statistics_allowed: bool = True
    fixture_id: int
    team_id: int
    opponent_id: int
    kickoff_utc: AwareDatetime
    completed_at: AwareDatetime
    is_home: bool
    goals_for: float = Field(ge=0)
    goals_against: float = Field(ge=0)
    corners_for: float | None = Field(None, ge=0)
    corners_against: float | None = Field(None, ge=0)
    shots: float | None = Field(None, ge=0)
    shots_on_target: float | None = Field(None, ge=0)
    possession: float | None = Field(None, ge=0, le=100)
    xg: float | None = Field(None, ge=0)
    xga: float | None = Field(None, ge=0)
    league_id: int
    competition: str
    source: str = "api_football"
    observed_at: AwareDatetime
