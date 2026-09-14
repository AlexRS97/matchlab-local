from abc import ABC, abstractmethod
from datetime import date, datetime

from app.domain.fixture import Fixture, MatchObservation


class FootballProvider(ABC):
    name: str

    @abstractmethod
    async def get_fixtures(self, target_date: date) -> list[Fixture]: ...

    @abstractmethod
    async def get_fixture(self, fixture_id: int) -> Fixture | None: ...

    @abstractmethod
    async def get_recent_matches(
        self, team_id: int, before: datetime, season: int
    ) -> list[MatchObservation]: ...

    @abstractmethod
    async def get_standings(self, league_id: int, season: int) -> list[dict]: ...
