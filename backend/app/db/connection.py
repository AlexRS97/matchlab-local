import json
import threading
from pathlib import Path
from typing import Any

import duckdb

from app.core.resources import available_cpu_threads
from app.db.schema import SCHEMA


def encode(value: Any) -> str:
    return json.dumps(value, default=str, ensure_ascii=False, allow_nan=False)


class Database:
    """One process, one connection, serialized access. Never run multiple Uvicorn workers."""

    def __init__(self, path: str):
        self.path = path
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.connection = duckdb.connect(path, config={"threads": available_cpu_threads()})
        self.execute(SCHEMA)

    def execute(self, sql: str, parameters: list | None = None) -> None:
        with self.lock:
            self.connection.execute(sql, parameters or [])

    def query(self, sql: str, parameters: list | None = None) -> list[dict]:
        with self.lock:
            cursor = self.connection.execute(sql, parameters or [])
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]

    def execute_many(self, sql: str, rows: list[list]) -> None:
        if not rows:
            return
        with self.lock:
            self.connection.execute("BEGIN TRANSACTION")
            try:
                self.connection.executemany(sql, rows)
                self.connection.execute("COMMIT")
            except Exception:
                self.connection.execute("ROLLBACK")
                raise

    def close(self) -> None:
        with self.lock:
            self.connection.close()
