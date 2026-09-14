import asyncio
import logging
from datetime import UTC, datetime

log = logging.getLogger("matchlab")


class Scheduler:
    def __init__(self, runtime):
        self.runtime = runtime
        self.task: asyncio.Task | None = None
        self.next_odds = {
            "betfair": datetime.min.replace(tzinfo=UTC),
            "pulsescore": datetime.min.replace(tzinfo=UTC),
        }
        self.next_fixtures = datetime.min.replace(tzinfo=UTC)

    def start(self):
        self.task = asyncio.create_task(self.run())

    async def run(self):
        from datetime import timedelta

        r = self.runtime
        while True:
            try:
                now = datetime.now(UTC)
                target = now.astimezone(r.settings.timezone).date()
                r.learning.daily_tick(now, r.settings.timezone)
                settings = r.user_settings.get()
                if not r.job["running"]:
                    if (
                        now >= self.next_fixtures
                        or r.job.get("date") != target.isoformat()
                        or r.daily.due(now)
                    ):
                        r.start_refresh(target)
                        self.next_fixtures = now + timedelta(minutes=settings.fixtures_minutes)
                    else:
                        for provider in ("betfair", "pulsescore"):
                            if now >= self.next_odds[provider]:
                                await r.refresh_odds(target, provider)
                                self.next_odds[provider] = now + timedelta(
                                    minutes=getattr(settings, f"{provider}_minutes")
                                )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                message = f"Actualización automática: {type(exc).__name__}; revisar logs"
                r.job["errors"] = list(dict.fromkeys(r.job["errors"] + [message]))
                log.error("scheduler_error", extra={"error": type(exc).__name__})
            await asyncio.sleep(30)

    async def close(self):
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
