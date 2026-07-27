import time
from dataclasses import dataclass
from typing import Any

import httpx


class ProviderError(RuntimeError):
    """Error controlado al consultar el proveedor de datos."""


@dataclass(frozen=True)
class ProviderResponse:
    endpoint: str
    parameters: dict[str, Any]
    body: dict[str, Any]
    status_code: int

    @property
    def items(self) -> list[dict[str, Any]]:
        response = self.body.get("response", [])
        return response if isinstance(response, list) else []


class ApiFootballProvider:
    name = "api_football"

    def __init__(self, api_key: str, base_url: str, timeout_seconds: int = 30) -> None:
        if not api_key:
            raise ProviderError("Falta API_FOOTBALL_KEY")
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"x-apisports-key": api_key},
            timeout=timeout_seconds,
        )
        self.calls = 0
        self.daily_limit: int | None = None
        self.daily_remaining: int | None = None
        self.minute_limit: int | None = None
        self.minute_remaining: int | None = None
        self._last_request_at: float | None = None

    def close(self) -> None:
        self._client.close()

    def _get(self, endpoint: str, **parameters: Any) -> ProviderResponse:
        clean_parameters = {key: value for key, value in parameters.items() if value is not None}
        if self.minute_limit and self._last_request_at is not None:
            minimum_interval = 60 / max(1, self.minute_limit)
            elapsed = time.monotonic() - self._last_request_at
            if elapsed < minimum_interval:
                time.sleep(minimum_interval - elapsed)
        try:
            response = self._client.get(endpoint, params=clean_parameters)
            self.calls += 1
            self._last_request_at = time.monotonic()
            self._read_rate_limits(response.headers)
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError(f"Error consultando {endpoint}: {exc}") from exc

        errors = body.get("errors") if isinstance(body, dict) else None
        if errors and errors != []:
            raise ProviderError(f"API-Football devolvio errores en {endpoint}: {errors}")
        return ProviderResponse(endpoint, clean_parameters, body, response.status_code)

    @staticmethod
    def _header_int(headers: httpx.Headers, name: str) -> int | None:
        value = headers.get(name)
        try:
            return int(value) if value is not None else None
        except ValueError:
            return None

    def _read_rate_limits(self, headers: httpx.Headers) -> None:
        self.daily_limit = self._header_int(headers, "x-ratelimit-requests-limit")
        self.daily_remaining = self._header_int(headers, "x-ratelimit-requests-remaining")
        self.minute_limit = self._header_int(headers, "x-ratelimit-limit")
        self.minute_remaining = self._header_int(headers, "x-ratelimit-remaining")

    def can_call(self, configured_budget: int, reserve: int = 5) -> bool:
        if self.calls >= configured_budget:
            return False
        return self.daily_remaining is None or self.daily_remaining > reserve

    def fixtures_by_date(self, target_date: str, timezone: str) -> ProviderResponse:
        return self._get("/fixtures", date=target_date, timezone=timezone)

    def current_leagues(self) -> ProviderResponse:
        return self._get("/leagues", current="true")

    def recent_team_fixtures(self, team_id: int, last: int = 20) -> ProviderResponse:
        return self._get("/fixtures", team=team_id, last=last, status="FT")

    def fixture_statistics(self, fixture_id: int) -> ProviderResponse:
        return self._get("/fixtures/statistics", fixture=fixture_id)

    def standings(self, league_id: int, season: int) -> ProviderResponse:
        return self._get("/standings", league=league_id, season=season)

    def odds(self, fixture_id: int) -> ProviderResponse:
        return self._get("/odds", fixture=fixture_id)
