from abc import ABC, abstractmethod
from datetime import date

from app.domain.market import Market
from app.domain.odds import NormalizedOdds, ProviderEvent


class OddsProvider(ABC):
    name: str
    configured: bool = True

    @abstractmethod
    async def get_events(self, target_date: date) -> list[ProviderEvent]: ...

    @abstractmethod
    async def get_event_odds(self, event: ProviderEvent) -> list[NormalizedOdds]: ...

    async def get_market_odds(self, event: ProviderEvent, market: Market) -> list[NormalizedOdds]:
        return [o for o in await self.get_event_odds(event) if o.market == market]

    @abstractmethod
    async def health_check(self) -> dict: ...
