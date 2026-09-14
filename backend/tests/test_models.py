from datetime import UTC, datetime, timedelta

import numpy as np
import pytest
from scipy.stats import poisson
from test_football import raw_fixture

from app.domain.fixture import MatchObservation
from app.domain.prediction import ModelOutput
from app.models.ensemble import combine
from app.models.goals.ensemble import GoalEnsemble
from app.models.goals.poisson import GoalPoissonModel
from app.models.goals.xg import GoalXGModel
from app.providers.api_football.normalization import normalize_fixture
from app.services.data_quality_service import DataQualityService, confidence
from app.services.features import build_features


def features(count=20):
    now = datetime.now(UTC)
    fixture = normalize_fixture(raw_fixture((now + timedelta(hours=5)).isoformat()), now)
    groups = []
    for team in (1, 2):
        groups.append(
            [
                MatchObservation(
                    fixture_id=100 * team + i,
                    team_id=team,
                    opponent_id=99,
                    kickoff_utc=now - timedelta(days=3 * i + 2),
                    completed_at=now - timedelta(days=3 * i + 1),
                    is_home=i % 2 == 0,
                    goals_for=i % 3 + 1,
                    goals_against=(i + 1) % 3,
                    league_id=140,
                    competition="La Liga",
                    observed_at=now,
                    corners_for=4 + i % 4,
                    corners_against=3 + i % 5,
                )
                for i in range(count)
            ]
        )
    return build_features(fixture, *groups, [], [])


def test_poisson_matrix_and_exact_tail():
    output = GoalPoissonModel().predict(features())
    assert np.sum(output.diagnostics["score_matrix"]) + output.diagnostics[
        "residual_tail"
    ] == pytest.approx(1)
    total = output.expected_home + output.expected_away
    for n in range(5):
        assert output.probabilities[f"OVER_{n}_5_GOALS"] == pytest.approx(poisson.sf(n, total))
    assert sum(output.diagnostics["total_distribution"]) == pytest.approx(1)


def test_missing_models_renormalize_per_market():
    models = [
        ModelOutput(name="a", probabilities={"m": 0.8}),
        ModelOutput(name="b", status="unavailable"),
        ModelOutput(name="c", probabilities={"m": 0.6, "x": 0.3}),
    ]
    result = combine(models, {"a": 0.3, "b": 0.5, "c": 0.2})
    assert result.probabilities["m"] == pytest.approx(0.72)
    assert result.probabilities["x"] == 0.3
    assert result.weights["m"] == {"a": 0.6, "c": 0.4}


def test_no_fake_xg_and_small_sample():
    f = features(3)
    assert GoalXGModel().predict(f).status == "unavailable"
    assert DataQualityService().evaluate(f)["category"] == "INSUFFICIENT"
    assert GoalPoissonModel().predict(f).status == "unavailable"


def test_target_and_future_observations_excluded():
    f = features()
    target = f.home[0].model_copy(update={"fixture_id": f.fixture.fixture_id})
    future = f.home[0].model_copy(
        update={"fixture_id": 999, "observed_at": f.fixture.kickoff_utc + timedelta(seconds=1)}
    )
    result = build_features(f.fixture, [target, future], f.away, [], [])
    assert result.home == []


def test_confidence_drops_with_disagreement():
    quality = {"score": 95, "sample_size": 20, "split_sample": 10}
    same = combine(
        [
            ModelOutput(name=str(i), probabilities={"m": p})
            for i, p in enumerate([0.72, 0.74, 0.73])
        ],
        {"0": 1, "1": 1, "2": 1},
    )
    apart = combine(
        [ModelOutput(name=str(i), probabilities={"m": p}) for i, p in enumerate([0.4, 0.8, 0.95])],
        {"0": 1, "1": 1, "2": 1},
    )
    assert confidence(quality, same, "m")["score"] > confidence(quality, apart, "m")["score"]
    assert confidence(quality, apart, "m")["category"] == "LOW"


def test_ensemble_has_all_goal_lines_and_monotonicity():
    result = GoalEnsemble(
        {"poisson": 0.3, "recent_form": 0.25, "home_away": 0.25, "xg": 0.15, "external": 0.05}
    ).predict(features())
    probabilities = [result.probabilities[f"OVER_{n}_5_GOALS"] for n in range(5)]
    assert probabilities == sorted(probabilities, reverse=True)
    assert result.probabilities["BTTS_YES"] + result.probabilities["BTTS_NO"] == pytest.approx(1)
