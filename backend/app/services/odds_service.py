from datetime import UTC, datetime
from statistics import mean

from app.domain.market import Market
from app.domain.odds import Bookmaker, NormalizedOdds
from app.repositories.odds_repository import OddsRepository
from app.services.odds_math import devig, expected_value, fair_odds, implied_probability


class OddsService:
    def __init__(self, repository: OddsRepository):
        self.repository = repository

    def compare(
        self,
        fixture_id: int,
        market: Market,
        probability: float | None,
        stale_minutes: int = 15,
        enabled: list[Bookmaker] | None = None,
        before: datetime | None = None,
        now: datetime | None = None,
        available_prices: list[NormalizedOdds] | None = None,
    ) -> dict:
        now = now or datetime.now(UTC)
        enabled = list(Bookmaker) if enabled is None else enabled
        canonical = Market.BTTS_YES if market == Market.BTTS_NO else market
        prices = [
            p
            for p in (
                available_prices
                if available_prices is not None
                else self.repository.current(fixture_id, before)
            )
            if p.market == canonical
            and not p.is_live
            and p.timestamp <= now
            and p.bookmaker in enabled
        ]
        quotes: dict[str, dict | None] = {book.value: None for book in Bookmaker}
        for book in Bookmaker:
            choices = [p for p in prices if p.bookmaker == book and p.selection == market.selection]
            if not choices:
                continue

            def stale(price):
                return (now - price.timestamp).total_seconds() > stale_minutes * 60

            priority = {"betfair": 0, "manual": 1, "pulsescore": 2}
            choices.sort(
                key=lambda p: (stale(p), priority.get(p.provider, 3), -p.timestamp.timestamp())
            )
            price = choices[0]
            other = next(
                (
                    p
                    for p in prices
                    if p.bookmaker == book
                    and p.provider == price.provider
                    and p.selection != price.selection
                    and abs((p.timestamp - price.timestamp).total_seconds()) <= 60
                    and not stale(p)
                ),
                None,
            )
            market_probability = (
                devig(price.decimal_odds, other.decimal_odds)[0]
                if other
                else implied_probability(price.decimal_odds)
            )
            quotes[book.value] = {
                **price.model_dump(mode="json"),
                "stale": stale(price),
                "market_probability": market_probability,
                "devig_status": "DEVIGGED" if other else "NOT_DEVIGGED",
                "edge": probability - market_probability if probability is not None else None,
                "ev": expected_value(probability, price.decimal_odds)
                if probability is not None
                else None,
            }
        available = [quote for quote in quotes.values() if quote]
        fresh = [quote for quote in available if not quote["stale"]]
        best = max(fresh or available, key=lambda q: q["decimal_odds"], default=None)
        consensus = mean(quote["market_probability"] for quote in fresh) if fresh else None
        return {
            "market": market.value,
            "quotes": quotes,
            "model_probability": probability,
            "fair_odds": fair_odds(probability),
            "best_bookmaker": best["bookmaker"] if best else None,
            "best_odds": best["decimal_odds"] if best else None,
            "best": best,
            "market_consensus": consensus,
            "consensus_status": "DEVIGGED"
            if fresh and all(q["devig_status"] == "DEVIGGED" for q in fresh)
            else "NOT_DEVIGGED",
            "consensus_edge": probability - consensus
            if probability is not None and consensus is not None
            else None,
        }
