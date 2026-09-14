import numpy as np

from app.domain.market import Market
from app.learning.evaluation import targets
from app.learning.league_selection import learned_selection, statistical_selection


def scenario(n):
    labels = np.tile([3, 1, 10], (n, 1))
    truth = np.column_stack([targets(labels, m)[0] for m in Market])
    probabilities = 0.1 + 0.8 * truth
    return labels, probabilities, np.full(probabilities.shape, 0.5), np.arange(n) * 86400


def test_statistics_are_selected_before_test_and_missing_leagues_keep_reference():
    labels, p, base, dates = scenario(450)
    split = {
        "validation": np.arange(150),
        "calibration": np.arange(150, 300),
        "test": np.arange(300, 450),
    }
    candidate = np.stack([p, 1 - p], axis=1)
    leagues = np.full(450, 140)
    adjusted, report = statistical_selection(
        candidate, base, labels, dates, leagues, ["goals:poisson", "goals:dixon_coles"], split
    )
    assert report["140"]["goals"]["family"] == "poisson"
    assert report["140"]["goals"]["gate"]["promoted"]
    altered = labels.copy()
    altered[split["test"], 0] = 0
    _, new_report = statistical_selection(
        candidate, base, altered, dates, leagues, ["goals:poisson", "goals:dixon_coles"], split
    )
    assert new_report["140"]["goals"]["gate"] == report["140"]["goals"]["gate"]
    assert not report["140"]["corners"]["gate"]["promoted"]
    np.testing.assert_array_equal(adjusted[:, :7], p[:, :7])
    np.testing.assert_array_equal(adjusted[:, 7:], base[:, 7:])
    small = {k: v[:30] for k, v in split.items()}
    unchanged, sparse = statistical_selection(
        candidate, base, labels, dates, leagues, ["goals:poisson", "goals:dixon_coles"], small
    )
    assert not sparse["140"]["goals"]["gate"]["promoted"]
    np.testing.assert_array_equal(unchanged, base)


def test_learned_family_is_not_chosen_using_test_outcomes():
    labels, p, base, dates = scenario(500)
    split = {"validation": np.arange(150), "test": np.arange(150, 500)}

    def as_dict(values):
        return {m.value: values[:, i] for i, m in enumerate(Market)}

    validation = {"mlp": as_dict(p[:150]), "gru": as_dict(1 - p[:150])}
    test = {"mlp": as_dict(1 - p[150:]), "gru": as_dict(p[150:])}
    report = learned_selection(
        validation, test, as_dict(base[150:]), labels, dates, np.full(500, 140), split, 0.2
    )
    assert report["140"]["goals"]["family"] == "mlp"
    assert not report["140"]["goals"]["gate"]["promoted"]
