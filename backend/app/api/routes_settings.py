from fastapi import APIRouter, Request

from app.domain.settings import UserSettings

router = APIRouter(prefix="/api")


@router.get("/settings")
def get_settings(request: Request):
    return request.app.state.runtime.user_settings.get()


@router.put("/settings")
def put_settings(request: Request, settings: UserSettings):
    return request.app.state.runtime.user_settings.save(settings)


@router.get("/providers/status")
async def providers_status(request: Request):
    runtime = request.app.state.runtime
    providers = [
        {"configured": runtime.football.configured, **runtime.football.transport.status()},
        await runtime.betfair.health_check(),
        await runtime.pulsescore.health_check(),
    ]
    for provider in providers:
        provider["status"] = (
            "NOT_CONFIGURED"
            if not provider["configured"]
            else "ERROR"
            if provider.get("last_error")
            else "CONNECTED"
            if provider.get("last_success")
            else "NOT_CHECKED"
        )
    return {"providers": providers, "bookmakers": runtime.bookmaker_status(), "job": runtime.job}


@router.get("/performance")
def performance(request: Request):
    return request.app.state.runtime.performance.metrics()
