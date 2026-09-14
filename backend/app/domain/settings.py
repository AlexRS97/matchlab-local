from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.market import Market
from app.domain.odds import Bookmaker


class UserSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    default_bookmaker: Literal["ALL", "BETFAIR", "BET365", "WINAMAX"] = "ALL"
    minimum_odds: float = Field(1.35, gt=1, le=1000)
    top_n: int = 5
    minimum_confidence: Literal["INSUFFICIENT", "LOW", "MEDIUM", "HIGH", "VERY_HIGH"] = "MEDIUM"
    minimum_data_quality: Literal["INSUFFICIENT", "LOW", "ACCEPTABLE", "GOOD", "EXCELLENT"] = (
        "ACCEPTABLE"
    )
    enabled_bookmakers: list[Bookmaker] = Field(default_factory=lambda: list(Bookmaker))
    enabled_markets: list[Market] = Field(default_factory=lambda: list(Market))
    enabled_countries: list[str] = Field(default_factory=list)
    enabled_leagues: list[int] = Field(default_factory=list)
    fixtures_minutes: int = Field(30, ge=15, le=1440)
    standings_minutes: int = Field(240, ge=180, le=1440)
    stats_minutes: int = Field(360, ge=60, le=1440)
    betfair_minutes: int = Field(5, ge=5, le=1440)
    pulsescore_minutes: int = Field(5, ge=5, le=1440)
    odds_stale_minutes: int = Field(15, ge=5, le=1440)
    betfair_fallback: bool = True

    @field_validator("top_n")
    @classmethod
    def top_size(cls, value):
        if value not in {0, 5, 10, 20}:
            raise ValueError("Top: 5, 10, 20 o 0 (todos)")
        return value
