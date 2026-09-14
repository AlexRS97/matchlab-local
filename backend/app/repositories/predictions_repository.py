import json
from datetime import datetime
from uuid import uuid4

from app.db.connection import Database, encode


class PredictionsRepository:
    def __init__(self, db: Database):
        self.db = db

    def save(self, fixture_id: int, timestamp: datetime, payload: dict):
        identifier = str(uuid4())
        self.db.execute(
            "INSERT INTO predictions VALUES (?,?,?,?,?)",
            [identifier, fixture_id, timestamp, "statistical-v1", encode(payload)],
        )
        if payload.get("corners", {}).get("probabilities"):
            self.db.execute(
                "INSERT INTO corner_predictions VALUES (?,?,?,?)",
                [identifier, fixture_id, timestamp, encode(payload["corners"])],
            )

    def latest(self, fixture_id: int, before: datetime | None = None) -> dict | None:
        rows = self.db.query(
            """SELECT payload FROM predictions WHERE fixture_id=?
            AND (? IS NULL OR timestamp<?) ORDER BY timestamp DESC LIMIT 1""",
            [fixture_id, before, before],
        )
        return json.loads(rows[0]["payload"]) if rows else None
