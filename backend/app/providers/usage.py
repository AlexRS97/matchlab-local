from datetime import UTC, datetime, timedelta

from app.core.exceptions import QuotaExceeded
from app.db.connection import Database


class ApiUsageTracker:
    def __init__(
        self, db: Database, provider: str, budget: int, monthly: bool = False, reserve: int = 0
    ):
        self.db, self.provider = db, provider
        self.budget, self.monthly, self.reserve = budget, monthly, reserve

    def period(self, now: datetime) -> tuple[str, datetime]:
        if self.monthly:
            reset = (now.replace(day=28) + timedelta(days=4)).replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )
            return now.strftime("%Y-%m"), reset
        return now.date().isoformat(), (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    def status(self, now: datetime | None = None) -> dict:
        now = now or datetime.now(UTC)
        period, reset = self.period(now)
        rows = self.db.query(
            "SELECT * FROM api_usage WHERE provider=? AND period=?", [self.provider, period]
        )
        row = rows[0] if rows else {}
        used = row.get("requests", 0)
        remaining = min(
            self.budget - used,
            row.get("requests_remaining")
            if row.get("requests_remaining") is not None
            else self.budget,
        )
        today = self.db.query(
            "SELECT requests FROM api_usage WHERE provider=? AND period=?",
            [self.provider, now.date().isoformat()],
        )
        return {
            "provider": self.provider,
            "requests_period": used,
            "requests_today": today[0]["requests"] if today else 0,
            "requests_remaining": max(0, remaining),
            "last_request": row.get("last_request"),
            "reset_time": reset,
            "budget": self.budget,
            "period": "month" if self.monthly else "day",
        }

    def consume(self) -> None:
        now = datetime.now(UTC)
        with self.db.lock:
            if self.status(now)["requests_remaining"] <= self.reserve:
                raise QuotaExceeded(f"{self.provider}: presupuesto agotado; se conserva la caché")
            periods = [self.period(now)]
            if self.monthly:
                periods.append(
                    (
                        now.date().isoformat(),
                        (now + timedelta(days=1)).replace(
                            hour=0, minute=0, second=0, microsecond=0
                        ),
                    )
                )
            for period, reset in periods:
                self.db.execute(
                    """INSERT INTO api_usage VALUES (?, ?, 1, NULL, ?, ?)
                    ON CONFLICT(provider, period) DO UPDATE SET requests=api_usage.requests+1,
                    last_request=excluded.last_request""",
                    [self.provider, period, now, reset],
                )

    def remaining(self, value: str | None) -> None:
        if value is not None and value.isdigit():
            self.db.execute(
                "UPDATE api_usage SET requests_remaining=? WHERE provider=? AND period=?",
                [int(value), self.provider, self.period(datetime.now(UTC))[0]],
            )
