"""Finite worker explicitly started by the user when the API is closed."""

import asyncio
from datetime import datetime

from app.core.config import Settings
from app.core.logging import configure_logging
from app.db.connection import Database, encode
from app.services.runtime import AnalyticsRuntime


async def main():
    configure_logging()
    settings = Settings(enable_scheduler=False)
    db = Database(settings.duckdb_path)
    runtime = AnalyticsRuntime(settings, db)
    try:
        runtime.start_refresh(datetime.now(settings.timezone).date(), force_analysis=True)
        runtime.learning.start()
        assert runtime.task is not None and runtime.learning.task is not None
        await asyncio.gather(runtime.task, runtime.learning.task)
        print(
            encode({"daily_analysis": runtime.daily.status(), "learning": runtime.learning.job}),
            flush=True,
        )
    finally:
        await runtime.close()
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
