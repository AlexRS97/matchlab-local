from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.api.routes_fixture import detail
from app.domain.market import Market
from app.domain.odds import Bookmaker, NormalizedOdds

router = APIRouter(prefix="/api")


@router.get("/fixtures/{fixture_id}/odds")
def get_odds(request: Request, fixture_id: int):
    data = detail(request, fixture_id)
    runtime = request.app.state.runtime
    settings = runtime.user_settings.get()
    prediction = data["prediction"] or {}
    probabilities = {
        **prediction.get("goals", {}).get("probabilities", {}),
        **prediction.get("corners", {}).get("probabilities", {}),
    }
    kickoff = datetime.fromisoformat(data["fixture"]["kickoff_utc"])
    return [
        runtime.odds_service.compare(
            fixture_id,
            market,
            probabilities.get(market.value),
            settings.odds_stale_minutes,
            settings.enabled_bookmakers,
            before=kickoff,
        )
        for market in Market
    ]


class ManualPrice(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fixture_id: int
    bookmaker: Bookmaker
    market: Market
    line: float | None = None
    odds: float = Field(gt=1, le=10000, allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_line(self):
        if self.line != self.market.line:
            raise ValueError("La línea no corresponde al mercado seleccionado")
        return self


@router.post("/odds/manual", status_code=201)
def manual_odds(request: Request, price: ManualPrice):
    runtime = request.app.state.runtime
    try:
        entered = runtime.manual.enter(
            NormalizedOdds(
                provider="manual",
                bookmaker=price.bookmaker,
                fixture_id=price.fixture_id,
                provider_event_id=str(price.fixture_id),
                market=price.market,
                line=price.line,
                selection=price.market.selection,
                decimal_odds=price.odds,
                timestamp=datetime.now(UTC),
                is_manual=True,
            )
        )
        return entered
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
