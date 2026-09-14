import numpy as np
from scipy.optimize import minimize_scalar
from scipy.special import softmax

from app.domain.market import Market
from app.learning.dataset import HEADS
from app.learning.diagnostics import calibration_diagnostic


def temperature_scale(probabilities: np.ndarray, temperature: float) -> np.ndarray:
    return softmax(np.log(np.clip(probabilities, 1e-9, 1)) / temperature, axis=1)


def calibrate(outputs: dict, labels: np.ndarray) -> dict[str, float]:
    temperatures = {}
    for index, head in enumerate(HEADS):
        valid = labels[:, index] >= 0
        if head not in outputs or valid.sum() < 100:
            continue
        probabilities, target = outputs[head][valid], labels[valid, index]

        def loss(temperature, probabilities=probabilities, target=target):
            scaled = temperature_scale(probabilities, temperature)
            return float(-np.log(np.clip(scaled[np.arange(len(target)), target], 1e-9, 1)).mean())

        fit = minimize_scalar(loss, bounds=(0.5, 5), method="bounded")
        temperatures[head] = float(fit.x) if fit.success else 1.0
    return temperatures


def market_probabilities(outputs: dict, temperatures: dict | None = None) -> dict[str, np.ndarray]:
    temperatures = temperatures or {}
    result = {}
    for head, probabilities in outputs.items():
        p = temperature_scale(probabilities, temperatures.get(head, 1))
        if head == "btts":
            result["BTTS_YES"], result["BTTS_NO"] = p[:, 1], p[:, 0]
        else:
            for market in Market:
                if (head == "corners" and market.value.endswith("CORNERS")) or (
                    head == "goals" and market.value.endswith("GOALS")
                ):
                    result[market.value] = p[:, int(market.line or 0) + 1 :].sum(axis=1)
    if "BTTS_YES" in result and "OVER_1_5_GOALS" in result:
        result["BTTS_YES"] = np.minimum(result["BTTS_YES"], result["OVER_1_5_GOALS"])
        result["BTTS_NO"] = 1 - result["BTTS_YES"]
    return result


def targets(labels: np.ndarray, market: Market) -> tuple[np.ndarray, np.ndarray]:
    index = 2 if market.value.endswith("CORNERS") else 1 if market.value.startswith("BTTS") else 0
    observed = labels[:, index]
    y = (
        (observed == (1 if market == Market.BTTS_YES else 0))
        if index == 1
        else observed > (market.line or 0)
    )
    return y.astype(float), observed >= 0


def evaluate(probabilities: dict, labels: np.ndarray) -> dict:
    metrics = {}
    for market in Market:
        if market.value not in probabilities:
            continue
        y, valid = targets(labels, market)
        p = np.asarray(probabilities[market.value])
        valid &= np.isfinite(p)
        y, p = y[valid], np.clip(p[valid], 1e-7, 1 - 1e-7)
        if not len(y):
            continue
        ece = 0.0
        for lower in np.arange(0, 1, 0.1):
            selected = (p >= lower) & (p < lower + 0.1)
            if selected.any():
                ece += selected.mean() * abs(p[selected].mean() - y[selected].mean())
        metrics[market.value] = {
            **calibration_diagnostic(y, p),
            "samples": len(y),
            "brier": float(np.mean((p - y) ** 2)),
            "log_loss": float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))),
            "ece": float(ece),
            "mean_probability": float(p.mean()),
            "observed_rate": float(y.mean()),
        }
    return {
        "markets": metrics,
        **{
            group: float(
                np.mean(
                    [
                        v["brier"]
                        for k, v in metrics.items()
                        if (k.endswith("CORNERS")) == (group == "corners") and k != "BTTS_NO"
                    ]
                )
            )
            if any(k.endswith("CORNERS") == (group == "corners") for k in metrics)
            else None
            for group in ("goals", "corners")
        },
    }


def paired_improvement(
    candidate: dict,
    baseline: dict,
    labels: np.ndarray,
    group: str,
    seed=42,
    dates=None,
    minimum_samples=300,
    confidence_level=0.95,
) -> dict:
    differences = []
    blocks = []
    for index in range(len(labels)):
        row = []
        for market in Market:
            if (
                market == Market.BTTS_NO
                or market.value.endswith("CORNERS") != (group == "corners")
                or market.value not in candidate
            ):
                continue
            y, valid = targets(labels[index : index + 1], market)
            p, b = candidate[market.value][index], baseline[market.value][index]
            if valid[0] and np.isfinite(b) and np.isfinite(p):
                row.append((b - y[0]) ** 2 - (p - y[0]) ** 2)
        if row:
            differences.append(float(np.mean(row)))
            blocks.append(int(dates[index]) // (7 * 86400) if dates is not None else index)
    if not differences:
        return {"mean": 0, "ci_lower": 0, "ci_upper": 0, "samples": 0, "promoted": False}
    values = np.asarray(differences)
    rng = np.random.default_rng(seed)
    # Resample whole calendar weeks, retaining dependence between matches in a round.
    block_ids = np.asarray(blocks)
    unique_blocks = np.unique(block_ids)
    sums = np.asarray([values[block_ids == block].sum() for block in unique_blocks])
    counts = np.asarray([(block_ids == block).sum() for block in unique_blocks])
    draws = rng.integers(0, len(sums), size=(1000, len(sums)))
    means = sums[draws].sum(axis=1) / counts[draws].sum(axis=1)
    alpha = (1 - confidence_level) / 2
    lower, upper = np.quantile(means, [alpha, 1 - alpha])
    return {
        "mean": float(values.mean()),
        "ci_lower": float(lower),
        "ci_upper": float(upper),
        "samples": len(values),
        "blocks": len(unique_blocks),
        "method": "weekly_block_bootstrap" if dates is not None else "fixture_bootstrap",
        "confidence_level": confidence_level,
        "promoted": bool(lower > 0 and len(values) >= minimum_samples and len(unique_blocks) >= 20),
    }
