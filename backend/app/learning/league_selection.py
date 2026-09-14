"""Select on validation, qualify statistical changes on calibration, evaluate on later test."""

import numpy as np

from app.domain.market import Market
from app.learning.evaluation import evaluate, paired_improvement, targets


def group_markets(group):
    return [m for m in Market if m.value.endswith("CORNERS") == (group == "corners")]


def complete_sample(probabilities, labels, group):
    mask = np.ones(len(labels), dtype=bool)
    for market in group_markets(group):
        if market.value not in probabilities:
            return np.zeros(len(labels), dtype=bool)
        _, valid = targets(labels, market)
        mask &= valid & np.isfinite(probabilities[market.value])
    return mask


def statistical_selection(statistical, baseline, labels, dates, leagues, names, split, seed=42):
    adjusted = baseline.copy()
    report = {}
    markets = list(Market)
    confidence = 1 - 0.05 / max(1, 2 * len(np.unique(leagues)))
    for league in np.unique(leagues):
        entry = {}
        for group in ("goals", "corners"):
            iv, ic, ie = [
                indices[leagues[indices] == league]
                for indices in (split["validation"], split["calibration"], split["test"])
            ]
            columns = [i for i, m in enumerate(markets) if m in group_markets(group)]

            def probabilities(matrix, indices, columns=columns):
                return {markets[col].value: matrix[indices, col] for col in columns}

            base_validation = probabilities(baseline, iv)
            common = complete_sample(base_validation, labels[iv], group)
            eligible = []
            for index, name in enumerate(names):
                if not name.startswith(group + ":"):
                    continue
                p = probabilities(statistical[:, index], iv)
                valid = complete_sample(p, labels[iv], group)
                # Compare identical matches and every market, never a selectively available subset.
                if common.sum() >= 150 and valid[common].all():
                    score = evaluate({k: v[common] for k, v in p.items()}, labels[iv][common])[
                        group
                    ]
                    eligible.append((score, index, name.split(":", 1)[1]))
            entry[group] = {
                "family": "ensemble",
                "gate": {"promoted": False},
                "validation_samples": int(common.sum()),
                "reason": "Sin mejora validada",
            }
            if not eligible:
                continue
            score, index, name = min(eligible)
            reference_score = evaluate(
                {k: v[common] for k, v in base_validation.items()}, labels[iv][common]
            )[group]
            if score >= reference_score:
                continue
            candidate = statistical[:, index]
            complete = complete_sample(probabilities(candidate, ic), labels[ic], group)
            complete &= complete_sample(probabilities(baseline, ic), labels[ic], group)
            ic = ic[complete]
            gate = paired_improvement(
                probabilities(candidate, ic),
                probabilities(baseline, ic),
                labels[ic],
                group,
                seed,
                dates[ic],
                minimum_samples=150,
                confidence_level=confidence,
            )
            entry[group].update(
                family=name,
                validation_brier=score,
                gate=gate,
                promotion_period="calibration",
                candidate_test=evaluate(probabilities(candidate, ie), labels[ie])[group],
            )
            if gate["promoted"]:
                for col in columns:
                    selected = (leagues == league) & np.isfinite(candidate[:, col])
                    adjusted[selected, col] = candidate[selected, col]
        report[str(league)] = entry
    return adjusted, report


def learned_selection(validation, test, baseline, labels, dates, leagues, split, weight, seed=42):
    report = {}
    iv, ie = split["validation"], split["test"]
    confidence = 1 - 0.05 / max(1, 2 * len(np.unique(leagues)))
    for league in np.unique(leagues):
        vm, tm = leagues[iv] == league, leagues[ie] == league
        entry = {}
        for group in ("goals", "corners"):
            candidates = []
            common = np.ones(int(vm.sum()), dtype=bool)
            for market in group_markets(group):
                _, valid_targets = targets(labels[iv][vm], market)
                common &= valid_targets
            for family, values in validation.items():
                p = {k: v[vm] for k, v in values.items()}
                valid = complete_sample(p, labels[iv][vm], group)
                if common.sum() >= 150 and valid[common].all():
                    candidates.append(
                        (
                            evaluate({k: v[common] for k, v in p.items()}, labels[iv][vm][common])[
                                group
                            ],
                            family,
                        )
                    )
            if not candidates:
                continue
            score, family = min(candidates)
            base = {k: v[tm] for k, v in baseline.items()}
            blended = {k: (1 - weight) * base[k] + weight * v[tm] for k, v in test[family].items()}
            gate = paired_improvement(
                blended,
                base,
                labels[ie][tm],
                group,
                seed,
                dates[ie][tm],
                confidence_level=confidence,
            )
            entry[group] = {
                "family": family,
                "blend_weight": weight,
                "gate": gate,
                "validation_brier": score,
                "blended_test": evaluate(blended, labels[ie][tm])[group],
                "selection": "league validation Brier before calibration",
            }
        report[str(league)] = entry
    return report
