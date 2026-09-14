from datetime import date, datetime, timedelta

import httpx

from app.core.config import Settings, read_config
from app.core.exceptions import ProviderError
from app.db.connection import Database
from app.domain.fixture import Fixture, MatchObservation
from app.providers.api_football.normalization import (
    normalize_fixture,
    normalize_statistics,
    observations,
)
from app.providers.base.football_provider import FootballProvider
from app.providers.transport import ProviderTransport
from app.providers.usage import ApiUsageTracker


class ApiFootballProvider(FootballProvider):
    name = "api_football"

    def __init__(self, settings: Settings, db: Database, client: httpx.AsyncClient | None = None):
        self.settings = settings
        self.refresh = read_config("refresh")
        self.configured = (
            bool(settings.api_football_key.get_secret_value())
            and read_config("providers")["api_football"]["enabled"]
        )
        self.transport = ProviderTransport(
            self.name,
            db,
            client
            or httpx.AsyncClient(
                base_url=settings.api_football_base_url,
                timeout=30,
                headers={"x-apisports-key": settings.api_football_key.get_secret_value()},
            ),
            ApiUsageTracker(
                db,
                self.name,
                settings.api_football_daily_call_budget,
                reserve=settings.api_football_quota_reserve,
            ),
            min_interval=0.5,
        )

    @staticmethod
    def validate(data):
        if not isinstance(data, dict) or "response" not in data:
            raise ProviderError("api_football: contrato de respuesta inválido")
        if data.get("errors"):
            # Provider messages can reflect request fields; only expose known error keys.
            keys = list(data["errors"]) if isinstance(data["errors"], dict) else ["upstream"]
            safe = [
                key
                for key in keys
                if key in {"requests", "rateLimit", "token", "plan", "last", "season", "date"}
            ]
            raise ProviderError(
                f"api_football: consulta rechazada ({', '.join(safe) or 'upstream'}); revisar plan/cuota"
            )

    async def _get(self, endpoint: str, ttl: float, **params):
        if not self.configured:
            raise ProviderError("Falta API_FOOTBALL_KEY en backend/.env")
        data = await self.transport.request(
            "GET", endpoint, ttl=ttl, params=params, validator=self.validate
        )
        response = data["response"]
        return response if isinstance(response, list) else [response]

    async def get_fixtures(self, target_date: date) -> list[Fixture]:
        rows = await self._get(
            "/fixtures",
            self.refresh["fixtures_minutes"] * 60,
            date=target_date.isoformat(),
            timezone=self.settings.app_timezone,
        )
        return [normalize_fixture(row, self.transport.last_response_at) for row in rows]

    async def get_fixture(self, fixture_id: int) -> Fixture | None:
        rows = await self._get("/fixtures", 1800, id=fixture_id)
        return normalize_fixture(rows[0], self.transport.last_response_at) if rows else None

    async def get_recent_matches(
        self, team_id: int, before: datetime, season: int
    ) -> list[MatchObservation]:
        params = {"team": team_id, "status": "FT-AET-PEN"}
        if self.settings.api_football_history_mode == "last":
            params["last"] = 40
        else:
            params["season"] = season
        rows = await self._get("/fixtures", self.refresh["stats_minutes"] * 60, **params)
        result = [
            obs
            for row in rows
            for obs in observations(row, self.transport.last_response_at)
            if obs.team_id == team_id and obs.completed_at < before
        ]
        if len(result) < 20 and self.settings.api_football_history_mode != "last":
            try:
                rows = await self._get(
                    "/fixtures",
                    self.refresh["stats_minutes"] * 60,
                    team=team_id,
                    season=season - 1,
                    status="FT-AET-PEN",
                )
            except ProviderError:
                if not result:
                    raise
                rows = []
            result.extend(
                obs
                for row in rows
                for obs in observations(row, self.transport.last_response_at)
                if obs.team_id == team_id and obs.completed_at < before
            )
        unique = {obs.fixture_id: obs for obs in result}
        return sorted(unique.values(), key=lambda obs: obs.kickoff_utc, reverse=True)[:40]

    async def get_head_to_head(self, home_id: int, away_id: int) -> list[MatchObservation]:
        rows = await self._get("/fixtures/headtohead", 21600, h2h=f"{home_id}-{away_id}")
        return [obs for row in rows for obs in observations(row, self.transport.last_response_at)]

    async def get_standings(self, league_id: int, season: int) -> list[dict]:
        rows = await self._get(
            "/standings", self.refresh["standings_minutes"] * 60, league=league_id, season=season
        )
        return [
            {
                "position": entry["rank"],
                "team_id": entry["team"]["id"],
                "team": entry["team"]["name"],
                "points": entry["points"],
                "goal_difference": entry["goalsDiff"],
                "played": entry["all"]["played"],
                "wins": entry["all"]["win"],
                "draws": entry["all"]["draw"],
                "losses": entry["all"]["lose"],
                "goals_for": entry["all"]["goals"]["for"],
                "goals_against": entry["all"]["goals"]["against"],
                "source": self.name,
                "observed_at": self.transport.last_response_at.isoformat(),
            }
            for row in rows
            for group in row.get("league", {}).get("standings", [])
            for entry in group
        ]

    async def get_fixture_statistics(self, fixture_id: int) -> dict[int, dict]:
        return normalize_statistics(
            await self._get("/fixtures/statistics", 86400 * 7, fixture=fixture_id)
        )

    async def get_team_statistics(
        self, team_id: int, league_id: int, season: int, before: datetime
    ) -> list[dict]:
        return await self._get(
            "/teams/statistics",
            21600,
            team=team_id,
            league=league_id,
            season=season,
            date=(before.date() - timedelta(days=1)).isoformat(),
        )

    async def get_league_matches(self, league_id: int, season: int) -> list[MatchObservation]:
        rows = await self._get(
            "/fixtures", 21600, league=league_id, season=season, status="FT-AET-PEN"
        )
        return [obs for row in rows for obs in observations(row, self.transport.last_response_at)]

    async def get_injuries(self, fixture_id: int) -> list[dict]:
        return await self._get("/injuries", 21600, fixture=fixture_id)

    async def get_lineups(self, fixture_id: int) -> list[dict]:
        return await self._get("/fixtures/lineups", 1800, fixture=fixture_id)

    async def get_predictions(self, fixture_id: int) -> dict:
        rows = await self._get("/predictions", 21600, fixture=fixture_id)
        prediction = rows[0].get("predictions", {}) if rows else {}
        percentages = prediction.get("percent", {})
        outcomes = {}
        for key in ("home", "draw", "away"):
            try:
                probability = float(str(percentages[key]).rstrip("%")) / 100
                if 0 <= probability <= 1:
                    outcomes[key.upper()] = probability
            except (KeyError, ValueError, TypeError):
                continue
        return {
            "source": self.name,
            "outcome_probabilities": outcomes,
            "market_probabilities": {},
            "advice": prediction.get("advice"),
            "observed_at": self.transport.last_response_at.isoformat(),
            "note": "1X2 externo; no se mezcla con probabilidades de goles o córners",
        }

    async def get_odds(self, fixture_id: int) -> list[dict]:
        return await self._get("/odds", 900, fixture=fixture_id)
