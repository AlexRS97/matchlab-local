from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db.connection import Database
from app.main import create_app
from app.repositories.cache import CacheRepository


def test_app_and_schema():
    with TestClient(create_app(Settings(duckdb_path=":memory:", enable_scheduler=False))) as client:
        assert client.get("/api/health").json()["status"] == "ok"
        tables = client.app.state.db.query("SHOW TABLES")
        assert len(tables) >= 20
        assert client.get("/health").headers["X-Content-Type-Options"] == "nosniff"


def test_cache_ttl_and_stale():
    db = Database(":memory:")
    cache = CacheRepository(db)
    now = datetime.now(UTC)
    cache.put("test", "fixture", [1, 2], 60, now)
    assert cache.get("test", now=now)["data"] == [1, 2]
    assert cache.get("test", now=now + timedelta(seconds=61)) is None
    assert cache.get("test", now=now + timedelta(seconds=61), stale=True)["stale"]
    db.close()
