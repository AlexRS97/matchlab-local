from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/api/fixtures")


def detail(request: Request, fixture_id: int):
    runtime = request.app.state.runtime
    fixture = runtime.fixtures.get(fixture_id)
    if fixture is None:
        raise HTTPException(404, "Partido no encontrado")
    return {
        "fixture": fixture.model_dump(mode="json"),
        "prediction": runtime.predictions.latest(fixture_id, before=fixture.kickoff_utc),
    }


@router.get("/{fixture_id}")
def get_fixture(request: Request, fixture_id: int):
    return detail(request, fixture_id)


@router.get("/{fixture_id}/goals")
def get_goals(request: Request, fixture_id: int):
    prediction = detail(request, fixture_id)["prediction"]
    return prediction.get("goals") if prediction else None


@router.get("/{fixture_id}/corners")
def get_corners(request: Request, fixture_id: int):
    prediction = detail(request, fixture_id)["prediction"]
    return prediction.get("corners") if prediction else None


@router.get("/{fixture_id}/analysis")
def get_analysis(request: Request, fixture_id: int):
    from app.domain.market import Market
    from app.services.analysis_service import AnalysisGenerator

    data = detail(request, fixture_id)
    runtime = request.app.state.runtime
    settings = runtime.user_settings.get()
    prediction = data["prediction"]
    probability = (
        (prediction or {})
        .get("goals", {})
        .get("probabilities", {})
        .get(Market.OVER_2_5_GOALS.value)
    )
    comparison = runtime.odds_service.compare(
        fixture_id,
        Market.OVER_2_5_GOALS,
        probability,
        settings.odds_stale_minutes,
        settings.enabled_bookmakers,
        before=runtime.fixtures.get(fixture_id).kickoff_utc,
    )
    return AnalysisGenerator().generate(prediction, comparison)
