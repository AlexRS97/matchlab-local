import math

import numpy as np

from app.domain.prediction import EnsembleOutput, ModelOutput


def combine(models: list[ModelOutput], configured_weights: dict[str, float]) -> EnsembleOutput:
    if any(not math.isfinite(weight) or weight < 0 for weight in configured_weights.values()):
        raise ValueError("Los pesos deben ser finitos y no negativos")
    result = EnsembleOutput(models=models)
    markets = {
        key for model in models if model.status == "available" for key in model.probabilities
    }
    for market in markets:
        active = [
            model
            for model in models
            if model.status == "available"
            and market in model.probabilities
            and configured_weights.get(model.name, 0) > 0
            and 0 <= model.probabilities[market] <= 1
        ]
        total = sum(configured_weights[model.name] for model in active)
        if not total:
            continue
        weights = {model.name: configured_weights[model.name] / total for model in active}
        probabilities = [model.probabilities[market] for model in active]
        std = float(np.std(probabilities))
        result.probabilities[market] = sum(
            model.probabilities[market] * weights[model.name] for model in active
        )
        result.weights[market] = weights
        result.consensus[market] = {
            "model_mean": float(np.mean(probabilities)),
            "model_std": std,
            "model_min": min(probabilities),
            "model_max": max(probabilities),
            "model_count": len(active),
            "model_disagreement": "LOW" if std <= 0.06 else "MEDIUM" if std <= 0.12 else "HIGH",
        }
    expected = [
        m
        for m in models
        if m.status == "available"
        and m.expected_home is not None
        and m.expected_away is not None
        and configured_weights.get(m.name, 0) > 0
    ]
    weight_sum = sum(configured_weights[m.name] for m in expected)
    if weight_sum:
        result.expected_home = (
            sum((m.expected_home or 0) * configured_weights[m.name] for m in expected) / weight_sum
        )
        result.expected_away = (
            sum((m.expected_away or 0) * configured_weights[m.name] for m in expected) / weight_sum
        )
        result.expected_total = result.expected_home + result.expected_away
    return result
