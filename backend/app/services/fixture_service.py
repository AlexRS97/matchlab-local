from datetime import date

from app.providers.base.football_provider import FootballProvider
from app.repositories.fixture_repository import FixtureRepository


class FixtureService:
    def __init__(self, provider: FootballProvider, repository: FixtureRepository):
        self.provider, self.repository = provider, repository

    async def refresh(self, target: date):
        fixtures = await self.provider.get_fixtures(target)
        for fixture in fixtures:
            self.repository.save(fixture)
        return self.repository.for_date(target)
