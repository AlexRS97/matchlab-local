from datetime import date, datetime

from celery import Celery
from celery.schedules import crontab

from football_api.config import get_settings
from football_api.database import SessionLocal
from football_api.services.ingestion import IngestionService

settings = get_settings()
celery_app = Celery("football_analytics", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    timezone=settings.app_timezone,
    enable_utc=True,
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "daily-football-ingestion": {
            "task": "football.ingest_date",
            "schedule": crontab(hour=5, minute=0),
        },
        "refresh-todays-fixtures": {
            "task": "football.ingest_today",
            "schedule": crontab(minute="*/30"),
        },
    },
)


@celery_app.task(name="football.ingest_date")
def ingest_date(target_date: str) -> dict:
    with SessionLocal() as db:
        job = IngestionService(db, settings).run_daily(date.fromisoformat(target_date))
        return {"job_id": job.id, "status": job.status, "fixtures": job.fixtures_found}


@celery_app.task(name="football.ingest_today")
def ingest_today() -> dict:
    return ingest_date(datetime.now(settings.timezone).date().isoformat())
