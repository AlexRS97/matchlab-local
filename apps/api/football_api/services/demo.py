import random
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from football_api.models import Competition, Fixture, StandingSnapshot, Team, TeamFixtureStatistic

DEMO_TEAMS = [
    (-101, "Atlético Norte"),
    (-102, "Real Bahía"),
    (-103, "Unión Central"),
    (-104, "Deportivo Sierra"),
    (-105, "Sporting Levante"),
    (-106, "Racing del Sur"),
]


def seed_demo_data(db: Session, target_date: date, timezone) -> list[Fixture]:
    competition = db.scalar(select(Competition).where(Competition.provider_id == -1))
    if competition is None:
        competition = Competition(
            provider="demo",
            provider_id=-1,
            name="Liga Demo Profesional",
            country="España",
            competition_type="League",
            coverage={"fixtures": {"statistics_fixtures": True}, "standings": True},
        )
        db.add(competition)

    teams: list[Team] = []
    for provider_id, name in DEMO_TEAMS:
        team = db.scalar(
            select(Team).where(Team.provider == "demo", Team.provider_id == provider_id)
        )
        if team is None:
            team = Team(provider="demo", provider_id=provider_id, name=name, country="España")
            db.add(team)
        teams.append(team)
    db.flush()

    rng = random.Random(20260717)
    for days_ago in range(1, 46):
        match_date = target_date - timedelta(days=days_ago)
        rotation = days_ago % len(teams)
        pairings = [
            (teams[rotation], teams[(rotation + 1) % 6]),
            (teams[(rotation + 2) % 6], teams[(rotation + 3) % 6]),
            (teams[(rotation + 4) % 6], teams[(rotation + 5) % 6]),
        ]
        for index, (home, away) in enumerate(pairings):
            provider_id = -(days_ago * 10 + index + 1000)
            fixture = db.scalar(
                select(Fixture).where(
                    Fixture.provider == "demo", Fixture.provider_id == provider_id
                )
            )
            if fixture is None:
                kickoff_local = datetime.combine(match_date, time(18 + index), tzinfo=timezone)
                home_goals = min(5, int(rng.expovariate(1 / 1.45)))
                away_goals = min(5, int(rng.expovariate(1 / 1.15)))
                fixture = Fixture(
                    provider="demo",
                    provider_id=provider_id,
                    competition_id=competition.id,
                    season=target_date.year,
                    round_name=f"Jornada {46 - days_ago}",
                    kickoff_at=kickoff_local.astimezone(UTC),
                    status="FT",
                    status_long="Match Finished",
                    home_team_id=home.id,
                    away_team_id=away.id,
                    home_goals=home_goals,
                    away_goals=away_goals,
                    venue_name="Estadio Demo",
                )
                db.add(fixture)
                db.flush()
                for team, is_home in ((home, True), (away, False)):
                    db.add(
                        TeamFixtureStatistic(
                            fixture_id=fixture.id,
                            team_id=team.id,
                            is_home=is_home,
                            corners=max(1, int(rng.gauss(5.1 if is_home else 4.3, 1.8))),
                            shots_on_goal=max(1, int(rng.gauss(5.0, 2.0))),
                            total_shots=max(4, int(rng.gauss(12.0, 3.2))),
                            possession=max(30.0, min(70.0, rng.gauss(50.0, 8.0))),
                            raw_statistics={},
                        )
                    )

    today_pairings = [(teams[0], teams[1]), (teams[2], teams[3]), (teams[4], teams[5])]
    fixtures_today: list[Fixture] = []
    for index, (home, away) in enumerate(today_pairings):
        provider_id = -(target_date.toordinal() * 10 + index)
        fixture = db.scalar(
            select(Fixture).where(Fixture.provider == "demo", Fixture.provider_id == provider_id)
        )
        if fixture is None:
            kickoff_local = datetime.combine(target_date, time(15 + index * 3), tzinfo=timezone)
            fixture = Fixture(
                provider="demo",
                provider_id=provider_id,
                competition_id=competition.id,
                season=target_date.year,
                round_name="Jornada actual",
                kickoff_at=kickoff_local.astimezone(UTC),
                status="NS",
                status_long="Not Started",
                home_team_id=home.id,
                away_team_id=away.id,
                venue_name=f"Campo de {home.name}",
            )
            db.add(fixture)
            db.flush()
        fixtures_today.append(fixture)

    has_standings = db.scalar(
        select(StandingSnapshot.id).where(
            StandingSnapshot.competition_id == competition.id,
            StandingSnapshot.snapshot_at >= datetime.combine(target_date, time.min, tzinfo=UTC),
        )
    )
    if has_standings is None:
        now = datetime.now(UTC)
        for rank, team in enumerate(teams, start=1):
            db.add(
                StandingSnapshot(
                    competition_id=competition.id,
                    team_id=team.id,
                    season=target_date.year,
                    snapshot_at=now,
                    rank=rank,
                    points=38 - rank * 3,
                    played=24,
                    wins=13 - rank,
                    draws=5,
                    losses=6 + rank,
                    goals_for=42 - rank * 2,
                    goals_against=23 + rank * 2,
                    form="WWDLW" if rank <= 3 else "LDWDL",
                )
            )
    db.commit()
    return fixtures_today

