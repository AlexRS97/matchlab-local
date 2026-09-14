import json
from datetime import datetime
from uuid import uuid4

from app.db.connection import Database, encode
from app.domain.fixture import MatchObservation


class StatsRepository:
    def __init__(self, db: Database):
        self.db = db

    def save_matches(self, observations: list[MatchObservation]):
        for obs in observations:
            existing = self.db.query(
                "SELECT payload FROM recent_matches WHERE fixture_id=? AND team_id=?",
                [obs.fixture_id, obs.team_id],
            )
            if existing:
                old = MatchObservation.model_validate_json(existing[0]["payload"])
                # Preserve collected statistics when the fixture-list endpoint has no statistics.
                for field in (
                    "corners_for",
                    "corners_against",
                    "shots",
                    "shots_on_target",
                    "possession",
                    "xg",
                    "xga",
                ):
                    if getattr(obs, field) is None:
                        setattr(obs, field, getattr(old, field))
            self.db.execute(
                "INSERT OR REPLACE INTO recent_matches VALUES (?,?,?,?,?)",
                [
                    obs.fixture_id,
                    obs.team_id,
                    obs.kickoff_utc,
                    obs.observed_at,
                    obs.model_dump_json(),
                ],
            )

    def matches(self, team_id: int, before: datetime, limit: int = 40) -> list[MatchObservation]:
        rows = self.db.query(
            """SELECT payload FROM recent_matches WHERE team_id=? AND kickoff_utc<?
          AND observed_at<? ORDER BY kickoff_utc DESC LIMIT ?""",
            [team_id, before, before, limit],
        )
        return [
            obs
            for row in rows
            if (obs := MatchObservation.model_validate_json(row["payload"])).completed_at < before
        ]

    def league_matches(self, league_id: int, before: datetime) -> list[MatchObservation]:
        rows = self.db.query(
            """SELECT payload FROM recent_matches WHERE kickoff_utc<? AND observed_at<?
            AND CAST(json_extract(payload,'$.league_id') AS BIGINT)=?
            AND CAST(json_extract(payload,'$.is_home') AS BOOLEAN)=true
            ORDER BY kickoff_utc DESC LIMIT 200""",
            [before, before, league_id],
        )
        return [
            obs
            for row in rows
            if (obs := MatchObservation.model_validate_json(row["payload"])).league_id == league_id
            and obs.is_home
            and obs.completed_at < before
        ]

    def h2h(self, team_id: int, opponent_id: int, before: datetime) -> list[MatchObservation]:
        return [
            obs
            for obs in self.matches(team_id, before, limit=500)
            if obs.opponent_id == opponent_id
        ][:10]

    def save_standings(self, league: int, season: int, data: list, timestamp: datetime):
        if data:
            self.db.execute(
                "INSERT INTO standings_snapshots VALUES (?,?,?,?,?)",
                [str(uuid4()), league, season, timestamp, encode(data)],
            )

    def standings(self, league: int, season: int, before: datetime) -> list[dict]:
        rows = self.db.query(
            """SELECT payload FROM standings_snapshots WHERE league_id=? AND season=?
           AND timestamp<? ORDER BY timestamp DESC LIMIT 1""",
            [league, season, before],
        )
        return json.loads(rows[0]["payload"]) if rows else []

    def save_statistics(self, fixture_id: int, statistics: dict, timestamp: datetime):
        self.db.execute(
            "INSERT OR REPLACE INTO fixture_statistics VALUES (?,?,?)",
            [fixture_id, timestamp, encode(statistics)],
        )

    def statistics(self, fixture_id: int) -> dict | None:
        rows = self.db.query(
            "SELECT payload, timestamp FROM fixture_statistics WHERE fixture_id=?", [fixture_id]
        )
        return (
            {"data": json.loads(rows[0]["payload"]), "timestamp": rows[0]["timestamp"]}
            if rows
            else None
        )
