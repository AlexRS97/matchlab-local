from datetime import date

from app.core.config import Settings, read_config
from app.domain.market import Market
from app.domain.settings import UserSettings
from app.repositories.fixture_repository import FixtureRepository
from app.repositories.predictions_repository import PredictionsRepository
from app.services.fixture_matcher import ALIASES, normalize_name
from app.services.odds_service import OddsService
from app.services.ranking_service import RankingService


class DashboardService:
    def __init__(
        self,
        fixtures: FixtureRepository,
        predictions: PredictionsRepository,
        odds: OddsService,
        environment: Settings,
    ):
        self.fixtures, self.predictions, self.odds, self.environment = (
            fixtures,
            predictions,
            odds,
            environment,
        )
        self.ranking = RankingService()

    def rows(self, target: date, settings: UserSettings) -> list[dict]:
        rows = []
        for fixture in self.fixtures.for_date(target):
            prediction = self.predictions.latest(fixture.fixture_id, before=fixture.kickoff_utc)
            probabilities = {
                **(prediction or {}).get("goals", {}).get("probabilities", {}),
                **(prediction or {}).get("corners", {}).get("probabilities", {}),
            }
            row = fixture.model_dump(mode="json")
            names = {normalize_name(fixture.home_team), normalize_name(fixture.away_team)}
            row["search_names"] = [
                alias for alias, canonical in ALIASES.items() if canonical in names
            ]
            row["kickoff_local"] = fixture.kickoff_utc.astimezone(
                self.environment.timezone
            ).isoformat()
            row["prediction"] = (
                {
                    key: value
                    for key, value in prediction.items()
                    if key not in {"features", "fingerprint"}
                }
                if prediction
                else None
            )
            prices = self.odds.repository.current(fixture.fixture_id, before=fixture.kickoff_utc)
            row["markets"] = {
                market.value: self.odds.compare(
                    fixture.fixture_id,
                    market,
                    probabilities.get(market.value),
                    settings.odds_stale_minutes,
                    settings.enabled_bookmakers,
                    before=fixture.kickoff_utc,
                    available_prices=prices,
                )
                for market in Market
            }
            rows.append(row)
        return rows

    def today(self, target: date, settings: UserSettings) -> dict:
        rows = self.rows(target, settings)
        complete = sum(
            bool(row["prediction"] and row["prediction"]["quality"]["score"] >= 75) for row in rows
        )
        analysed = sum(
            bool(row["prediction"] and row["prediction"]["goals"]["probabilities"]) for row in rows
        )
        stats_updates = [
            row["prediction"]["quality"]["last_updated"]
            for row in rows
            if row["prediction"] and row["prediction"]["quality"].get("last_updated")
        ]
        odds_updates = [
            q["timestamp"]
            for row in rows
            for m in row["markets"].values()
            for q in m["quotes"].values()
            if q
        ]
        fixture_updates = [row["updated_at"] for row in rows]
        groups = [
            Market(key)
            for key, value in read_config("ranking")["markets"].items()
            if value.get("enabled")
        ]
        return {
            "date": target.isoformat(),
            "timezone": self.environment.app_timezone,
            "fixtures_found": len(rows),
            "fixtures_analysed": analysed,
            "complete_data": complete,
            "partial_data": max(0, analysed - complete),
            "insufficient_data": len(rows) - analysed,
            "last_stats_update": max(stats_updates, default=None),
            "last_odds_update": max(odds_updates, default=None),
            "last_fixtures_update": max(fixture_updates, default=None),
            "fixtures": rows,
            "top_groups": {
                m.value: self.ranking.rank(rows, m, settings, bookmaker=settings.default_bookmaker)
                for m in groups
            },
        }
