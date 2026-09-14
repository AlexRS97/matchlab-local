from datetime import UTC, datetime

from scipy.stats import binomtest

from app.db.connection import Database
from app.domain.fixture import Fixture, FixtureStatus
from app.domain.market import Market


class PerformanceService:
    """One first published pre-match forecast per fixture/market to avoid repeated counting."""

    def __init__(self, db: Database):
        self.db = db

    def record(self, rows: list[dict]):
        now = datetime.now(UTC)
        for row in rows:
            prediction = row.get("prediction")
            if (
                not prediction
                or row["status"] != "NOT_STARTED"
                or datetime.fromisoformat(row["kickoff_utc"]) <= now
            ):
                continue
            for market, comparison in row["markets"].items():
                probability = comparison.get("model_probability")
                if probability is None:
                    continue
                best = comparison["best"]
                if best and best["stale"]:
                    best = None
                self.db.execute(
                    """INSERT INTO prediction_results
                    VALUES (?, ?, ?, ?, ?, NULL, NULL, ?, NULL) ON CONFLICT DO NOTHING""",
                    [
                        row["fixture_id"],
                        now,
                        market,
                        probability,
                        best["decimal_odds"] if best else None,
                        best["bookmaker"] if best else None,
                    ],
                )

    def settle(self, fixture: Fixture):
        if fixture.status != FixtureStatus.FINISHED:
            return
        rows = self.db.query(
            "SELECT market FROM prediction_results WHERE fixture_id=?",
            [fixture.fixture_id],
        )
        for row in rows:
            market = Market(row["market"])
            if market.value.endswith("CORNERS"):
                if fixture.home_corners is None or fixture.away_corners is None:
                    continue
                result = fixture.home_corners + fixture.away_corners
                won = result > (market.line or 0)
            elif market in {Market.BTTS_YES, Market.BTTS_NO}:
                if fixture.home_goals is None or fixture.away_goals is None:
                    continue
                result = int(fixture.home_goals > 0 and fixture.away_goals > 0)
                won = bool(result) if market == Market.BTTS_YES else not bool(result)
            else:
                if fixture.home_goals is None or fixture.away_goals is None:
                    continue
                result = fixture.home_goals + fixture.away_goals
                won = result > (market.line or 0)
            self.db.execute(
                "UPDATE prediction_results SET result=?, won=?, settled_at=? WHERE fixture_id=? AND market=? AND (result IS DISTINCT FROM ? OR won IS DISTINCT FROM ?)",
                [result, won, datetime.now(UTC), fixture.fixture_id, market.value, result, won],
            )

    def metrics(self):
        rows = self.db.query("""SELECT market, count(*) AS number_predictions,
          count(won) AS settled_predictions, avg(CASE WHEN won THEN 1.0 WHEN won IS NOT NULL THEN 0.0 END) AS hit_rate,
          sum(CASE WHEN won THEN 1 ELSE 0 END) AS wins,
          avg(CASE WHEN won IS NOT NULL THEN predicted_probability END) AS average_predicted_probability,
          avg(CASE WHEN won IS NOT NULL THEN pow(predicted_probability - CASE WHEN won THEN 1 ELSE 0 END, 2) END) AS brier_score,
          avg(CASE WHEN won IS NOT NULL THEN -ln(greatest(1e-7, least(1-1e-7, CASE WHEN won THEN predicted_probability ELSE 1-predicted_probability END))) END) AS log_loss,
          avg(CASE WHEN won IS NOT NULL AND odds_at_prediction IS NOT NULL
              THEN CASE WHEN won THEN odds_at_prediction - 1 ELSE -1 END END) AS roi,
          count(CASE WHEN won IS NOT NULL AND odds_at_prediction IS NOT NULL THEN 1 END) AS priced_results
          FROM prediction_results GROUP BY market ORDER BY market""")
        for row in rows:
            n = row["settled_predictions"]
            interval = binomtest(row.pop("wins"), n).proportion_ci(method="wilson") if n else None
            row["hit_rate_interval"] = (
                {
                    "low": float(interval.low),
                    "high": float(interval.high),
                    "level": 0.95,
                    "method": "wilson",
                }
                if interval
                else None
            )
            row["calibration_gap"] = (
                row["hit_rate"] - row["average_predicted_probability"] if n else None
            )
        return rows
