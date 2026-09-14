from datetime import UTC, datetime, timedelta

from app.domain.fixture import Fixture, FixtureStatus, MatchObservation

STATUS = {
    "NS": FixtureStatus.NOT_STARTED,
    "TBD": FixtureStatus.POSTPONED,
    "PST": FixtureStatus.POSTPONED,
    "SUSP": FixtureStatus.POSTPONED,
    "CANC": FixtureStatus.CANCELLED,
    "ABD": FixtureStatus.CANCELLED,
    "AWD": FixtureStatus.CANCELLED,
    "WO": FixtureStatus.CANCELLED,
    "FT": FixtureStatus.FINISHED,
    "AET": FixtureStatus.FINISHED,
    "PEN": FixtureStatus.FINISHED,
}


def normalize_fixture(raw: dict, observed_at: datetime) -> Fixture:
    fixture, teams, league = raw["fixture"], raw["teams"], raw["league"]
    score = (raw.get("score") or {}).get("fulltime") or raw.get("goals") or {}
    return Fixture(
        fixture_id=fixture["id"],
        provider_fixture_id=str(fixture["id"]),
        kickoff_utc=datetime.fromisoformat(fixture["date"]).astimezone(UTC),
        country=league.get("country", ""),
        league_id=league["id"],
        league_name=league["name"],
        season=league["season"],
        home_team_id=teams["home"]["id"],
        home_team=teams["home"]["name"],
        away_team_id=teams["away"]["id"],
        away_team=teams["away"]["name"],
        status=STATUS.get(fixture["status"]["short"], FixtureStatus.LIVE),
        source_status=fixture["status"]["short"],
        home_goals=score.get("home"),
        away_goals=score.get("away"),
        updated_at=observed_at,
    )


def observations(raw: dict, observed_at: datetime) -> list[MatchObservation]:
    fixture = normalize_fixture(raw, observed_at)
    if (
        fixture.status != FixtureStatus.FINISHED
        or fixture.home_goals is None
        or fixture.away_goals is None
    ):
        return []
    return [
        MatchObservation(
            statistics_allowed=raw["fixture"]["status"]["short"] == "FT",
            fixture_id=fixture.fixture_id,
            team_id=team,
            opponent_id=opponent,
            kickoff_utc=fixture.kickoff_utc,
            completed_at=fixture.kickoff_utc + timedelta(hours=3),
            is_home=home,
            goals_for=gf,
            goals_against=ga,
            league_id=fixture.league_id,
            competition=fixture.league_name,
            observed_at=observed_at,
        )
        for team, opponent, home, gf, ga in [
            (
                fixture.home_team_id,
                fixture.away_team_id,
                True,
                fixture.home_goals,
                fixture.away_goals,
            ),
            (
                fixture.away_team_id,
                fixture.home_team_id,
                False,
                fixture.away_goals,
                fixture.home_goals,
            ),
        ]
    ]


def number(value) -> float | None:
    if value is None:
        return None
    try:
        result = float(str(value).rstrip("%"))
        return result if 0 <= result < float("inf") else None
    except (ValueError, TypeError):
        return None


def normalize_statistics(rows: list[dict]) -> dict[int, dict]:
    names = {
        "Corner Kicks": "corners",
        "Total Shots": "shots",
        "Shots on Goal": "shots_on_target",
        "Ball Possession": "possession",
        "expected_goals": "xg",
    }
    return {
        row["team"]["id"]: {
            names[entry["type"]]: number(entry.get("value"))
            for entry in row.get("statistics", [])
            if entry.get("type") in names
        }
        for row in rows
    }
