import pytest

from app.core import resources
from app.db.connection import Database


def test_cpu_detection_respects_affinity_and_falls_back(monkeypatch):
    monkeypatch.setattr(resources.os, "sched_getaffinity", lambda _: {1, 2, 3}, raising=False)
    monkeypatch.setattr(resources.os, "cpu_count", lambda: 24)
    assert resources.available_cpu_threads() == 3
    monkeypatch.setattr(resources.os, "sched_getaffinity", None)
    assert resources.available_cpu_threads() == 24
    monkeypatch.setattr(resources.os, "cpu_count", lambda: None)
    assert resources.available_cpu_threads() == 1


def test_automatic_capacity_and_explicit_test_budget(monkeypatch):
    monkeypatch.setattr(resources, "available_cpu_threads", lambda: 24)
    assert resources.resolve_threads("auto") == resources.resolve_threads() == 24
    assert resources.resolve_threads(1) == 1
    assert resources.resolve_threads(100) == 24
    with pytest.raises(ValueError):
        resources.resolve_threads(0)


def test_database_uses_available_capacity(monkeypatch):
    monkeypatch.setattr("app.db.connection.available_cpu_threads", lambda: 6)
    db = Database(":memory:")
    try:
        assert db.query("SELECT current_setting('threads') AS n")[0]["n"] == 6
    finally:
        db.close()
