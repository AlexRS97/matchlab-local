from datetime import date
from zoneinfo import ZoneInfo

from app.db.connection import Database
from app.domain.fixture import Fixture


class FixtureRepository:
    def __init__(self, db: Database, timezone: str = "Europe/Madrid"):
        self.db, self.timezone = db, ZoneInfo(timezone)

    def save(self, fixture: Fixture):
        local = fixture.kickoff_utc.astimezone(self.timezone)
        self.db.execute(
            "INSERT OR REPLACE INTO fixtures VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [
                fixture.fixture_id,
                fixture.provider,
                fixture.provider_fixture_id,
                local.date(),
                fixture.kickoff_utc,
                local.isoformat(),
                fixture.country,
                fixture.league_id,
                fixture.league_name,
                fixture.season,
                fixture.home_team_id,
                fixture.home_team,
                fixture.away_team_id,
                fixture.away_team,
                fixture.status.value,
                fixture.updated_at,
                fixture.model_dump_json(),
            ],
        )
        for team_id, name in [
            (fixture.home_team_id, fixture.home_team),
            (fixture.away_team_id, fixture.away_team),
        ]:
            self.db.execute(
                "INSERT OR REPLACE INTO teams VALUES (?,?,?)", [team_id, name, fixture.provider]
            )
        self.db.execute(
            "INSERT OR REPLACE INTO leagues VALUES (?,?,?)",
            [fixture.league_id, fixture.league_name, fixture.country],
        )

    def for_date(self, target: date) -> list[Fixture]:
        return [
            Fixture.model_validate_json(row["payload"])
            for row in self.db.query(
                "SELECT payload FROM fixtures WHERE date=? ORDER BY kickoff_utc, fixture_id",
                [target],
            )
        ]

    def get(self, fixture_id: int) -> Fixture | None:
        rows = self.db.query("SELECT payload FROM fixtures WHERE fixture_id=?", [fixture_id])
        return Fixture.model_validate_json(rows[0]["payload"]) if rows else None

    def leagues(self):
        return self.db.query("SELECT * FROM leagues ORDER BY country, name")
