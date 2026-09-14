import hashlib
import json
from datetime import UTC, datetime

from app.db.connection import Database, encode


class HistoricalRepository:
    """Replace one validated source partition atomically; unchanged imports perform no writes."""

    def __init__(self, db: Database):
        self.db = db

    def replace(self, league: str, season: str, rows: list[dict]) -> bool:
        keys = [row["match_key"] for row in rows]
        if len(keys) != len(set(keys)):
            raise ValueError(f"{league} {season}: partidos duplicados; se conserva el histórico")
        digest = hashlib.sha256(
            json.dumps(sorted(rows, key=lambda r: r["match_key"]), sort_keys=True).encode()
        ).hexdigest()
        with self.db.lock:
            previous = self.db.query(
                "SELECT digest FROM historical_imports WHERE league_code=? AND season=?",
                [league, season],
            )
            if previous and previous[0]["digest"] == digest:
                return False
            count = self.db.query(
                "SELECT count(*) AS n FROM historical_matches WHERE league_code=? AND json_extract_string(payload, '$.season')=?",
                [league, season],
            )[0]["n"]
            if len(rows) < count:
                raise ValueError(
                    f"{league} {season}: la fuente ha pasado de {count} a {len(rows)} filas; se conserva el histórico"
                )
            connection = self.db.connection
            connection.execute("BEGIN TRANSACTION")
            try:
                connection.execute(
                    "DELETE FROM historical_matches WHERE league_code=? AND json_extract_string(payload, '$.season')=?",
                    [league, season],
                )
                if rows:
                    connection.execute(
                        """INSERT INTO historical_matches
                        SELECT json_extract_string(value, '$.match_key'), ?,
                               CAST(json_extract_string(value, '$.date') AS DATE), 'football_data', ?, value
                        FROM json_each(?)""",
                        [league, datetime.now(UTC), encode(rows)],
                    )
                connection.execute(
                    "INSERT OR REPLACE INTO historical_imports VALUES (?,?,?,?,?,?)",
                    [
                        league,
                        season,
                        digest,
                        len(rows),
                        max((r["date"] for r in rows), default=None),
                        datetime.now(UTC),
                    ],
                )
                connection.execute("COMMIT")
            except Exception:
                connection.execute("ROLLBACK")
                raise
        return True

    def coverage(self) -> list[dict]:
        return self.db.query("""SELECT league_code, count(*) AS matches, max(match_date) AS latest_match,
            min(match_date) AS first_match FROM historical_matches GROUP BY league_code ORDER BY league_code""")

    def revision(self) -> str | None:
        rows = self.db.query(
            "SELECT league_code, season, digest FROM historical_imports ORDER BY league_code, season"
        )
        return hashlib.sha256(encode(rows).encode()).hexdigest() if rows else None
