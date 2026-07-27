from datetime import UTC, date, datetime, timedelta

from celery import Celery
from celery.schedules import crontab
from sqlalchemy import select

from football_api.config import get_settings
from football_api.database import SessionLocal
from football_api.models import IngestionJob
from football_api.services.ingestion import IngestionService

settings = get_settings()
celery_app = Celery("football_analytics", broker=settings.redis_url, backend=settings.redis_url)
beat_schedule = {}
if settings.enable_scheduled_ingestion:
    beat_schedule = {
        "refresh-if-stale": {
            "task": "football.ingest_today_if_stale",
            "schedule": crontab(minute="*/30"),
            "args": [False],
        },
    }
celery_app.conf.update(
    timezone=settings.app_timezone,
    enable_utc=True,
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    broker_connection_retry_on_startup=True,
    beat_schedule=beat_schedule,
)


@celery_app.task(name="football.ingest_date")
def ingest_date(target_date: str) -> dict:
    with SessionLocal() as db:
        job = IngestionService(db, settings).run_daily(date.fromisoformat(target_date))
        return {"job_id": job.id, "status": job.status, "fixtures": job.fixtures_found}


@celery_app.task(name="football.ingest_today")
def ingest_today() -> dict:
    return ingest_date(datetime.now(settings.timezone).date().isoformat())


@celery_app.task(name="football.ingest_today_if_stale")
def ingest_today_if_stale(respect_freshness: bool = True) -> dict:
    if not settings.api_football_key:
        return {"status": "skipped", "reason": "API_FOOTBALL_KEY no configurada"}

    target_date = datetime.now(settings.timezone).date()
    cutoff = datetime.now(UTC) - timedelta(minutes=settings.automatic_refresh_minutes)
    with SessionLocal() as db:
        running = db.scalar(
            select(IngestionJob.id)
            .where(
                IngestionJob.target_date == target_date,
                IngestionJob.status == "running",
            )
            .limit(1)
        )
        if running is not None:
            return {"status": "skipped", "reason": "Ya hay una actualización en curso"}
        if respect_freshness:
            latest = db.scalar(
                select(IngestionJob)
                .where(
                    IngestionJob.target_date == target_date,
                    IngestionJob.status == "completed",
                    IngestionJob.message.like("Cobertura mundial:%"),
                )
                .order_by(IngestionJob.finished_at.desc())
                .limit(1)
            )
            if latest and latest.finished_at and latest.finished_at >= cutoff:
                return {
                    "status": "skipped",
                    "reason": "Los datos todavía están actualizados",
                    "last_job_id": latest.id,
                }
    return ingest_today()
