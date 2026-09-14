from datetime import UTC, date, datetime

from fastapi import APIRouter, Query, Request

router = APIRouter(prefix="/api")


@router.get("/today")
async def today(request: Request, target_date: date | None = Query(None, alias="date")):
    runtime = request.app.state.runtime
    target = target_date or datetime.now(runtime.settings.timezone).date()
    if runtime.settings.enable_scheduler and not runtime.job["running"]:
        last_requested = runtime.requested_dates.get(target)
        if (
            last_requested is None
            or (datetime.now(UTC) - last_requested).total_seconds()
            > runtime.user_settings.get().fixtures_minutes * 60
        ):
            runtime.start_refresh(target)
    return {
        **runtime.dashboard.today(target, runtime.user_settings.get()),
        "job": runtime.job,
        "daily_analysis": runtime.daily.status(),
    }


@router.post("/refresh", status_code=202)
async def refresh(request: Request, target_date: date | None = Query(None, alias="date")):
    runtime = request.app.state.runtime
    return runtime.start_refresh(target_date or datetime.now(runtime.settings.timezone).date())


@router.get("/leagues")
def leagues(request: Request):
    return request.app.state.runtime.fixtures.leagues()


@router.post("/refresh/daily", status_code=202)
async def daily_refresh(request: Request):
    runtime = request.app.state.runtime
    runtime.learning.start()
    return runtime.start_refresh(
        datetime.now(runtime.settings.timezone).date(), force_analysis=True
    )


@router.get("/refresh/status")
def refresh_status(request: Request):
    runtime = request.app.state.runtime
    return {
        "job": runtime.job,
        "daily_analysis": runtime.daily.status(),
        "scheduler_enabled": runtime.settings.enable_scheduler,
        "learning": runtime.learning.job,
        "odds": runtime.odds_job,
    }
