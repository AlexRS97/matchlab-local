from datetime import UTC, date, datetime

from app.core.exceptions import ProviderError
from app.domain.fixture import Fixture
from app.domain.odds import Bookmaker
from app.domain.settings import UserSettings
from app.jobs.progress import JobProgress
from app.providers.betfair.provider import BetfairProvider
from app.providers.pulsescore.provider import PulseScoreProvider
from app.repositories.odds_repository import OddsRepository
from app.services.fixture_matcher import FixtureMatcher


class OddsRefreshService:
    def __init__(
        self,
        betfair: BetfairProvider,
        pulsescore: PulseScoreProvider,
        repository: OddsRepository,
        matcher: FixtureMatcher,
    ):
        self.betfair, self.pulsescore = betfair, pulsescore
        self.repository, self.matcher = repository, matcher

    async def refresh(
        self,
        target: date,
        fixtures: list[Fixture],
        settings: UserSettings,
        only: str | None = None,
        progress: JobProgress | None = None,
    ) -> list[str]:
        errors: list[str] = []
        self.betfair.ttl = settings.betfair_minutes * 60
        self.pulsescore.ttl = settings.pulsescore_minutes * 60
        self.pulsescore.enabled_bookmakers = set(settings.enabled_bookmakers)
        self.pulsescore.config["betfair_fallback"] = settings.betfair_fallback
        pending = [f for f in fixtures if f.prematch(datetime.now(UTC))]
        if not pending:
            return errors
        providers = [self.betfair, self.pulsescore]
        for index, provider in enumerate(providers):
            if progress:
                progress.update(index, len(providers), f"Consultando {provider.name}")
            if only and provider.name != only:
                continue
            if not provider.configured or (
                provider.name == "betfair" and Bookmaker.BETFAIR not in settings.enabled_bookmakers
            ):
                continue
            try:
                events = await provider.get_events(target)
                for event in events:
                    matched = self.matcher.match(event, pending)
                    if matched.fixture_id is None:
                        continue
                    fixture = next(f for f in pending if f.fixture_id == matched.fixture_id)
                    prices = [
                        p.model_copy(update={"fixture_id": matched.fixture_id})
                        for p in event.odds
                        if not p.is_live
                        and p.timestamp < fixture.kickoff_utc
                        and p.timestamp <= datetime.now(UTC)
                    ]
                    self.repository.save(prices)
                    if event.observed_at:
                        self.repository.save_board(
                            matched.fixture_id,
                            event.provider,
                            event.bookmaker.value,
                            event.observed_at,
                            prices,
                        )
                if isinstance(provider, PulseScoreProvider):
                    errors.extend(provider.warnings)
            except ProviderError as exc:
                errors.append(str(exc))
        if progress:
            progress.update(len(providers), len(providers), "Comparación revisada")
        return errors
