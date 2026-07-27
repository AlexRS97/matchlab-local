from dataclasses import asdict
from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from football_api.config import Settings, get_settings
from football_api.database import get_db
from football_api.models import Competition, Fixture, IngestionJob, OddsSnapshot, Prediction, Team
from football_api.schemas import (
    CompetitionSummary,
    DailyAnalysisResponse,
    DataQualityResponse,
    FixtureResponse,
    JobQueuedResponse,
    JobResponse,
    PredictionResponse,
    RecommendationResponse,
    TeamFormMatch,
    TeamFormResponse,
    TeamInsightResponse,
    TeamSummary,
)
from football_api.services.competition_coverage import competition_priority, competition_region
from football_api.services.ingestion import IngestionService
from football_api.services.persistence import FINISHED_STATUSES
from football_api.services.predictions import PredictionService
from football_api.services.recommendations import build_recommendations, build_team_insights

router = APIRouter(prefix="/api/v1")
DbDependency = Annotated[Session, Depends(get_db)]
SettingsDependency = Annotated[Settings, Depends(get_settings)]


def _date_bounds(target_date: date, settings: Settings) -> tuple[datetime, datetime]:
    local_start = datetime.combine(target_date, time.min, tzinfo=settings.timezone)
    local_end = datetime.combine(target_date, time.max, tzinfo=settings.timezone)
    return local_start.astimezone(UTC), local_end.astimezone(UTC)


def _latest_prediction(fixture: Fixture) -> Prediction | None:
    return max(fixture.predictions, key=lambda item: item.generated_at, default=None)


def _prediction_response(
    prediction: Prediction | None,
    fixture: Fixture,
    odds: list[OddsSnapshot] | None = None,
) -> PredictionResponse | None:
    if prediction is None:
        return None
    total_corners = None
    if (
        prediction.home_expected_corners is not None
        and prediction.away_expected_corners is not None
    ):
        total_corners = round(
            prediction.home_expected_corners + prediction.away_expected_corners, 2
        )
    return PredictionResponse(
        id=prediction.id,
        generated_at=prediction.generated_at,
        model_version=prediction.model_version,
        home_expected_goals=prediction.home_expected_goals,
        away_expected_goals=prediction.away_expected_goals,
        total_expected_goals=round(
            prediction.home_expected_goals + prediction.away_expected_goals, 2
        ),
        home_expected_corners=prediction.home_expected_corners,
        away_expected_corners=prediction.away_expected_corners,
        total_expected_corners=total_corners,
        home_win_probability=prediction.home_win_probability,
        draw_probability=prediction.draw_probability,
        away_win_probability=prediction.away_win_probability,
        over_2_5_probability=prediction.over_2_5_probability,
        btts_probability=prediction.btts_probability,
        over_8_5_corners_probability=prediction.over_8_5_corners_probability,
        over_9_5_corners_probability=prediction.over_9_5_corners_probability,
        confidence=prediction.confidence,
        data_quality=prediction.data_quality,
        likely_scores=prediction.likely_scores,
        explanation=prediction.explanation,
        recommendations=[
            RecommendationResponse(**asdict(item))
            for item in build_recommendations(prediction, odds or [])
        ],
        team_insights=[
            TeamInsightResponse(**asdict(item))
            for item in build_team_insights(fixture, prediction)
        ],
    )


def _fixture_response(
    fixture: Fixture,
    odds: list[OddsSnapshot] | None = None,
) -> FixtureResponse:
    priority = competition_priority(
        fixture.competition.name,
        fixture.competition.country,
        fixture.competition.coverage,
        fixture.competition.is_friendly,
    )
    return FixtureResponse(
        id=fixture.id,
        provider_id=fixture.provider_id,
        kickoff_at=fixture.kickoff_at,
        status=fixture.status,
        status_long=fixture.status_long,
        round_name=fixture.round_name,
        venue_name=fixture.venue_name,
        home_goals=fixture.home_goals,
        away_goals=fixture.away_goals,
        home_team=TeamSummary(
            id=fixture.home_team.id,
            name=fixture.home_team.name,
            logo_url=fixture.home_team.logo_url,
        ),
        away_team=TeamSummary(
            id=fixture.away_team.id,
            name=fixture.away_team.name,
            logo_url=fixture.away_team.logo_url,
        ),
        competition=CompetitionSummary(
            id=fixture.competition.id,
            name=fixture.competition.name,
            country=fixture.competition.country,
            logo_url=fixture.competition.logo_url,
            is_friendly=fixture.competition.is_friendly,
            region=competition_region(
                fixture.competition.name,
                fixture.competition.country,
            ),
            priority=priority,
        ),
        prediction=_prediction_response(_latest_prediction(fixture), fixture, odds),
    )


def _fixtures_for_date(db: Session, target_date: date, settings: Settings) -> list[Fixture]:
    start, end = _date_bounds(target_date, settings)
    start = max(start, datetime.now(UTC))
    return db.scalars(
        select(Fixture)
        .options(
            selectinload(Fixture.home_team),
            selectinload(Fixture.away_team),
            selectinload(Fixture.competition),
            selectinload(Fixture.predictions),
        )
        .where(
            Fixture.kickoff_at.between(start, end),
            Fixture.status.in_({"NS", "TBD"}),
        )
        .order_by(Fixture.kickoff_at)
    ).all()


def _odds_by_fixture(
    db: Session,
    fixture_ids: list[int],
) -> dict[int, list[OddsSnapshot]]:
    if not fixture_ids:
        return {}
    rows = db.scalars(
        select(OddsSnapshot)
        .where(
            OddsSnapshot.fixture_id.in_(fixture_ids),
            OddsSnapshot.captured_at >= datetime.now(UTC) - timedelta(hours=24),
        )
        .order_by(OddsSnapshot.captured_at.desc())
    ).all()
    grouped: dict[int, list[OddsSnapshot]] = {}
    for row in rows:
        grouped.setdefault(row.fixture_id, []).append(row)
    return grouped


def _has_stored_fixture_for_date(
    db: Session,
    target_date: date,
    settings: Settings,
) -> bool:
    start, end = _date_bounds(target_date, settings)
    return (
        db.scalar(
            select(Fixture.id)
            .where(Fixture.kickoff_at.between(start, end))
            .limit(1)
        )
        is not None
    )


@router.get("/fixtures", response_model=list[FixtureResponse])
def list_fixtures(
    db: DbDependency,
    settings: SettingsDependency,
    target_date: date | None = Query(default=None, alias="date"),
) -> list[FixtureResponse]:
    target_date = target_date or datetime.now(settings.timezone).date()
    fixtures = _fixtures_for_date(db, target_date, settings)
    odds = _odds_by_fixture(db, [fixture.id for fixture in fixtures])
    return [_fixture_response(fixture, odds.get(fixture.id)) for fixture in fixtures]


@router.get("/fixtures/{fixture_id}", response_model=FixtureResponse)
def get_fixture(fixture_id: int, db: DbDependency) -> FixtureResponse:
    fixture = db.scalar(
        select(Fixture)
        .options(
            selectinload(Fixture.home_team),
            selectinload(Fixture.away_team),
            selectinload(Fixture.competition),
            selectinload(Fixture.predictions),
        )
        .where(Fixture.id == fixture_id)
    )
    if fixture is None:
        raise HTTPException(status_code=404, detail="Partido no encontrado")
    odds = _odds_by_fixture(db, [fixture.id])
    return _fixture_response(fixture, odds.get(fixture.id))


@router.get("/fixtures/{fixture_id}/analysis", response_model=PredictionResponse)
@router.get("/fixtures/{fixture_id}/predictions", response_model=PredictionResponse)
def get_analysis(fixture_id: int, db: DbDependency) -> PredictionResponse:
    fixture = db.scalar(
        select(Fixture)
        .options(
            selectinload(Fixture.home_team),
            selectinload(Fixture.away_team),
            selectinload(Fixture.competition),
        )
        .where(Fixture.id == fixture_id)
    )
    if fixture is None:
        raise HTTPException(status_code=404, detail="Partido no encontrado")
    prediction = db.scalar(
        select(Prediction)
        .where(Prediction.fixture_id == fixture_id)
        .order_by(Prediction.generated_at.desc())
        .limit(1)
    )
    if prediction is None:
        prediction = PredictionService(db).generate_for_fixture(fixture)
        db.commit()
    odds = _odds_by_fixture(db, [fixture.id])
    response = _prediction_response(prediction, fixture, odds.get(fixture.id))
    if response is None:
        raise HTTPException(status_code=500, detail="No se pudo generar el analisis")
    return response


@router.get("/daily-analysis", response_model=DailyAnalysisResponse)
def daily_analysis(
    db: DbDependency,
    settings: SettingsDependency,
    target_date: date | None = Query(default=None, alias="date"),
) -> DailyAnalysisResponse:
    target_date = target_date or datetime.now(settings.timezone).date()
    fixtures = _fixtures_for_date(db, target_date, settings)
    if (
        not fixtures
        and settings.app_demo_mode
        and not _has_stored_fixture_for_date(db, target_date, settings)
    ):
        IngestionService(db, settings).run_daily(target_date)
        fixtures = _fixtures_for_date(db, target_date, settings)
    odds = _odds_by_fixture(db, [fixture.id for fixture in fixtures])
    responses = [_fixture_response(fixture, odds.get(fixture.id)) for fixture in fixtures]
    analyzed = [fixture for fixture in responses if fixture.prediction]
    latest_job = db.scalar(
        select(IngestionJob)
        .where(
            IngestionJob.target_date == target_date,
            IngestionJob.status == "completed",
        )
        .order_by(IngestionJob.finished_at.desc())
        .limit(1)
    )
    return DailyAnalysisResponse(
        date=target_date,
        timezone=settings.app_timezone,
        total_fixtures=len(responses),
        analyzed_fixtures=len(analyzed),
        high_confidence_fixtures=sum(
            1
            for fixture in analyzed
            if fixture.prediction and fixture.prediction.confidence >= 0.75
        ),
        recommended_fixtures=sum(
            1
            for fixture in analyzed
            if fixture.prediction and fixture.prediction.recommendations
        ),
        demo_mode=not bool(settings.api_football_key),
        automatic_refresh=(
            settings.enable_scheduled_ingestion and bool(settings.api_football_key)
        ),
        automatic_refresh_hours=settings.automatic_refresh_hours,
        last_updated_at=latest_job.finished_at if latest_job else None,
        fixtures=responses,
    )


@router.get("/competitions", response_model=list[CompetitionSummary])
def competitions(db: DbDependency) -> list[CompetitionSummary]:
    rows = db.scalars(select(Competition).order_by(Competition.country, Competition.name)).all()
    return [
        CompetitionSummary(
            id=row.id,
            name=row.name,
            country=row.country,
            logo_url=row.logo_url,
            is_friendly=row.is_friendly,
            region=competition_region(row.name, row.country),
            priority=competition_priority(
                row.name,
                row.country,
                row.coverage,
                row.is_friendly,
            ),
        )
        for row in rows
    ]


@router.get("/teams/{team_id}/form", response_model=TeamFormResponse)
def team_form(team_id: int, db: DbDependency) -> TeamFormResponse:
    team = db.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    fixtures = db.scalars(
        select(Fixture)
        .options(selectinload(Fixture.home_team), selectinload(Fixture.away_team))
        .where(
            Fixture.status.in_(FINISHED_STATUSES),
            or_(Fixture.home_team_id == team_id, Fixture.away_team_id == team_id),
        )
        .order_by(Fixture.kickoff_at.desc())
        .limit(10)
    ).all()
    matches = []
    for fixture in fixtures:
        is_home = fixture.home_team_id == team_id
        goals_for = fixture.home_goals if is_home else fixture.away_goals
        goals_against = fixture.away_goals if is_home else fixture.home_goals
        if goals_for is None or goals_against is None:
            continue
        result = "W" if goals_for > goals_against else "D" if goals_for == goals_against else "L"
        matches.append(
            TeamFormMatch(
                fixture_id=fixture.id,
                kickoff_at=fixture.kickoff_at,
                opponent=fixture.away_team.name if is_home else fixture.home_team.name,
                venue="home" if is_home else "away",
                goals_for=goals_for,
                goals_against=goals_against,
                result=result,
            )
        )
    return TeamFormResponse(
        team=TeamSummary(id=team.id, name=team.name, logo_url=team.logo_url), matches=matches
    )


@router.get("/value-opportunities")
def value_opportunities(
    db: DbDependency,
    settings: SettingsDependency,
    target_date: date | None = Query(default=None, alias="date"),
) -> list[dict]:
    target_date = target_date or datetime.now(settings.timezone).date()
    fixtures = _fixtures_for_date(db, target_date, settings)
    opportunities = []
    for fixture in fixtures:
        prediction = _latest_prediction(fixture)
        if prediction is None or prediction.confidence < 0.55:
            continue
        latest_odds = db.scalars(
            select(OddsSnapshot)
            .where(OddsSnapshot.fixture_id == fixture.id)
            .order_by(OddsSnapshot.captured_at.desc())
            .limit(50)
        ).all()
        probabilities = {
            "Over 2.5": prediction.over_2_5_probability,
            "BTTS Yes": prediction.btts_probability,
            "Home": prediction.home_win_probability,
            "Draw": prediction.draw_probability,
            "Away": prediction.away_win_probability,
        }
        for odd in latest_odds:
            probability = probabilities.get(odd.selection)
            if probability is None:
                continue
            expected_value = probability * float(odd.decimal_odds) - 1
            if expected_value >= 0.05:
                opportunities.append(
                    {
                        "fixture_id": fixture.id,
                        "match": f"{fixture.home_team.name} - {fixture.away_team.name}",
                        "bookmaker": odd.bookmaker,
                        "selection": odd.selection,
                        "decimal_odds": float(odd.decimal_odds),
                        "model_probability": probability,
                        "expected_value": round(expected_value, 4),
                        "confidence": prediction.confidence,
                    }
                )
    return opportunities


@router.get("/models/performance")
def model_performance(db: DbDependency) -> dict:
    settled = db.execute(
        select(Prediction, Fixture)
        .join(Fixture, Prediction.fixture_id == Fixture.id)
        .where(
            Fixture.status.in_(FINISHED_STATUSES),
            Fixture.home_goals.is_not(None),
            Fixture.away_goals.is_not(None),
        )
    ).all()
    if not settled:
        return {"model_version": "baseline-poisson-nb-v2", "settled_predictions": 0}
    errors = [
        abs(
            (prediction.home_expected_goals + prediction.away_expected_goals)
            - (fixture.home_goals + fixture.away_goals)
        )
        for prediction, fixture in settled
    ]
    return {
        "model_version": "baseline-poisson-nb-v2",
        "settled_predictions": len(settled),
        "goals_mae": round(sum(errors) / len(errors), 4),
        "warning": (
            "El ROI no se muestra hasta disponer de cuotas "
            "y una muestra temporal suficiente."
        ),
    }


@router.post("/admin/ingestion/run", response_model=JobQueuedResponse, status_code=202)
def run_ingestion(
    settings: SettingsDependency,
    target_date: date | None = Query(default=None, alias="date"),
) -> JobQueuedResponse:
    from football_api.worker import ingest_date

    target_date = target_date or datetime.now(settings.timezone).date()
    task = ingest_date.delay(target_date.isoformat())
    return JobQueuedResponse(task_id=task.id)


@router.post(
    "/admin/ingestion/run-if-stale",
    response_model=JobQueuedResponse,
    status_code=202,
)
def run_ingestion_if_stale() -> JobQueuedResponse:
    from football_api.worker import ingest_today_if_stale

    task = ingest_today_if_stale.delay()
    return JobQueuedResponse(task_id=task.id)


@router.post("/admin/predictions/generate")
def generate_predictions(
    db: DbDependency,
    settings: SettingsDependency,
    target_date: date | None = Query(default=None, alias="date"),
) -> dict:
    target_date = target_date or datetime.now(settings.timezone).date()
    fixtures = _fixtures_for_date(db, target_date, settings)
    service = PredictionService(db)
    for fixture in fixtures:
        service.generate_for_fixture(fixture)
    db.commit()
    return {"generated": len(fixtures), "date": target_date}


@router.post("/admin/models/train")
def train_model() -> dict:
    return {
        "status": "baseline_active",
        "model_version": "baseline-poisson-nb-v2",
        "message": (
            "El baseline no requiere entrenamiento. "
            "Anade datos y valida antes de ML supervisado."
        ),
    }


@router.get("/admin/jobs", response_model=list[JobResponse])
def list_jobs(db: DbDependency) -> list[IngestionJob]:
    return db.scalars(select(IngestionJob).order_by(IngestionJob.id.desc()).limit(50)).all()


@router.get("/admin/data-quality", response_model=DataQualityResponse)
def data_quality(
    db: DbDependency,
    settings: SettingsDependency,
    target_date: date | None = Query(default=None, alias="date"),
) -> DataQualityResponse:
    target_date = target_date or datetime.now(settings.timezone).date()
    fixtures = _fixtures_for_date(db, target_date, settings)
    predictions = [_latest_prediction(fixture) for fixture in fixtures]
    with_prediction = [prediction for prediction in predictions if prediction]
    return DataQualityResponse(
        date=target_date,
        fixtures=len(fixtures),
        with_prediction=len(with_prediction),
        with_corner_prediction=sum(
            1 for prediction in with_prediction if prediction.home_expected_corners is not None
        ),
        high_quality=sum(1 for prediction in with_prediction if prediction.data_quality == "alta"),
        coverage_percentage=round(100 * len(with_prediction) / len(fixtures), 2) if fixtures else 0,
    )
