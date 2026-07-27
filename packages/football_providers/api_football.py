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

    def close(self) -> None:
        self._client.close()

    def _get(self, endpoint: str, **parameters: Any) -> ProviderResponse:
        clean_parameters = {key: value for key, value in parameters.items() if value is not None}
        try:
            response = self._client.get(endpoint, params=clean_parameters)
            self.calls += 1
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError(f"Error consultando {endpoint}: {exc}") from exc

        errors = body.get("errors") if isinstance(body, dict) else None
        if errors and errors != []:
            raise ProviderError(f"API-Football devolvio errores en {endpoint}: {errors}")
        return ProviderResponse(endpoint, clean_parameters, body, response.status_code)

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
