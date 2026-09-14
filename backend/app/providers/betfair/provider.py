import re
from datetime import UTC, date, datetime, time, timedelta

import httpx

from app.core.config import Settings, read_config
from app.core.exceptions import ProviderError
from app.db.connection import Database
from app.domain.market import Market
from app.domain.odds import Bookmaker, NormalizedOdds, ProviderEvent
from app.providers.base.odds_provider import OddsProvider
from app.providers.betfair.session import BetfairSession
from app.providers.transport import ProviderTransport
from app.providers.usage import ApiUsageTracker


class BetfairProvider(OddsProvider):
    name = "betfair"
    READ_METHODS = frozenset({"listEvents", "listMarketCatalogue", "listMarketBook"})

    def __init__(
        self,
        settings: Settings,
        db: Database,
        client: httpx.AsyncClient | None = None,
        session: BetfairSession | None = None,
    ):
        self.settings = settings
        self.configured = all(
            secret.get_secret_value()
            for secret in (
                settings.betfair_app_key,
                settings.betfair_username,
                settings.betfair_password,
            )
        )
        self.session = session or BetfairSession(settings)
        self.configured = self.configured and read_config("providers")["betfair"]["enabled"]
        self.transport = ProviderTransport(
            self.name,
            db,
            client
            or httpx.AsyncClient(
                base_url="https://api.betfair.com/exchange/betting/rest/v1.0/", timeout=30
            ),
            ApiUsageTracker(db, self.name, 100000),
            min_interval=0.25,
        )
        self.ttl = 300

    async def rpc(self, method: str, params: dict, ttl: int = 300):
        if method not in self.READ_METHODS:
            raise ProviderError("Betfair: operación fuera del contrato de solo lectura")
        if not self.configured:
            raise ProviderError("Faltan las credenciales de Betfair en backend/.env")

        def validate(data):
            if isinstance(data, dict) and (data.get("error") or data.get("faultcode")):
                if "INVALID_SESSION_INFORMATION" in str(data):
                    raise ProviderError("betfair: INVALID_SESSION_INFORMATION")
                raise ProviderError("betfair: operación de consulta rechazada")
            if not isinstance(data, list):
                raise ProviderError("betfair: contrato de consulta inválido")

        for attempt in range(2):
            try:
                headers = await self.session.headers()
                return await self.transport.request(
                    "POST",
                    method + "/",
                    body=params,
                    headers=headers,
                    ttl=ttl,
                    validator=validate,
                    allow_stale=False,
                )
            except ProviderError as exc:
                if attempt == 0 and "INVALID_SESSION_INFORMATION" in str(exc):
                    self.session.invalidate()
                    continue
                self.transport.error(str(exc))
                raise

    async def catalogue(self, start: datetime, end: datetime) -> list[dict]:
        result = await self.rpc(
            "listMarketCatalogue",
            {
                "filter": {
                    "eventTypeIds": ["1"],
                    "marketStartTime": {"from": start.isoformat(), "to": end.isoformat()},
                    "marketTypeCodes": [
                        "OVER_UNDER_05",
                        "OVER_UNDER_15",
                        "OVER_UNDER_25",
                        "OVER_UNDER_35",
                        "OVER_UNDER_45",
                        "BOTH_TEAMS_TO_SCORE",
                        "CORNER_KICKS",
                        "CORNER_KICKS_85",
                        "CORNER_KICKS_105",
                        "OVER_UNDER_85_CORNR",
                        "OVER_UNDER_105_CORNR",
                    ],
                },
                "marketProjection": [
                    "EVENT",
                    "COMPETITION",
                    "RUNNER_DESCRIPTION",
                    "MARKET_START_TIME",
                    "MARKET_DESCRIPTION",
                ],
                "sort": "FIRST_TO_START",
                "maxResults": "1000",
            },
            ttl=1800,
        )
        if len(result) == 1000:
            if (end - start).total_seconds() < 60:
                raise ProviderError("Betfair: catálogo incompleto por límite de resultados")
            middle = start + (end - start) / 2
            combined = await self.catalogue(start, middle) + await self.catalogue(middle, end)
            return list({r["marketId"]: r for r in combined}.values())
        return result

    @staticmethod
    def normalize_market(
        catalogue: dict, book: dict, event: ProviderEvent, timestamp: datetime
    ) -> list[NormalizedOdds]:
        if book.get("status") != "OPEN" or book.get("inplay"):
            return []
        kind = catalogue.get("description", {}).get("marketType", "")
        name = catalogue.get("marketName", "").lower()
        if (
            any(token in name for token in ("half", "extra time", "team"))
            and kind != "BOTH_TEAMS_TO_SCORE"
        ):
            return []
        descriptions = {r["selectionId"]: r["runnerName"] for r in catalogue.get("runners", [])}
        prices = []
        for runner in book.get("runners", []):
            if runner.get("status") != "ACTIVE":
                continue
            runner_name = descriptions.get(runner["selectionId"], "").lower()
            try:
                if kind == "BOTH_TEAMS_TO_SCORE":
                    market, side, line = Market.BTTS_YES, runner_name.upper(), None
                else:
                    match = re.search(r"(over|under)\s+(\d+\.5)", runner_name)
                    if not match:
                        continue
                    side, line = match[1].upper(), float(match[2])
                    market = Market(
                        f"OVER_{int(line)}_5_{'CORNERS' if 'corner' in name else 'GOALS'}"
                    )
                backs = [
                    p["price"]
                    for p in runner.get("ex", {}).get("availableToBack", [])
                    if p.get("size", 0) > 0
                ]
                lays = [
                    p["price"]
                    for p in runner.get("ex", {}).get("availableToLay", [])
                    if p.get("size", 0) > 0
                ]
                if not backs:
                    continue
                prices.append(
                    NormalizedOdds(
                        provider="betfair",
                        bookmaker=Bookmaker.BETFAIR,
                        provider_event_id=event.provider_event_id,
                        market=market,
                        line=line,
                        selection=side,
                        decimal_odds=max(backs),
                        timestamp=timestamp,
                        best_back_price=max(backs),
                        best_lay_price=min(lays) if lays else None,
                        is_delayed=book.get("isMarketDataDelayed", True),
                        source_label="Betfair Exchange · API oficial",
                    )
                )
            except (ValueError, KeyError, TypeError):
                continue
        return prices

    async def get_events(self, target_date: date) -> list[ProviderEvent]:
        start = datetime.combine(target_date, time.min, self.settings.timezone).astimezone(UTC)
        end = datetime.combine(
            target_date + timedelta(days=1), time.min, self.settings.timezone
        ).astimezone(UTC)
        catalogue = await self.catalogue(start, end)
        events: dict[str, ProviderEvent] = {}
        markets: dict[str, dict] = {}
        for entry in catalogue:
            raw = entry.get("event", {})
            teams = re.split(r"\s+v(?:s\.?)*\s+", raw.get("name", ""), maxsplit=1)
            if len(teams) != 2:
                continue
            event_id = str(raw["id"])
            events.setdefault(
                event_id,
                ProviderEvent(
                    provider=self.name,
                    bookmaker=Bookmaker.BETFAIR,
                    provider_event_id=event_id,
                    home_team=teams[0],
                    away_team=teams[1],
                    competition=entry.get("competition", {}).get("name", ""),
                    kickoff_utc=entry["marketStartTime"],
                ),
            )
            markets[entry["marketId"]] = entry
        ids = list(markets)
        for offset in range(0, len(ids), 40):
            books = await self.rpc(
                "listMarketBook",
                {
                    "marketIds": ids[offset : offset + 40],
                    "priceProjection": {
                        "priceData": ["EX_BEST_OFFERS"],
                        "exBestOffersOverrides": {"bestPricesDepth": 1},
                    },
                },
                ttl=self.ttl,
            )
            for book in books:
                entry = markets[book["marketId"]]
                event = events[str(entry["event"]["id"])]
                event.observed_at = (
                    min(event.observed_at, self.transport.last_response_at)
                    if event.observed_at
                    else self.transport.last_response_at
                )
                event.odds.extend(
                    self.normalize_market(entry, book, event, self.transport.last_response_at)
                )
        return list(events.values())

    async def get_event_odds(self, event: ProviderEvent) -> list[NormalizedOdds]:
        events = await self.get_events(event.kickoff_utc.astimezone(self.settings.timezone).date())
        return next(
            (item.odds for item in events if item.provider_event_id == event.provider_event_id), []
        )

    async def health_check(self) -> dict:
        return {"configured": self.configured, "delayed_prices": True, **self.transport.status()}
