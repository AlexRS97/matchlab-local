from datetime import UTC, date, datetime

from app.domain.market import Market
from app.domain.odds import NormalizedOdds, ProviderEvent
from app.providers.base.odds_provider import OddsProvider
from app.repositories.fixture_repository import FixtureRepository
from app.repositories.odds_repository import OddsRepository


class ManualOddsProvider(OddsProvider):
    name = "manual"

    def __init__(self, repository: OddsRepository, fixtures: FixtureRepository):
        self.repository, self.fixtures = repository, fixtures

    def enter(self, price: NormalizedOdds):
        fixture = self.fixtures.get(price.fixture_id) if price.fixture_id is not None else None
        if fixture is None or not fixture.prematch(datetime.now(UTC)):
            raise ValueError(
                "Las cuotas manuales solo se admiten antes del inicio de un partido existente"
            )
        price = price.model_copy(
            update={
                "provider": self.name,
                "is_manual": True,
                "timestamp": datetime.now(UTC),
                "source_label": "MANUAL",
                "market": Market.BTTS_YES if price.market == Market.BTTS_NO else price.market,
            }
        )
        self.repository.save([price])
        return price

    async def get_events(self, target_date: date) -> list[ProviderEvent]:
        return [
            ProviderEvent(
                provider=self.name,
                provider_event_id=str(f.fixture_id),
                home_team=f.home_team,
                away_team=f.away_team,
                competition=f.league_name,
                kickoff_utc=f.kickoff_utc,
                bookmaker=p.bookmaker,
                odds=[p],
            )
            for f in self.fixtures.for_date(target_date)
            for p in self.repository.current(f.fixture_id)
            if p.is_manual
        ]

    async def get_event_odds(self, event: ProviderEvent) -> list[NormalizedOdds]:
        return [p for p in self.repository.current(int(event.provider_event_id)) if p.is_manual]

    async def health_check(self):
        return {"provider": self.name, "configured": True, "status": "AVAILABLE"}
