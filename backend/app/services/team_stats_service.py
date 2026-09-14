from datetime import UTC, datetime

from app.core.exceptions import ProviderError
from app.domain.fixture import Fixture, MatchObservation
from app.providers.api_football.provider import ApiFootballProvider
from app.repositories.stats_repository import StatsRepository


class TeamStatsService:
    def __init__(self, provider: ApiFootballProvider, repository: StatsRepository):
        self.provider, self.repository = provider, repository

    async def refresh_fixture(self, fixture: Fixture, *, statistics_budget: int = 0) -> list[str]:
        if not fixture.prematch(datetime.now(UTC)):
            return []
        errors = []
        for team in (fixture.home_team_id, fixture.away_team_id):
            try:
                matches = await self.provider.get_recent_matches(
                    team, fixture.kickoff_utc, fixture.season
                )
                self.repository.save_matches(matches)
            except ProviderError as exc:
                errors.append(str(exc))
        return errors

    async def enrich_statistics(self, matches: list[MatchObservation], budget: int) -> int:
        consumed = 0
        for obs in matches:
            if not obs.statistics_allowed:
                continue
            stored = self.repository.statistics(obs.fixture_id)
            if stored is None:
                if consumed >= budget:
                    continue
                stats = await self.provider.get_fixture_statistics(obs.fixture_id)
                observed_at = self.provider.transport.last_response_at
                self.repository.save_statistics(obs.fixture_id, stats, observed_at)
                consumed += 1
            else:
                stats = {int(key): value for key, value in stored["data"].items()}
                observed_at = stored["timestamp"]
            own = stats.get(obs.team_id, {})
            other = stats.get(obs.opponent_id, {})
            update = {
                "corners_for": own.get("corners"),
                "corners_against": other.get("corners"),
                "shots": own.get("shots"),
                "shots_on_target": own.get("shots_on_target"),
                "possession": own.get("possession"),
                "xg": own.get("xg"),
                "xga": other.get("xg"),
                "observed_at": max(obs.observed_at, observed_at),
            }
            self.repository.save_matches([obs.model_copy(update=update)])
        return consumed
