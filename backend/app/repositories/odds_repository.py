import hashlib
import json
from datetime import datetime

from app.db.connection import Database, encode
from app.domain.odds import NormalizedOdds


class OddsRepository:
    def __init__(self, db: Database):
        self.db = db

    def save(self, odds: list[NormalizedOdds]):
        for price in odds:
            if price.fixture_id is None:
                raise ValueError("No se guardan cuotas sin emparejamiento seguro")
            payload = price.model_dump_json()
            identifier = hashlib.sha256(payload.encode()).hexdigest()
            self.db.execute(
                "INSERT INTO odds_snapshots VALUES (?,?,?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING",
                [
                    identifier,
                    price.fixture_id,
                    price.bookmaker.value,
                    price.provider,
                    price.market.value,
                    price.line,
                    price.selection,
                    price.decimal_odds,
                    price.timestamp,
                    payload,
                ],
            )

    def current(self, fixture_id: int, before: datetime | None = None) -> list[NormalizedOdds]:
        rows = self.db.query(
            """SELECT payload FROM odds_snapshots WHERE fixture_id=?
          AND (? IS NULL OR timestamp<?)
          QUALIFY ROW_NUMBER() OVER (PARTITION BY bookmaker, provider, market, side ORDER BY timestamp DESC)=1""",
            [fixture_id, before, before],
        )
        boards = self.db.query(
            """SELECT provider,bookmaker,payload FROM odds_boards WHERE fixture_id=?
            AND (? IS NULL OR timestamp<?)
            QUALIFY ROW_NUMBER() OVER(PARTITION BY provider,bookmaker ORDER BY timestamp DESC)=1""",
            [fixture_id, before, before],
        )
        available = {(b["provider"], b["bookmaker"]): set(json.loads(b["payload"])) for b in boards}
        prices = [NormalizedOdds.model_validate_json(row["payload"]) for row in rows]
        return [
            p
            for p in prices
            if (p.provider, p.bookmaker.value) not in available
            or f"{p.market.value}:{p.selection}" in available[(p.provider, p.bookmaker.value)]
        ]

    def save_board(
        self,
        fixture_id: int,
        provider: str,
        bookmaker: str,
        timestamp: datetime,
        prices: list[NormalizedOdds],
    ):
        keys = sorted({f"{p.market.value}:{p.selection}" for p in prices})
        self.db.execute(
            "INSERT INTO odds_boards VALUES (?,?,?,?,?) ON CONFLICT DO NOTHING",
            [fixture_id, provider, bookmaker, timestamp, encode(keys)],
        )

    def history(self, fixture_id: int) -> list[NormalizedOdds]:
        return [
            NormalizedOdds.model_validate_json(row["payload"])
            for row in self.db.query(
                "SELECT payload FROM odds_snapshots WHERE fixture_id=? ORDER BY timestamp DESC LIMIT 1000",
                [fixture_id],
            )
        ]
