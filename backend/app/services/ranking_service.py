from datetime import UTC, datetime

from app.domain.market import Market
from app.domain.settings import UserSettings
from app.services.data_quality_service import CONFIDENCE_LEVELS, QUALITY_LEVELS


class RankingService:
    def rank(
        self,
        rows: list[dict],
        market: Market,
        settings: UserSettings,
        *,
        bookmaker: str = "ALL",
        min_odds: float | None = None,
        max_odds: float | None = None,
        min_probability: float = 0,
        min_edge: float | None = None,
        min_ev: float | None = None,
        top_n: int | None = None,
        min_confidence: str | None = None,
        min_quality: str | None = None,
        now: datetime | None = None,
    ) -> list[dict]:
        now = now or datetime.now(UTC)
        if market not in settings.enabled_markets:
            return []
        minimum = settings.minimum_odds if min_odds is None else min_odds
        confidence_min = CONFIDENCE_LEVELS[min_confidence or settings.minimum_confidence]
        quality_min = QUALITY_LEVELS[min_quality or settings.minimum_data_quality]
        ranked = []
        for row in rows:
            if row["status"] != "NOT_STARTED" or datetime.fromisoformat(row["kickoff_utc"]) <= now:
                continue
            if settings.enabled_countries and row["country"] not in settings.enabled_countries:
                continue
            if settings.enabled_leagues and row["league_id"] not in settings.enabled_leagues:
                continue
            prediction = row.get("prediction") or {}
            probability = (
                prediction.get("corners" if market.value.endswith("CORNERS") else "goals", {})
                .get("probabilities", {})
                .get(market.value)
            )
            quality = prediction.get(
                "corner_quality" if market.value.endswith("CORNERS") else "quality", {"score": 0}
            )
            confidence = prediction.get("confidence", {}).get(market.value, {"score": 0})
            comparison = row["markets"][market.value]
            quote = (
                comparison["best"] if bookmaker == "ALL" else comparison["quotes"].get(bookmaker)
            )
            if probability is None or probability < min_probability or not quote or quote["stale"]:
                continue
            if quote["decimal_odds"] < minimum or (
                max_odds is not None and quote["decimal_odds"] > max_odds
            ):
                continue
            if confidence["score"] < confidence_min or quality["score"] < max(40, quality_min):
                continue
            if min_edge is not None and (quote["edge"] is None or quote["edge"] < min_edge):
                continue
            if min_ev is not None and (quote["ev"] is None or quote["ev"] < min_ev):
                continue
            ranked.append(
                {
                    "fixture": row,
                    "market": market.value,
                    "probability": probability,
                    "confidence": confidence,
                    "quality": quality,
                    "comparison": comparison,
                    "selected_quote": quote,
                }
            )
        ranked.sort(
            key=lambda r: (
                r["probability"],
                r["confidence"]["score"],
                r["quality"]["score"],
                r["selected_quote"]["ev"]
                if r["selected_quote"]["ev"] is not None
                else -float("inf"),
            ),
            reverse=True,
        )
        count = settings.top_n if top_n is None else top_n
        return [
            {"rank": i + 1, **item} for i, item in enumerate(ranked[:count] if count else ranked)
        ]
