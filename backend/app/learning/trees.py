import json
from pathlib import Path

import numpy as np

from app.core.resources import resolve_threads
from app.learning.dataset import HEADS


class TreeModels:
    def __init__(self, family: str, config: dict):
        self.family, self.config = (
            family,
            {**config, "threads": resolve_threads(config.get("threads"))},
        )
        self.models: dict = {}
        self.classes: dict = {}

    def fit(self, x, y, xv, yv, on_progress=None):
        for index, (head, _size) in enumerate(HEADS.items()):
            if on_progress:
                on_progress(
                    index,
                    len(HEADS),
                    f"{self.family.upper()} · objetivo {head} ({index + 1}/{len(HEADS)})",
                )
            valid = y[:, index] >= 0
            classes = np.unique(y[valid, index])
            if valid.sum() < 200 or len(classes) < 2:
                continue
            val = np.isin(yv[:, index], classes)
            target = np.searchsorted(classes, y[valid, index])
            validation = np.searchsorted(classes, yv[val, index])
            seed, threads, trees = self.config["seed"], self.config["threads"], self.config["trees"]
            if self.family == "catboost":
                from catboost import CatBoostClassifier

                model = CatBoostClassifier(
                    iterations=trees,
                    depth=5,
                    learning_rate=0.04,
                    l2_leaf_reg=8,
                    loss_function="MultiClass",
                    random_seed=seed,
                    thread_count=threads,
                    verbose=False,
                    allow_writing_files=False,
                    has_time=True,
                )
                model.fit(
                    x[valid],
                    target,
                    eval_set=(xv[val], validation),
                    early_stopping_rounds=25,
                    verbose=False,
                )
            elif self.family == "lightgbm":
                from lightgbm import LGBMClassifier, early_stopping

                model = LGBMClassifier(
                    n_estimators=trees,
                    num_leaves=15,
                    max_depth=5,
                    learning_rate=0.035,
                    min_child_samples=40,
                    reg_lambda=8,
                    verbosity=-1,
                    n_jobs=threads,
                    random_state=seed,
                    deterministic=True,
                    force_col_wise=True,
                )
                model.fit(
                    x[valid],
                    target,
                    eval_set=[(xv[val], validation)],
                    callbacks=[early_stopping(25, verbose=False)],
                )
            elif self.family == "xgboost":
                from xgboost import XGBClassifier

                model = XGBClassifier(
                    n_estimators=trees,
                    max_depth=4,
                    learning_rate=0.035,
                    min_child_weight=10,
                    reg_lambda=8,
                    subsample=0.85,
                    colsample_bytree=0.85,
                    tree_method="hist",
                    n_jobs=threads,
                    random_state=seed,
                    early_stopping_rounds=25,
                    eval_metric="mlogloss" if len(classes) > 2 else "logloss",
                )
                model.fit(x[valid], target, eval_set=[(xv[val], validation)], verbose=False)
            else:
                raise ValueError("Familia de árboles no reconocida")
            self.models[head], self.classes[head] = model, classes.tolist()
            if on_progress:
                on_progress(index + 1, len(HEADS), f"{self.family.upper()} · {head} entrenado")
        return self

    def predict(self, x, sequence=None):
        outputs = {}
        for head, model in self.models.items():
            raw = np.asarray(
                model.predict_proba(x, thread_count=self.config["threads"])
                if self.family == "catboost"
                else model.predict_proba(x)
            )
            if raw.ndim == 1:
                raw = np.column_stack([1 - raw, raw])
            expanded = np.zeros((len(x), HEADS[head]), dtype=np.float64)
            expanded[:, self.classes[head]] = raw
            outputs[head] = expanded
        return outputs

    def save(self, directory: Path):
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "classes.json").write_text(json.dumps(self.classes), encoding="utf-8")
        for head, model in self.models.items():
            if self.family == "lightgbm":
                model.booster_.save_model(str(directory / f"{head}.txt"))
            else:
                model.save_model(
                    str(directory / f"{head}.{'json' if self.family == 'xgboost' else 'cbm'}")
                )

    @classmethod
    def load(cls, family: str, directory: Path):
        result = cls(family, {})
        result.classes = json.loads((directory / "classes.json").read_text(encoding="utf-8"))
        for head in result.classes:
            if family == "catboost":
                from catboost import CatBoostClassifier

                model = CatBoostClassifier(thread_count=result.config["threads"])
                model.load_model(str(directory / f"{head}.cbm"))
            elif family == "xgboost":
                from xgboost import XGBClassifier

                model = XGBClassifier()
                model.load_model(str(directory / f"{head}.json"))
                model.set_params(n_jobs=result.config["threads"])
            else:
                import lightgbm as lgb

                model = BoosterProbabilities(lgb.Booster(model_file=str(directory / f"{head}.txt")))
            result.models[head] = model
        return result


class BoosterProbabilities:
    def __init__(self, booster):
        self.booster = booster

    def predict_proba(self, x):
        raw = self.booster.predict(x, num_threads=resolve_threads())
        return np.column_stack([1 - raw, raw]) if raw.ndim == 1 else raw
