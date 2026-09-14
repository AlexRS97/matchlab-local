import pytest
from scipy.stats import nbinom
from test_models import features

from app.models.corners.common import output
from app.models.corners.ensemble import CornerEnsemble
from app.models.corners.negative_binomial import CornerNegativeBinomialModel
from app.services.analysis_service import AnalysisGenerator


def test_corners_negative_binomial_tail_and_poisson_fallback():
    result = output("negative_binomial", 5, 5, variance=20)
    assert result.probabilities["OVER_9_5_CORNERS"] == pytest.approx(nbinom.sf(9, 10, 0.5))
    assert output("negative_binomial", 5, 5, variance=8).diagnostics["distribution"] == "poisson"


def test_corners_models_and_missing_stats():
    f = features()
    ensemble = CornerEnsemble(
        {"negative_binomial": 0.35, "poisson": 0.2, "recent_form": 0.25, "home_away": 0.2}
    ).predict(f)
    probs = [ensemble.probabilities[f"OVER_{n}_5_CORNERS"] for n in range(7, 12)]
    assert probs == sorted(probs, reverse=True)
    assert all(0 < p < 1 for p in probs)
    for obs in f.home:
        obs.corners_for = None
    assert CornerNegativeBinomialModel().predict(f).status == "unavailable"


def test_analysis_without_data_is_explicit():
    result = AnalysisGenerator().generate(None)
    assert "suficientes datos" in result["paragraphs"][0]
    assert "%" not in result["paragraphs"][0]
