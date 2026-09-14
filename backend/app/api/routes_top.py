from datetime import date, datetime, time
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request

from app.domain.market import Market

router = APIRouter(prefix="/api")


@router.get("/top")
def top(
    request: Request,
    target_date: date | None = Query(None, alias="date"),
    market: str = "over_2_5",
    bookmaker: Literal[
        "all", "betfair", "bet365", "winamax", "ALL", "BETFAIR", "BET365", "WINAMAX"
    ] = "all",
    min_odds: float | None = Query(None, gt=1),
    max_odds: float | None = Query(None, gt=1),
    min_probability: float = Query(0, ge=0, le=1),
    min_edge: float | None = Query(None, ge=-1, le=1),
    min_ev: float | None = Query(None, ge=-1),
    top_n: int | None = Query(None, ge=0, le=500),
    min_confidence: Literal["INSUFFICIENT", "LOW", "MEDIUM", "HIGH", "VERY_HIGH"] | None = None,
    min_quality: Literal["INSUFFICIENT", "LOW", "ACCEPTABLE", "GOOD", "EXCELLENT"] | None = None,
    country: str | None = None,
    league_id: int | None = None,
    search: str = "",
    kickoff_from: time | None = None,
    kickoff_to: time | None = None,
):
    runtime = request.app.state.runtime
    target = target_date or datetime.now(runtime.settings.timezone).date()
    try:
        canonical = Market.parse(market)
    except ValueError:
        raise HTTPException(422, "Mercado no reconocido") from None
    settings = runtime.user_settings.get()
    rows = runtime.dashboard.rows(target, settings)
    if country:
        rows = [row for row in rows if row["country"] == country]
    if league_id is not None:
        rows = [row for row in rows if row["league_id"] == league_id]
    if search:
        rows = [
            row
            for row in rows
            if runtime.matcher.search(search, runtime.fixtures.get(row["fixture_id"]))
        ]
    rows = [
        row
        for row in rows
        if (
            kickoff_from is None
            or datetime.fromisoformat(row["kickoff_local"]).time() >= kickoff_from
        )
        and (
            kickoff_to is None or datetime.fromisoformat(row["kickoff_local"]).time() <= kickoff_to
        )
    ]
    return runtime.dashboard.ranking.rank(
        rows,
        canonical,
        settings,
        bookmaker=bookmaker.upper(),
        min_odds=min_odds,
        max_odds=max_odds,
        min_probability=min_probability,
        min_edge=min_edge,
        min_ev=min_ev,
        top_n=top_n,
        min_confidence=min_confidence,
        min_quality=min_quality,
    )
