import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from app.core.config import read_config
from app.db.connection import Database, encode
from app.jobs.progress import JobProgress
from app.learning.dataset import build_dataset, chronological_split
from app.learning.evaluation import calibrate, evaluate, market_probabilities, paired_improvement
from app.learning.features import Preprocessor
from app.learning.league_selection import learned_selection, statistical_selection
from app.learning.provenance import provenance
from app.learning.trees import TreeModels

FAMILIES = ("catboost", "lightgbm", "xgboost", "mlp", "gru")
TRAINING_PHASES = (
    [("dataset", "Preparar muestras y dividir periodos")]
    + [(family, f"Entrenar {family.upper()}") for family in FAMILIES]
    + [("evaluation", "Evaluar y comparar modelos"), ("publish", "Guardar modelos y reporte")]
)


def train(
    db: Database, directory: Path, config: dict, progress=print, tracker: JobProgress | None = None
) -> dict:
    from app.learning.deep import DeepModel

    run_id = uuid.uuid4().hex
    run_dir = directory / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    tracker = tracker or JobProgress({}, TRAINING_PHASES)
    tracker.start("dataset")
    metadata = build_dataset(
        db, run_dir / "dataset.npz", config["embargo_days"], progress, tracker.update
    )
    if metadata["rows"] < config["minimum_samples"]:
        raise ValueError(f"Muestra insuficiente: {metadata['rows']} / {config['minimum_samples']}")
    with np.load(run_dir / "dataset.npz", allow_pickle=False) as data:
        x, sequence, y, dates, baseline = [
            data[key] for key in ("x", "sequences", "y", "dates", "baseline")
        ]
        leagues = data["leagues"] if "leagues" in data else None
        statistical = data["statistical"] if "statistical" in data else None
    split = chronological_split(
        dates,
        config["train_fraction"],
        config["validation_fraction"],
        config["calibration_fraction"],
        config["embargo_days"],
    )
    if min(len(indices) for indices in split.values()) < 100:
        raise ValueError("Cada bloque temporal necesita al menos 100 partidos")
    league_statistics = {}
    if leagues is not None and statistical is not None:
        baseline, league_statistics = statistical_selection(
            statistical,
            baseline,
            y,
            dates,
            leagues,
            metadata["statistical_names"],
            split,
            config["seed"],
        )
    prep, seq_prep = (
        Preprocessor().fit(x[split["train"]]),
        Preprocessor().fit(sequence[split["train"]]),
    )
    x, sequence = prep.transform(x), seq_prep.transform(sequence)
    (run_dir / "preprocessor.json").write_text(
        encode({"static": prep.state(), "sequence": seq_prep.state()}), encoding="utf-8"
    )
    candidates, validation_scores, test_probabilities = {}, {}, {}
    validation_probabilities = {}
    it, iv, ic, ie = [split[key] for key in ("train", "validation", "calibration", "test")]
    tracker.end()
    for family in FAMILIES:
        tracker.start(family, 3, "Entrenamiento, calibración y guardado")

        def fitting(done, total, detail):
            tracker.update(done / max(1, total), 3, detail)

        progress(f"Entrenando {family.upper()} con {len(it)} partidos; validación: {len(iv)}")
        try:
            if family in ("mlp", "gru"):
                model = DeepModel(family, x.shape[-1], sequence.shape[-1], config)
                model.fit(x[it], sequence[it], y[it], x[iv], sequence[iv], y[iv], fitting)
            else:
                model = TreeModels(family, config).fit(x[it], y[it], x[iv], y[iv], fitting)
            tracker.update(1, 3, f"{family.upper()} · validación y calibración")
            validation_p = market_probabilities(model.predict(x[iv], sequence[iv]))
            validation = evaluate(validation_p, y[iv])
            temperatures = calibrate(model.predict(x[ic], sequence[ic]), y[ic])
            probabilities = market_probabilities(model.predict(x[ie], sequence[ie]), temperatures)
            tracker.update(2, 3, f"{family.upper()} · guardando y verificando el modelo")
            model.save(run_dir / family)
            # Native-format round trip must preserve inference before publishing artifacts.
            restored = (
                DeepModel.load(family, run_dir / family)
                if family in ("mlp", "gru")
                else TreeModels.load(family, run_dir / family)
            )
            reloaded = market_probabilities(
                restored.predict(x[ie[:3]], sequence[ie[:3]]), temperatures
            )
            for market in reloaded:
                if not np.allclose(reloaded[market], probabilities[market][:3], atol=1e-5):
                    raise ValueError(f"Inferencia no reproducible al recargar {family}")
            candidates[family] = {
                "status": "trained",
                "validation": validation,
                "test": evaluate(probabilities, y[ie]),
                "temperatures": temperatures,
                "epochs": getattr(model, "epochs", None),
            }
            validation_scores[family] = validation
            validation_probabilities[family] = validation_p
            test_probabilities[family] = probabilities
            tracker.end()
        except Exception as exc:
            candidates[family] = {
                "status": "failed",
                "error": f"{type(exc).__name__}: {str(exc)[:240]}",
            }
            progress(f"{family}: {candidates[family]['error']}")
            tracker.end(f"{family.upper()}: {candidates[family]['error']}")
    tracker.start("evaluation", 2, "Comparando goles y córners con la referencia")
    base = {market: baseline[ie, index] for index, market in enumerate(metadata["markets"])}
    champions = {}
    for group in ("goals", "corners"):
        eligible = [
            name for name, metrics in validation_scores.items() if metrics[group] is not None
        ]
        if not eligible:
            continue
        # Winner chosen on validation; the final test is never used to choose a family.
        selected = min(eligible, key=lambda name: validation_scores[name][group])
        weight = float(config["learned_blend_weight"])
        blended = {
            market: (1 - weight) * base[market] + weight * p
            for market, p in test_probabilities[selected].items()
        }
        gate = paired_improvement(blended, base, y[ie], group, config["seed"], dates=dates[ie])
        champions[group] = {
            "family": selected,
            "blend_weight": weight,
            "gate": gate,
            "blended_test": evaluate(blended, y[ie])[group],
            "selection": "lowest validation Brier before calibration",
        }
        tracker.update(len(champions), 2, f"Comparación de {group} completada")
    if not validation_scores:
        raise RuntimeError("Ninguna familia pudo entrenarse: " + encode(candidates))
    league_champions = (
        learned_selection(
            validation_probabilities,
            test_probabilities,
            base,
            y,
            dates,
            leagues,
            split,
            float(config["learned_blend_weight"]),
            config["seed"],
        )
        if leagues is not None
        else {}
    )
    tracker.end()
    tracker.start("publish", detail="Guardando el reporte y publicando la versión")
    now = datetime.now(UTC)
    report = {
        "run_id": run_id,
        "created_at": now.isoformat(),
        "status": "complete",
        "duration_seconds": round(time.monotonic() - started, 1),
        "dataset": metadata,
        "config": config,
        "statistical_weights": read_config("model_weights"),
        "feature_schema_version": 1,
        "provenance": provenance(),
        "splits": {
            key: {
                "samples": len(indices),
                "from": datetime.fromtimestamp(int(dates[indices[0]]), UTC).isoformat(),
                "to": datetime.fromtimestamp(int(dates[indices[-1]]), UTC).isoformat(),
            }
            for key, indices in split.items()
        },
        "baseline": evaluate(base, y[ie]),
        "models": candidates,
        "champions": champions,
        "league_statistics": league_statistics,
        "league_champions": league_champions,
        "limitations": [
            "Histórico retrospectivo; publicación de estadísticas aproximada con embargo de 48 horas.",
            "El test es temporal y posterior al entrenamiento; no equivale a resultados prospectivos en vivo.",
            "La selección se hace en validación y la promoción usa el test. Su evidencia pierde independencia al reutilizar periodos en reentrenamientos.",
            "La comparación mide probabilidades, no rentabilidad ni garantía de acierto.",
            "Selección estadística por liga en validación y promoción en calibración; muestra mínima 150 y 20 semanas. El test posterior evalúa esa política.",
            "Selección ML por liga en validación; promoción del blend con al menos 300 partidos y 20 semanas de test. Intervalos ajustados por número de ligas y grupos; no existe un mejor modelo universal.",
        ],
    }
    (run_dir / "report.json").write_text(encode(report), encoding="utf-8")
    temporary = directory / "current.tmp"
    temporary.write_text(encode({"run_id": run_id}), encoding="utf-8")
    temporary.replace(directory / "current.json")
    db.execute(
        "INSERT INTO learning_runs VALUES (?,?,?,?,?)",
        [run_id, now, "complete", metadata["rows"], encode(report)],
    )
    progress(f"Entrenamiento terminado: {run_id} ({report['duration_seconds']} s)")
    tracker.end()
    return report
