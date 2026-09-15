import json
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import numpy as np
import pytest
from test_models import features

from app.db.connection import Database, encode
from app.domain.market import CORNER_MARKETS, GOAL_MARKETS, Market
from app.learning.dataset import HEADS, build_dataset, chronological_split
from app.learning.evaluation import calibrate, market_probabilities, paired_improvement
from app.learning.features import FEATURE_NAMES, Preprocessor
from app.learning.schema import SCHEMA
from app.learning.service import LearningService
from app.models.goals.dixon_coles import DixonColesModel
from app.models.goals.negative_binomial import GoalNegativeBinomialModel
from app.providers.football_data.provider import FootballDataProvider


def test_historical_csv_whitelist_and_missing_values():
    csv = "Date,HomeTeam,AwayTeam,FTHG,FTAG,HC,AC,HS,AS,HST,AST,B365H\n01/01/2020,A,B,2,1,5,4,12,8,4,2,1.50\n02/01/2020,C,D,,,4,3,,,,,\n"
    rows = FootballDataProvider.parse(csv, "E0", "1920")
    assert len(rows) == 1 and rows[0]["home_corners"] == 5
    assert "B365H" not in rows[0]
    assert not any("odds" in name.lower() or "b365" in name.lower() for name in FEATURE_NAMES)


def test_temporal_splits_have_embargo_and_no_overlap():
    dates = np.arange(200) * 86400
    split = chronological_split(dates)
    periods = [dates[split[key]] for key in ("train", "validation", "calibration", "test")]
    assert len(set(np.concatenate(list(split.values())))) == sum(map(len, split.values()))
    for past, future in zip(periods, periods[1:], strict=False):
        assert future.min() - past.max() > 2 * 86400


def test_preprocessing_is_fitted_only_from_training_and_tracks_missing():
    prep = Preprocessor().fit(np.asarray([[1, np.nan], [3, np.nan]], np.float32))
    prior = prep.state()
    result = prep.transform(np.asarray([[1000, 7], [np.nan, np.nan]], np.float32))
    assert prep.state() == prior and prior["median"] == [2, 0]
    assert result.shape == (2, 4) and np.isfinite(result).all()
    assert result[1, 2:].tolist() == [1, 1]
    with pytest.raises(ValueError, match="ajustado"):
        Preprocessor().transform(np.ones((1, 2)))


def test_calibrated_counts_obey_all_market_relationships():
    rng = np.random.default_rng(4)
    outputs = {key: rng.dirichlet(np.ones(size), 500) for key, size in HEADS.items()}
    labels = np.column_stack([rng.integers(0, size, 500) for size in HEADS.values()])
    temperatures = calibrate(outputs, labels)
    probabilities = market_probabilities(outputs, temperatures)
    assert set(probabilities) == {m.value for m in Market}
    assert np.allclose(probabilities["BTTS_YES"] + probabilities["BTTS_NO"], 1)
    assert np.all(probabilities["BTTS_YES"] <= probabilities["OVER_1_5_GOALS"])
    for group in (GOAL_MARKETS[:5], CORNER_MARKETS):
        for lower, higher in zip(group, group[1:], strict=False):
            assert np.all(probabilities[lower.value] >= probabilities[higher.value])
    assert all(0.5 <= t <= 5 for t in temperatures.values())


def test_bootstrap_gate_rejects_a_worse_model_and_insufficient_time_blocks():
    labels = np.tile([3, 1, 10], (500, 1))
    baseline = {m.value: np.full(500, 0.5) for m in Market}
    candidate = {m.value: np.full(500, 0.99 if (m.line or 0) > 3 else 0.01) for m in Market}
    assert not paired_improvement(candidate, baseline, labels, "goals", dates=np.zeros(500))[
        "promoted"
    ]
    perfect = {
        m.value: np.full(500, 1 if m == Market.BTTS_YES or (m.line or 0) < 3 else 0)
        for m in GOAL_MARKETS
    }
    assert not paired_improvement(perfect, baseline, labels, "goals", dates=np.zeros(500))[
        "promoted"
    ]


@pytest.mark.parametrize("model", [DixonColesModel(), GoalNegativeBinomialModel()])
def test_extended_statistical_models_are_valid_distributions(model):
    result = model.predict(features())
    assert all(0 <= p <= 1 for p in result.probabilities.values())
    assert result.probabilities["BTTS_YES"] + result.probabilities["BTTS_NO"] == pytest.approx(1)
    overs = [result.probabilities[m.value] for m in GOAL_MARKETS[:5]]
    assert overs == sorted(overs, reverse=True)
    if model.name == "dixon_coles":
        matrix = np.asarray(result.diagnostics["score_matrix"])
        assert matrix.min() >= 0
        assert matrix.sum() + result.diagnostics["residual_tail"] == pytest.approx(1)
        assert sum(result.diagnostics["total_distribution"]) == pytest.approx(1)


def test_dataset_does_not_use_target_result_or_future_games(tmp_path):
    db = Database(":memory:")
    db.execute(SCHEMA)
    rows = []
    for index in range(20):
        day = (datetime(2020, 1, 1) + timedelta(days=7 * index)).date().isoformat()
        row = FootballDataProvider.parse(
            f"Date,HomeTeam,AwayTeam,FTHG,FTAG,HC,AC\n{datetime.fromisoformat(day):%d/%m/%Y},A,B,{index % 3},1,5,4\n",
            "E0",
            "1920",
        )[0]
        rows.append(row)
        db.execute(
            "INSERT INTO historical_matches VALUES (?,?,?,?,?,?)",
            [row["match_key"], "E0", day, "football_data", datetime.now(UTC), encode(row)],
        )
    build_dataset(db, tmp_path / "before.npz")
    target = rows[-1]
    target["home_goals"] = 12
    target["home_corners"] = 19
    db.execute(
        "UPDATE historical_matches SET payload=? WHERE match_key=?",
        [encode(target), target["match_key"]],
    )
    build_dataset(db, tmp_path / "after.npz")
    with np.load(tmp_path / "before.npz") as before, np.load(tmp_path / "after.npz") as after:
        assert np.allclose(before["x"], after["x"], equal_nan=True)
        assert np.allclose(before["baseline"], after["baseline"], equal_nan=True)
        assert not np.array_equal(before["y"][-1], after["y"][-1])
    db.close()


async def test_daily_refresh_recovers_once_and_does_not_repeat(tmp_path):
    from zoneinfo import ZoneInfo

    db = Database(":memory:")
    service = LearningService(db, tmp_path / "models")
    service.start = Mock()
    now = datetime(2026, 9, 13, 12, tzinfo=UTC)
    service.daily_tick(now, ZoneInfo("Europe/Madrid"))
    service.start.assert_called_once()
    db.execute(
        "INSERT INTO settings VALUES ('learning_update',?)",
        [encode({"timestamp": now.isoformat()})],
    )
    service.daily_tick(now + timedelta(hours=1), ZoneInfo("Europe/Madrid"))
    service.start.assert_called_once()
    await service.close()
    db.close()


async def test_inference_abstains_without_artifacts_and_outside_training_coverage(tmp_path):
    db = Database(":memory:")
    service = LearningService(db, tmp_path)
    assert service.predict(features())["status"] == "unavailable"
    run_id = "a" * 32
    (tmp_path / run_id).mkdir()
    (tmp_path / "current.json").write_text(json.dumps({"run_id": run_id}))
    (tmp_path / run_id / "report.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "created_at": datetime.now(UTC).isoformat(),
                "config": {"leagues": ["E0"]},
            }
        )
    )
    assert "cobertura" in service.predict(features())["reason"]
    await service.close()
    db.close()


async def test_inference_cache_isolated_by_league_inputs_and_model_age(tmp_path, monkeypatch):
    db = Database(":memory:")
    service = LearningService(db, tmp_path)
    report = {
        "run_id": "a" * 32,
        "created_at": datetime.now(UTC).isoformat(),
        "config": {"leagues": ["SP1", "E0"]},
        "models": {"fake": {"temperatures": {}}},
        "champions": {},
        "league_statistics": {"140": {"goals": {"family": "poisson"}}},
    }
    monkeypatch.setattr(service, "report", lambda: report)
    raw = np.ones(8, np.float32)
    monkeypatch.setattr("app.learning.service.vectorize", lambda _: raw)
    monkeypatch.setattr("app.learning.service.sequences", lambda _: np.ones((10, 4), np.float32))
    service.loaded_id = report["run_id"]
    service.prep = Preprocessor().fit(raw[None, :])
    service.seq_prep = Preprocessor().fit(np.ones((10, 4), np.float32))
    model = Mock()
    model.predict.return_value = {
        head: np.full((1, size), 1 / size) for head, size in HEADS.items()
    }
    service.loaded = {"fake": model}
    f = features()
    first = service.predict(f)
    first["models"]["fake"]["BTTS_YES"] = -1
    assert service.predict(f)["models"]["fake"]["BTTS_YES"] > 0
    assert model.predict.call_count == 1
    f.fixture = f.fixture.model_copy(update={"league_id": 39})
    assert service.predict(f)["statistical_selection"] == {}
    assert model.predict.call_count == 2
    raw[0] = 2
    service.predict(f)
    assert model.predict.call_count == 3
    report["created_at"] = (datetime.now(UTC) - timedelta(days=100)).isoformat()
    assert service.predict(f)["status"] == "unavailable"
    assert model.predict.call_count == 3
    await service.close()
    db.close()


async def test_model_review_detects_expiration_and_new_rows_without_revision(tmp_path):
    db = Database(":memory:")
    service = LearningService(db, tmp_path)
    now = datetime.now(UTC)
    assert service.training_due(None, 2000, None, now)
    report = {
        "created_at": (now - timedelta(days=2)).isoformat(),
        "dataset": {"historical_matches": 2000},
    }
    assert not service.training_due(report, 2000, None, now)
    assert service.training_due(report, 2001, None, now)
    report["created_at"] = (now - timedelta(days=100)).isoformat()
    assert service.training_due(report, 2000, None, now)
    await service.close()
    db.close()
