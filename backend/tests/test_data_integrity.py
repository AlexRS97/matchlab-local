import json
import os
from datetime import UTC, datetime

import duckdb
import httpx
import pytest
from test_models import features

from app.db.connection import Database
from app.providers.football_data.provider import FootballDataProvider
from app.services.performance_service import PerformanceService

CSV = "Date,HomeTeam,AwayTeam,FTHG,FTAG,HC,AC\n01/01/2020,A,B,2,1,5,4\n"


def test_historical_partition_is_idempotent_and_corrects_changed_keys(tmp_path):
    db = Database(":memory:")
    repository = FootballDataProvider(db, tmp_path).repository
    rows = FootballDataProvider.parse(CSV, "E0", "1920")
    assert repository.replace("E0", "1920", rows)
    before = db.query("SELECT * FROM historical_matches")
    revision = repository.revision()
    assert not repository.replace("E0", "1920", rows)
    assert db.query("SELECT * FROM historical_matches") == before
    corrected = FootballDataProvider.parse(CSV.replace("01/01", "02/01"), "E0", "1920")
    assert repository.replace("E0", "1920", corrected)
    assert repository.revision() != revision
    stored = db.query("SELECT payload FROM historical_matches")
    assert len(stored) == 1 and json.loads(stored[0]["payload"])["date"] == "2020-01-02"
    db.close()


def test_invalid_or_shrinking_import_preserves_last_good_partition(tmp_path):
    db = Database(":memory:")
    repository = FootballDataProvider(db, tmp_path).repository
    rows = FootballDataProvider.parse(CSV, "E0", "1920")
    repository.replace("E0", "1920", rows)
    before = db.query("SELECT * FROM historical_matches")
    revision = repository.revision()
    with pytest.raises(ValueError, match="duplicados"):
        repository.replace("E0", "1920", rows * 2)
    with pytest.raises(ValueError, match="conserva"):
        repository.replace("E0", "1920", [])
    with pytest.raises(duckdb.ConversionException):
        repository.replace("E0", "1920", [{**rows[0], "date": "invalid"}])
    assert db.query("SELECT * FROM historical_matches") == before
    assert repository.revision() == revision
    db.close()


async def test_bad_download_falls_back_to_good_csv_without_overwriting_it(tmp_path, monkeypatch):
    db = Database(":memory:")
    provider = FootballDataProvider(db, tmp_path)
    path = tmp_path / "E0_1920.csv"
    path.write_text(CSV, encoding="utf-8")
    os.utime(path, (0, 0))
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, text="<html>unavailable</html>")
        )
    )
    monkeypatch.setattr(
        "app.providers.football_data.provider.httpx.AsyncClient", lambda **_: client
    )
    result = await provider.update(["E0"], ["1920"])
    assert result["errors"] and result["stored_matches"] == 1
    assert path.read_text(encoding="utf-8") == CSV
    db.close()


def test_performance_uses_resolved_cohort_and_corrects_results_without_duplicate_settlement():
    db = Database(":memory:")
    service = PerformanceService(db)
    f = features().fixture
    for fixture_id, probability in ((f.fixture_id, 0.6), (f.fixture_id + 1, 0.99)):
        db.execute(
            "INSERT INTO prediction_results VALUES (?,?,?,?,?,NULL,NULL,?,NULL)",
            [fixture_id, datetime.now(UTC), "OVER_2_5_GOALS", probability, 2.0, "BET365"],
        )
    pending = service.metrics()[0]
    assert pending["average_predicted_probability"] is None and pending["hit_rate_interval"] is None
    finished = f.model_copy(update={"status": "FINISHED", "home_goals": 2, "away_goals": 1})
    service.settle(finished)
    original = db.query(
        "SELECT settled_at FROM prediction_results WHERE fixture_id=?", [f.fixture_id]
    )
    service.settle(finished)
    assert (
        db.query("SELECT settled_at FROM prediction_results WHERE fixture_id=?", [f.fixture_id])
        == original
    )
    metrics = service.metrics()[0]
    assert metrics["average_predicted_probability"] == pytest.approx(0.6)
    assert metrics["brier_score"] == pytest.approx(0.16)
    assert 0 < metrics["hit_rate_interval"]["low"] < metrics["hit_rate_interval"]["high"] <= 1
    service.settle(finished.model_copy(update={"away_goals": 0}))
    corrected = service.metrics()[0]
    assert corrected["settled_predictions"] == 1 and corrected["hit_rate"] == 0
    assert corrected["brier_score"] == pytest.approx(0.36)
    assert corrected["roi"] == -1 and corrected["log_loss"] > 0
    db.close()
