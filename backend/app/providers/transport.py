import asyncio
import hashlib
import json
import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime

import httpx

from app.core.exceptions import CircuitOpen, ProviderError, QuotaExceeded
from app.db.connection import Database
from app.providers.usage import ApiUsageTracker
from app.repositories.cache import CacheRepository

log = logging.getLogger("matchlab")


class ProviderTransport:
    def __init__(
        self,
        name: str,
        db: Database,
        client: httpx.AsyncClient,
        usage: ApiUsageTracker,
        attempts: int = 3,
        cooldown: int = 120,
        min_interval: float = 0,
    ):
        self.name, self.db, self.client, self.usage = name, db, client, usage
        self.cache = CacheRepository(db)
        self.attempts, self.cooldown, self.min_interval = attempts, cooldown, min_interval
        self.last_response_at = datetime.now(UTC)
        self.last_stale = False
        self.last_sent = 0.0
        self.lock = asyncio.Lock()

    def status(self) -> dict:
        rows = self.db.query("SELECT * FROM provider_status WHERE provider=?", [self.name])
        return {**self.usage.status(), **(rows[0] if rows else {})}

    def error(self, message: str, retry_after: float | None = None):
        now = datetime.now(UTC)
        state = self.status()
        failures = state.get("failures", 0) + 1
        until = (
            now + timedelta(seconds=retry_after or self.cooldown)
            if failures >= 3 or retry_after
            else None
        )
        self.db.execute(
            """INSERT INTO provider_status VALUES (?, NULL, ?, ?, ?, ?)
          ON CONFLICT(provider) DO UPDATE SET last_error=excluded.last_error, failures=excluded.failures,
          circuit_until=excluded.circuit_until, last_request=excluded.last_request""",
            [self.name, message, failures, until, now],
        )

    def success(self):
        now = datetime.now(UTC)
        self.db.execute(
            """INSERT INTO provider_status VALUES (?, ?, NULL, 0, NULL, ?)
          ON CONFLICT(provider) DO UPDATE SET last_success=excluded.last_success, last_error=NULL,
          failures=0, circuit_until=NULL, last_request=excluded.last_request""",
            [self.name, now, now],
        )

    @staticmethod
    def retry_seconds(value: str | None) -> float:
        try:
            return max(1, float(value or "60"))
        except ValueError:
            try:
                return max(
                    1, (parsedate_to_datetime(value or "") - datetime.now(UTC)).total_seconds()
                )
            except (TypeError, ValueError):
                return 60

    async def request(
        self,
        method: str,
        endpoint: str,
        *,
        ttl: float = 0,
        params=None,
        body=None,
        headers=None,
        validator: Callable | None = None,
        allow_stale: bool = True,
    ):
        signature = json.dumps([method, endpoint, params, body], sort_keys=True, default=str)
        key = self.name + ":" + hashlib.sha256(signature.encode()).hexdigest()
        async with self.lock:
            cached = self.cache.get(key) if ttl else None
            if cached:
                self.last_response_at, self.last_stale = cached["updated_at"], False
                log.info(
                    "provider_cache",
                    extra={
                        "provider": self.name,
                        "endpoint": endpoint,
                        "cache_hit": True,
                        "status": "cached",
                        "duration": 0,
                    },
                )
                return cached["data"]
            started = time.monotonic()
            try:
                state = self.status()
                if state.get("circuit_until") and state["circuit_until"] > datetime.now(UTC):
                    raise CircuitOpen(
                        f"{self.name}: circuito abierto hasta {state['circuit_until'].isoformat()}"
                    )
                for attempt in range(self.attempts):
                    await asyncio.sleep(
                        max(0, self.min_interval - (time.monotonic() - self.last_sent))
                    )
                    self.usage.consume()
                    self.last_sent = time.monotonic()
                    try:
                        response = await self.client.request(
                            method, endpoint, params=params, json=body, headers=headers
                        )
                        self.usage.remaining(response.headers.get("x-ratelimit-requests-remaining"))
                        minute_limit = response.headers.get("x-ratelimit-limit")
                        if minute_limit and minute_limit.isdigit():
                            self.min_interval = max(
                                self.min_interval, 60 / max(1, int(minute_limit))
                            )
                        if response.status_code == 429:
                            delay = self.retry_seconds(response.headers.get("Retry-After"))
                            self.error(f"{self.name}: HTTP 429; límite de peticiones", delay)
                            raise QuotaExceeded(
                                f"{self.name}: HTTP 429; reintento después de {delay:.0f}s"
                            )
                        if response.status_code >= 500:
                            raise httpx.HTTPStatusError(
                                "upstream", request=response.request, response=response
                            )
                        if response.status_code >= 400:
                            raise ProviderError(
                                f"{self.name}: HTTP {response.status_code} en {endpoint}"
                            )
                        data = response.json()
                        if validator:
                            validator(data)
                        self.success()
                        self.last_response_at, self.last_stale = datetime.now(UTC), False
                        if ttl:
                            self.cache.put(key, self.name, data, ttl, self.last_response_at)
                        log.info(
                            "provider_request",
                            extra={
                                "provider": self.name,
                                "endpoint": endpoint,
                                "duration": round(time.monotonic() - started, 3),
                                "status": "ok",
                                "cache_hit": False,
                            },
                        )
                        return data
                    except (httpx.HTTPError, ValueError) as exc:
                        if attempt + 1 == self.attempts:
                            raise ProviderError(
                                f"{self.name}: {type(exc).__name__} en {endpoint}"
                            ) from None
                        await asyncio.sleep(2**attempt)
                raise ProviderError(f"{self.name}: respuesta no disponible")
            except ProviderError as exc:
                if not isinstance(exc, (CircuitOpen, QuotaExceeded)):
                    self.error(str(exc))
                elif isinstance(exc, QuotaExceeded) and "429" not in str(exc):
                    self.error(str(exc))
                stale = self.cache.get(key, stale=True) if ttl and allow_stale else None
                log.warning(
                    "provider_failure",
                    extra={
                        "provider": self.name,
                        "endpoint": endpoint,
                        "error": str(exc),
                        "status": "stale" if stale else "error",
                        "cache_hit": bool(stale),
                    },
                )
                if stale:
                    self.last_response_at, self.last_stale = stale["updated_at"], True
                    return stale["data"]
                raise

    async def close(self):
        await self.client.aclose()
