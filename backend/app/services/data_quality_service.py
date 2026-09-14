from datetime import UTC, datetime

from app.domain.prediction import EnsembleOutput
from app.services.features import Features

QUALITY_LEVELS = {"INSUFFICIENT": 0, "LOW": 40, "ACCEPTABLE": 60, "GOOD": 75, "EXCELLENT": 90}
CONFIDENCE_LEVELS = {"INSUFFICIENT": 0, "LOW": 40, "MEDIUM": 60, "HIGH": 75, "VERY_HIGH": 90}


def category(score: float, levels: dict) -> str:
    return max(
        (key for key, minimum in levels.items() if score >= minimum), key=lambda key: levels[key]
    )


class DataQualityService:
    def evaluate(self, f: Features, corners: bool = False, now: datetime | None = None) -> dict:
        now = now or datetime.now(UTC)
        groups = [f.home, f.away, f.home_split, f.away_split]
        if corners:
            groups = [
                [m for m in group if m.corners_for is not None and m.corners_against is not None]
                for group in groups
            ]
        home, away, home_split, away_split = groups
        n, split = min(len(home), len(away)), min(len(home_split), len(away_split))
        observed = [m.observed_at for m in home + away]
        oldest_team_update = (
            min(max(m.observed_at for m in home), max(m.observed_at for m in away))
            if home and away
            else None
        )
        age = (
            max(0, (now - oldest_team_update).total_seconds() / 3600)
            if oldest_team_update
            else float("inf")
        )
        freshness = 1.0 if age <= 6 else 0.6 if age <= 24 else 0.2
        team_ids = {entry.get("team_id") for entry in f.standings}
        standings = f.fixture.home_team_id in team_ids and f.fixture.away_team_id in team_ids
        shots = (
            min(sum(m.shots is not None for m in home), sum(m.shots is not None for m in away)) >= 5
        )
        xg = min(sum(m.xg is not None for m in home), sum(m.xg is not None for m in away)) >= 5
        score = (
            35 * min(n / 20, 1)
            + 25 * min(split / 5, 1)
            + 10 * standings
            + 5 * shots
            + 5 * xg
            + 10 * bool(f.league)
            + 10 * freshness
        )
        reasons = []
        if n < 5:
            reasons.append("Mínimo de 5 partidos con datos por equipo no alcanzado")
            score = min(score, 39)
        if split < 3:
            reasons.append("Muestra casa/fuera insuficiente")
        if not xg:
            reasons.append("xG no disponible o muestra insuficiente")
        if not f.league:
            reasons.append("Contexto de liga sin muestra suficiente")
        if age > 6:
            reasons.append("Estadísticas pendientes de actualización")
        return {
            "score": round(score, 1),
            "category": category(score, QUALITY_LEVELS),
            "sample_size": n,
            "split_sample": split,
            "freshness": freshness,
            "reasons": reasons,
            "last_updated": max(observed).isoformat() if observed else None,
        }


def confidence(quality: dict, ensemble: EnsembleOutput, market: str) -> dict:
    consensus = ensemble.consensus.get(market)
    if not consensus or quality["sample_size"] < 5:
        return {"score": 0, "category": "INSUFFICIENT"}
    agreement = max(0, 1 - consensus["model_std"] / 0.20)
    diversity = min(consensus["model_count"] / 3, 1)
    score = (
        0.6 * quality["score"]
        + 25 * agreement * diversity
        + 15 * min(quality["sample_size"] / 20, 1)
    )
    if consensus["model_disagreement"] == "HIGH":
        score = min(score, 59)
    if quality["split_sample"] < 3:
        score = min(score, 59)
    return {"score": round(score, 1), "category": category(score, CONFIDENCE_LEVELS)}
