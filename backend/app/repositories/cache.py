import json
from datetime import UTC, datetime, timedelta

from app.db.connection import Database, encode


class CacheRepository:
    def __init__(self, db: Database):
        self.db = db

    def get(self, key: str, *, stale: bool = False, now: datetime | None = None) -> dict | None:
        rows = self.db.query("SELECT * FROM analysis_cache WHERE cache_key = ?", [key])
        if not rows:
            return None
        row = rows[0]
        expired = row["expires_at"] <= (now or datetime.now(UTC))
        if expired and not stale:
            return None
        return {
            "data": json.loads(row["payload"]),
            "stale": expired,
            "updated_at": row["created_at"],
            "expires_at": row["expires_at"],
        }

    def put(self, key: str, provider: str, data, ttl: float, now: datetime | None = None):
        now = now or datetime.now(UTC)
        self.db.execute(
            "INSERT OR REPLACE INTO analysis_cache VALUES (?, ?, ?, ?, ?)",
            [key, provider, now, now + timedelta(seconds=ttl), encode(data)],
        )
