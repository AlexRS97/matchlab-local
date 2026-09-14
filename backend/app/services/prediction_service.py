import hashlib
import json
from datetime import UTC, datetime

from app.core.config import read_config
from app.domain.fixture import Fixture
from app.domain.prediction import ModelOutput
from app.models.corners.ensemble import CornerEnsemble
from app.models.ensemble import combine
from app.models.goals.ensemble import GoalEnsemble
from app.repositories.cache import CacheRepository
from app.repositories.predictions_repository import PredictionsRepository
from app.repositories.stats_repository import StatsRepository
from app.services.data_quality_service import DataQualityService, confidence
from app.services.features import build_features, feature_summary


class PredictionService:
    def __init__(self, stats: StatsRepository, repository: PredictionsRepository, learning=None):
        self.stats, self.repository = stats, repository
        self.learning = learning
        self.weights = read_config("model_weights")
        self.goals = GoalEnsemble(self.weights["goals"])
        self.corners = CornerEnsemble(self.weights["corners"])
        self.quality = DataQualityService()

    def calculate(
        self, fixture: Fixture, now: datetime | None = None, force: bool = False
    ) -> dict | None:
        now = now or datetime.now(UTC)
        if not fixture.prematch(now):
            return self.repository.latest(fixture.fixture_id, before=fixture.kickoff_utc)
        f = build_features(
            fixture,
            self.stats.matches(fixture.home_team_id, fixture.kickoff_utc),
            self.stats.matches(fixture.away_team_id, fixture.kickoff_utc),
            self.stats.league_matches(fixture.league_id, fixture.kickoff_utc),
            self.stats.standings(fixture.league_id, fixture.season, fixture.kickoff_utc),
        )
        f.h2h = self.stats.h2h(fixture.home_team_id, fixture.away_team_id, fixture.kickoff_utc)
        external = CacheRepository(self.stats.db).get(f"external:{fixture.fixture_id}", stale=True)
        if external and external["updated_at"] < fixture.kickoff_utc:
            f.external = external["data"]
        summary = feature_summary(f)
        summary["external"] = f.external
        quality = self.quality.evaluate(f, now=now)
        learned: dict = {"status": "unavailable", "models": {}}
        if self.learning:
            try:
                learned = self.learning.predict(f)
            except Exception as exc:
                learned["reason"] = f"Inferencia no disponible: {type(exc).__name__}"
        fingerprint = hashlib.sha256(
            json.dumps(
                [summary, self.weights, quality, learned.get("run_id"), learned.get("status")],
                sort_keys=True,
            ).encode()
        ).hexdigest()
        existing = self.repository.latest(fixture.fixture_id)
        if not force and existing and existing.get("fingerprint") == fingerprint:
            return existing
        goals = self.goals.predict(f)
        corners = self.corners.predict(f)
        selected_statistics = learned.get("statistical_selection", {})
        ensembles = {}
        for group, ensemble in (("goals", goals), ("corners", corners)):
            selection = selected_statistics.get(group, {})
            if selection.get("gate", {}).get("promoted"):
                selected_model = next(
                    (m for m in ensemble.models if m.name == selection["family"]), None
                )
                if (
                    selected_model
                    and selected_model.status == "available"
                    and all(m in selected_model.probabilities for m in ensemble.probabilities)
                ):
                    ensemble = combine(ensemble.models, {selected_model.name: 1.0})
                else:
                    learned["champions"] = {
                        **learned.get("champions", {}),
                        group: {
                            "gate": {"promoted": False},
                            "reason": "La referencia estadística evaluada no está disponible",
                        },
                    }
            ensembles[group] = ensemble
        goals, corners = ensembles["goals"], ensembles["corners"]
        statistical = {"goals": dict(goals.probabilities), "corners": dict(corners.probabilities)}
        for group, ensemble in (("goals", goals), ("corners", corners)):
            champion = learned.get("champions", {}).get(group, {})
            if not champion.get("gate", {}).get("promoted"):
                continue
            family = champion["family"]
            probabilities = {
                m: p
                for m, p in learned["models"].get(family, {}).items()
                if m in ensemble.probabilities
            }
            if not probabilities:
                continue
            weight = min(0.2, float(champion["blend_weight"]))
            name = f"learned_{family}"
            ensemble.models.append(
                ModelOutput(
                    name=name,
                    probabilities=probabilities,
                    diagnostics={"run_id": learned["run_id"], "gate": champion["gate"]},
                )
            )
            for market, p in probabilities.items():
                ensemble.probabilities[market] = (1 - weight) * ensemble.probabilities[
                    market
                ] + weight * p
                ensemble.weights[market] = {
                    **{
                        key: value * (1 - weight) for key, value in ensemble.weights[market].items()
                    },
                    name: weight,
                }
                import numpy as np

                values = [
                    m.probabilities[market]
                    for m in ensemble.models
                    if m.name in ensemble.weights[market]
                ]
                std = float(np.std(values))
                ensemble.consensus[market] = {
                    "model_mean": float(np.mean(values)),
                    "model_std": std,
                    "model_min": min(values),
                    "model_max": max(values),
                    "model_count": len(values),
                    "model_disagreement": "LOW"
                    if std <= 0.06
                    else "MEDIUM"
                    if std <= 0.12
                    else "HIGH",
                }
        corner_quality = self.quality.evaluate(f, corners=True, now=now)
        if corner_quality["sample_size"] < 5:
            corners.probabilities = {}
            corners.expected_home = corners.expected_away = corners.expected_total = None
        if quality["sample_size"] < 5:
            goals.probabilities = {}
            goals.expected_home = goals.expected_away = goals.expected_total = None
        output = {
            "fixture_id": fixture.fixture_id,
            "timestamp": now.isoformat(),
            "fingerprint": fingerprint,
            "version": "hybrid-v3-leagues",
            "learning": learned,
            "statistical_probabilities": statistical,
            "features": summary,
            "goals": goals.model_dump(mode="json"),
            "quality": quality,
            "confidence": {m: confidence(quality, goals, m) for m in goals.probabilities},
            "corners": corners.model_dump(mode="json"),
            "corner_quality": corner_quality,
        }
        output["confidence"].update(
            {m: confidence(corner_quality, corners, m) for m in corners.probabilities}
        )
        self.repository.save(fixture.fixture_id, now, output)
        return output
