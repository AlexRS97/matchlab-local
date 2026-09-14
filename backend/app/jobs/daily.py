import json
from datetime import UTC, datetime, timedelta

from app.core.config import read_config
from app.db.connection import Database, encode


class DailyAnalysis:
    """Persistent daily analysis status, separate from model training cadence."""

    def __init__(self, db: Database, timezone):
        self.db, self.timezone = db, timezone
        self.hour = int(read_config("refresh").get("daily_analysis_hour", 6))

    def last(self) -> dict | None:
        rows = self.db.query("SELECT payload FROM settings WHERE key='daily_analysis'")
        return json.loads(rows[0]["payload"]) if rows else None

    def due(self, now: datetime) -> bool:
        local = now.astimezone(self.timezone)
        last = self.last()
        return local.hour >= self.hour and (not last or last["date"] != local.date().isoformat())

    def record(self, job: dict, fixtures: int, analysed: int):
        if datetime.fromisoformat(job["started_at"]).astimezone(
            self.timezone
        ).hour < self.hour and not job.get("force_analysis"):
            return
        self.db.execute(
            "INSERT OR REPLACE INTO settings VALUES ('daily_analysis',?)",
            [
                encode(
                    {
                        "date": job["date"],
                        "started_at": job.get("started_at"),
                        "finished_at": job["finished_at"],
                        "status": "partial"
                        if job["errors"] and fixtures
                        else "unavailable"
                        if job["errors"]
                        else "complete",
                        "fixtures": fixtures,
                        "analysed": analysed,
                        "errors": job["errors"],
                    }
                )
            ],
        )

    def status(self, now: datetime | None = None) -> dict:
        local = (now or datetime.now(UTC)).astimezone(self.timezone)
        next_run = local.replace(hour=self.hour, minute=0, second=0, microsecond=0)
        if next_run <= local:
            next_run += timedelta(days=1)
        return {
            "hour": self.hour,
            "timezone": str(self.timezone),
            "next_scheduled_at": next_run.isoformat(),
            "last": self.last(),
            "due": self.due(local),
        }
