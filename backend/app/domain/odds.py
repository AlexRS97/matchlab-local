from enum import StrEnum

from pydantic import AwareDatetime, BaseModel, Field, model_validator

from app.domain.market import Market


class Bookmaker(StrEnum):
    BETFAIR = "BETFAIR"
    BET365 = "BET365"
    WINAMAX = "WINAMAX"


class NormalizedOdds(BaseModel):
    provider: str
    bookmaker: Bookmaker
    fixture_id: int | None = None
    provider_event_id: str
    market: Market
    line: float | None = None
    selection: str
    decimal_odds: float = Field(gt=1, allow_inf_nan=False)
    timestamp: AwareDatetime
    is_live: bool = False
    source_url: str | None = None
    best_back_price: float | None = Field(None, gt=1, allow_inf_nan=False)
    best_lay_price: float | None = Field(None, gt=1, allow_inf_nan=False)
    is_manual: bool = False
    is_delayed: bool = False
    source_label: str | None = None

    @model_validator(mode="after")
    def valid_market(self) -> "NormalizedOdds":
        if self.line != self.market.line:
            raise ValueError("La línea no corresponde al mercado")
        allowed = {"YES", "NO"} if self.market.line is None else {"OVER", "UNDER"}
        if self.selection not in allowed:
            raise ValueError("Selección incompatible con el mercado")
        if self.best_back_price is not None and self.decimal_odds != self.best_back_price:
            raise ValueError("El precio Exchange debe ser el best back")
        return self


class ProviderEvent(BaseModel):
    provider: str
    provider_event_id: str
    home_team: str
    away_team: str
    competition: str
    kickoff_utc: AwareDatetime
    bookmaker: Bookmaker
    home_provider_id: str | None = None
    away_provider_id: str | None = None
    odds: list[NormalizedOdds] = Field(default_factory=list)
    observed_at: AwareDatetime | None = None
