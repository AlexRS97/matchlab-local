import math
from datetime import UTC, date, datetime

import httpx
from pydantic import ValidationError

from app.core.config import Settings, read_config
from app.core.exceptions import ProviderError
from app.db.connection import Database
from app.domain.market import Market
from app.domain.odds import Bookmaker, NormalizedOdds, ProviderEvent
from app.providers.base.odds_provider import OddsProvider
from app.providers.transport import ProviderTransport
from app.providers.usage import ApiUsageTracker


class PulseScoreProvider(OddsProvider):
    name = "pulsescore"

    def __init__(self, settings: Settings, db: Database, client: httpx.AsyncClient | None = None):
        self.settings, self.config = settings, read_config("providers")["pulsescore"]
        self.configured = (
            bool(settings.pulsescore_api_key.get_secret_value()) and self.config["enabled"]
        )
        self.transport = ProviderTransport(
            self.name,
            db,
            client
            or httpx.AsyncClient(
                base_url=settings.pulsescore_base_url,
                timeout=30,
                headers={
                    "X-Secret": settings.pulsescore_api_key.get_secret_value(),
                    "Accept-Encoding": "gzip",
                },
            ),
            ApiUsageTracker(db, self.name, settings.pulsescore_monthly_budget, monthly=True),
            min_interval=1,
        )
        self.enabled_bookmakers = set(Bookmaker)
        self.ttl = 300
        self.warnings: list[str] = []
        self.last_cycle_requests = 2

    def effective_interval(self, requested_minutes: int) -> int:
        usage = self.transport.usage.status()
        remaining = max(1, usage["requests_remaining"])
        minutes_left = (usage["reset_time"] - datetime.now(UTC)).total_seconds() / 60
        return max(
            requested_minutes, math.ceil(minutes_left * self.last_cycle_requests / remaining)
        )

    def normalize(self, raw: dict, bookmaker: Bookmaker, timestamp: datetime) -> ProviderEvent:
        kickoff = raw.get("startTime")
        if not kickoff:
            raise ValueError("Falta hora de inicio; no se puede emparejar con seguridad")
        event = ProviderEvent(
            provider=self.name,
            bookmaker=bookmaker,
            observed_at=timestamp,
            provider_event_id=str(raw["eventId"]),
            home_team=raw["home"],
            away_team=raw["away"],
            competition=raw.get("league", ""),
            kickoff_utc=datetime.fromisoformat(kickoff.replace("Z", "+00:00")),
        )
        for market in raw.get("markets", []):
            if market.get("isActive") is not True or market.get("period", "").upper() not in {
                "FULL_TIME",
                "FULLTIME",
            }:
                continue
            kind = market.get("canonicalMarket", "").upper()
            raw_name = market.get("rawName", "").lower()
            is_btts = kind in {"BOTH_TEAMS_TO_SCORE", "BTTS"}
            if any(
                part in raw_name for part in ("half", "1st", "2nd", "extra", "alternative asian")
            ) or ("team" in raw_name and not is_btts):
                continue
            is_corners = kind in {
                "TOTAL_CORNERS",
                "CORNERS_OVER_UNDER",
                "CORNERS_TOTAL",
                "TOTAL_CORNER_KICKS",
            }
            is_goals = kind in {"OVER_UNDER", "TOTAL_GOALS"} and "corner" not in raw_name
            if not (is_btts or is_corners or is_goals):
                continue
            for selection in market.get("selections", []):
                if selection.get("isActive") is not True:
                    continue
                side = str(selection.get("canonicalOutcome", selection.get("name", ""))).upper()
                line = selection.get("line", market.get("line"))
                try:
                    if is_btts:
                        canonical, line = Market.BTTS_YES, None
                    else:
                        line = float(line)
                        if line % 1 != 0.5:
                            continue
                        canonical = Market(
                            f"OVER_{int(line)}_5_{'CORNERS' if is_corners else 'GOALS'}"
                        )
                    source_time = (
                        selection.get("updatedAt")
                        or market.get("updatedAt")
                        or raw.get("updatedAt")
                    )
                    price_time = (
                        datetime.fromisoformat(source_time.replace("Z", "+00:00"))
                        if source_time
                        else timestamp
                    )
                    event.odds.append(
                        NormalizedOdds(
                            provider=self.name,
                            bookmaker=bookmaker,
                            provider_event_id=event.provider_event_id,
                            market=canonical,
                            line=line,
                            selection=side,
                            decimal_odds=selection["odds"],
                            timestamp=price_time,
                            is_live=bool(raw.get("live", False)),
                            source_label="Orbit Exchange (PulseScore)"
                            if bookmaker == Bookmaker.BETFAIR
                            else "PulseScore",
                            source_url=raw.get("url"),
                        )
                    )
                except (ValueError, KeyError, TypeError, ValidationError):
                    continue
        return event

    async def get_events(self, target_date: date) -> list[ProviderEvent]:
        if not self.configured:
            raise ProviderError("Falta PULSESCORE_API_KEY en backend/.env")
        self.warnings = []
        before_requests = self.transport.usage.status()["requests_period"]
        self.ttl = max(self.ttl, self.effective_interval(max(5, self.ttl // 60)) * 60)
        events = []
        books = [
            b
            for b in Bookmaker
            if b in self.enabled_bookmakers
            and read_config("providers").get(b.value.lower(), {}).get("enabled", True)
            and (b != Bookmaker.BETFAIR or self.config.get("betfair_fallback"))
        ]

        def validate(data):
            if not isinstance(data, dict) or not isinstance(data.get("events"), list):
                raise ProviderError("pulsescore: contrato de eventos inválido")

        for bookmaker in books:
            prefix = self.config["prefixes"][bookmaker.value]
            try:
                for page in range(1, self.settings.pulsescore_max_pages + 1):
                    data = await self.transport.request(
                        "GET",
                        prefix + "/events",
                        ttl=self.ttl,
                        params={"page": page, "limit": 30},
                        validator=validate,
                    )
                    if not isinstance(data, dict) or not isinstance(data.get("events"), list):
                        raise ProviderError("pulsescore: contrato de eventos inválido")
                    for raw in data["events"]:
                        try:
                            event = self.normalize(raw, bookmaker, self.transport.last_response_at)
                        except (ValueError, KeyError, TypeError, ValidationError):
                            self.warnings.append(
                                f"{bookmaker}: evento sin datos suficientes para matching"
                            )
                            continue
                        local_date = event.kickoff_utc.astimezone(self.settings.timezone).date()
                        if local_date == target_date:
                            events.append(event)
                    if not data.get("hasNextPage"):
                        break
                    if page == self.settings.pulsescore_max_pages:
                        self.warnings.append(
                            f"{bookmaker}: cobertura parcial, límite de páginas alcanzado"
                        )
            except ProviderError as exc:
                self.warnings.append(str(exc))
        spent = self.transport.usage.status()["requests_period"] - before_requests
        if spent:
            self.last_cycle_requests = spent
        return events

    async def get_event_odds(self, event: ProviderEvent) -> list[NormalizedOdds]:
        prefix = self.config["prefixes"][event.bookmaker.value]
        data = await self.transport.request(
            "GET", prefix + "/events/" + event.provider_event_id, ttl=self.ttl
        )
        return (
            self.normalize(data["data"], event.bookmaker, self.transport.last_response_at).odds
            if data.get("data")
            else []
        )

    async def health_check(self) -> dict:
        return {
            "configured": self.configured,
            **self.transport.status(),
            "warnings": self.warnings,
            "effective_interval_minutes": self.effective_interval(5),
        }
