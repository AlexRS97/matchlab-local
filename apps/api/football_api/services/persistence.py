import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from football_api.models import (
    Competition,
    Fixture,
    RawApiResponse,
    StandingSnapshot,
    Team,
    TeamFixtureStatistic,
)
from football_providers import ProviderResponse

FINISHED_STATUSES = {"FT", "AET", "PEN"}


def _integer_stat_value(values: dict[str | None, Any], name: str) -> int | None:
    value = values.get(name)
    if value is None:
        return None
    try:
        return int(float(str(value).replace("%", "")))
    except ValueError:
        return None


def store_raw_response(db: Session, response: ProviderResponse) -> RawApiResponse:
    serialized = json.dumps(response.body, sort_keys=True, separators=(",", ":"))
    raw = RawApiResponse(
        provider="api_football",
        endpoint=response.endpoint,
        request_parameters=response.parameters,
        response_json=response.body,
        requested_at=datetime.now(UTC),
        http_status=response.status_code,
        response_hash=hashlib.sha256(serialized.encode()).hexdigest(),
    )
    db.add(raw)
    return raw


def upsert_league_catalog(db: Session, items: list[dict[str, Any]]) -> int:
    stored = 0
    for item in items:
        league = item.get("league", {})
        provider_id = league.get("id")
        if provider_id is None:
            continue
        competition = db.scalar(
            select(Competition).where(
                Competition.provider == "api_football",
                Competition.provider_id == int(provider_id),
            )
        )
        if competition is None:
            competition = Competition(
                provider="api_football",
                provider_id=int(provider_id),
                name=league.get("name") or f"Competicion {provider_id}",
            )
            db.add(competition)
        seasons = item.get("seasons", [])
        current_season = next((season for season in seasons if season.get("current")), None)
        competition.name = league.get("name") or competition.name
        competition.competition_type = league.get("type")
        competition.logo_url = league.get("logo")
        country = item.get("country") or {}
        competition.country = country.get("name") if isinstance(country, dict) else country
        competition.coverage = (current_season or {}).get("coverage") or {}
        competition.is_friendly = "friend" in competition.name.lower()
        stored += 1
    return stored


def _upsert_competition(db: Session, item: dict[str, Any]) -> Competition:
    league = item.get("league", {})
    provider_id = int(league["id"])
    competition = db.scalar(
        select(Competition).where(
            Competition.provider == "api_football", Competition.provider_id == provider_id
        )
    )
    name = league.get("name") or f"Competicion {provider_id}"
    if competition is None:
        competition = Competition(provider_id=provider_id, name=name)
        db.add(competition)
    competition.name = name
    competition.country = league.get("country")
    competition.logo_url = league.get("logo")
    competition.is_friendly = "friend" in name.lower() or "amist" in name.lower()
    return competition


def _upsert_team(db: Session, data: dict[str, Any]) -> Team:
    provider_id = int(data["id"])
    team = db.scalar(
        select(Team).where(Team.provider == "api_football", Team.provider_id == provider_id)
    )
    if team is None:
        team = Team(provider_id=provider_id, name=data.get("name") or f"Equipo {provider_id}")
        db.add(team)
    team.name = data.get("name") or team.name
    team.logo_url = data.get("logo")
    return team


def upsert_fixture(db: Session, item: dict[str, Any]) -> Fixture:
    fixture_data = item.get("fixture", {})
    provider_id = int(fixture_data["id"])
    competition = _upsert_competition(db, item)
    teams = item.get("teams", {})
    home_team = _upsert_team(db, teams["home"])
    away_team = _upsert_team(db, teams["away"])
    db.flush()

    fixture = db.scalar(
        select(Fixture).where(
            Fixture.provider == "api_football", Fixture.provider_id == provider_id
        )
    )
    if fixture is None:
        fixture = Fixture(
            provider_id=provider_id,
            competition_id=competition.id,
            season=int(item.get("league", {}).get("season") or datetime.now().year),
            kickoff_at=datetime.now(UTC),
            home_team_id=home_team.id,
            away_team_id=away_team.id,
        )
        db.add(fixture)

    kickoff = fixture_data.get("date")
    if kickoff:
        fixture.kickoff_at = datetime.fromisoformat(kickoff.replace("Z", "+00:00"))
    status = fixture_data.get("status", {})
    goals = item.get("goals", {})
    fixture.competition_id = competition.id
    fixture.season = int(item.get("league", {}).get("season") or fixture.season)
    fixture.round_name = item.get("league", {}).get("round")
    fixture.status = status.get("short") or "NS"
    fixture.status_long = status.get("long")
    fixture.home_team_id = home_team.id
    fixture.away_team_id = away_team.id
    fixture.home_goals = goals.get("home")
    fixture.away_goals = goals.get("away")
    fixture.venue_name = (fixture_data.get("venue") or {}).get("name")
    fixture.referee = fixture_data.get("referee")
    return fixture


def upsert_fixture_statistics(
    db: Session, fixture: Fixture, response_items: list[dict[str, Any]]
) -> int:
    stored = 0
    for block in response_items:
        team_data = block.get("team", {})
        provider_team_id = team_data.get("id")
        if provider_team_id is None:
            continue
        team = db.scalar(select(Team).where(Team.provider_id == int(provider_team_id)))
        if team is None:
            team = _upsert_team(db, team_data)
            db.flush()
        values = {stat.get("type"): stat.get("value") for stat in block.get("statistics", [])}

        stat = db.scalar(
            select(TeamFixtureStatistic).where(
                TeamFixtureStatistic.fixture_id == fixture.id,
                TeamFixtureStatistic.team_id == team.id,
            )
        )
        if stat is None:
            stat = TeamFixtureStatistic(
                fixture_id=fixture.id,
                team_id=team.id,
                is_home=team.id == fixture.home_team_id,
            )
            db.add(stat)
        stat.corners = _integer_stat_value(values, "Corner Kicks")
        stat.shots_on_goal = _integer_stat_value(values, "Shots on Goal")
        stat.total_shots = _integer_stat_value(values, "Total Shots")
        possession = _integer_stat_value(values, "Ball Possession")
        stat.possession = float(possession) if possession is not None else None
        stat.raw_statistics = values
        stored += 1
    return stored


def store_standings(
    db: Session,
    competition: Competition,
    season: int,
    response_items: list[dict[str, Any]],
) -> int:
    now = datetime.now(UTC)
    stored = 0
    for league_block in response_items:
        groups = league_block.get("league", {}).get("standings", [])
        for group in groups:
            for row in group:
                team = _upsert_team(db, row.get("team", {}))
                db.flush()
                record = row.get("all", {})
                goals = record.get("goals", {})
                db.add(
                    StandingSnapshot(
                        competition_id=competition.id,
                        team_id=team.id,
                        season=season,
                        snapshot_at=now,
                        rank=row.get("rank"),
                        points=row.get("points"),
                        played=record.get("played"),
                        wins=record.get("win"),
                        draws=record.get("draw"),
                        losses=record.get("lose"),
                        goals_for=goals.get("for"),
                        goals_against=goals.get("against"),
                        form=row.get("form"),
                    )
                )
                stored += 1
    return stored
