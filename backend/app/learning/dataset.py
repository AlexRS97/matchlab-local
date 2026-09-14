import hashlib
import json
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np

from app.core.config import read_config
from app.db.connection import Database
from app.domain.fixture import Fixture, FixtureStatus, MatchObservation
from app.domain.market import Market
from app.learning.features import FEATURE_NAMES, sequences, vectorize
from app.models.corners.ensemble import CornerEnsemble
from app.models.goals.ensemble import GoalEnsemble
from app.repositories.historical_repository import HistoricalRepository
from app.services.features import Features

HEADS = {"goals": 7, "btts": 2, "corners": 21}


def identifier(value: str) -> int:
    return int(hashlib.sha256(value.encode()).hexdigest()[:13], 16)


def build_dataset(
    db: Database, output: Path, embargo_days: int = 2, progress=None, on_progress=None
) -> dict:
    rows = [
        json.loads(r["payload"])
        for r in db.query("SELECT payload FROM historical_matches ORDER BY match_date, match_key")
    ]
    history: dict[tuple, list] = defaultdict(list)
    league_history: dict[str, list] = defaultdict(list)
    x, sequence, labels, timestamps, sources, baselines = [], [], [], [], [], []
    league_ids, statistical = [], []
    weights = read_config("model_weights")
    goal_model = GoalEnsemble(weights["goals"])
    corner_model = CornerEnsemble(weights["corners"])
    statistical_names = [f"goals:{m.name}" for m in goal_model.models] + [
        f"corners:{m.name}" for m in corner_model.models
    ]
    markets = list(Market)
    for index, row in enumerate(rows):
        kickoff = datetime.fromisoformat(row["date"]).replace(tzinfo=UTC)
        league = row["league_code"]
        team_home, team_away = identifier(league + row["home"]), identifier(league + row["away"])
        home = [m for m in reversed(history[(league, row["home"])]) if m.observed_at < kickoff][:40]
        away = [m for m in reversed(history[(league, row["away"])]) if m.observed_at < kickoff][:40]
        fixture = Fixture(
            fixture_id=identifier(row["match_key"]),
            provider="football_data",
            provider_fixture_id=row["match_key"],
            kickoff_utc=kickoff,
            country="",
            league_id=row["league_id"],
            league_name=row["league_name"],
            season=2000 + int(row["season"][:2]),
            home_team_id=team_home,
            home_team=row["home"],
            away_team_id=team_away,
            away_team=row["away"],
            status=FixtureStatus.NOT_STARTED,
            updated_at=kickoff - timedelta(seconds=1),
        )
        league_sample = [m for m in reversed(league_history[league]) if m.observed_at < kickoff][
            :200
        ]
        context = (
            {
                "home_goals": float(np.mean([m.goals_for for m in league_sample])),
                "away_goals": float(np.mean([m.goals_against for m in league_sample])),
            }
            if len(league_sample) >= 30
            else None
        )
        if min(len(home), len(away)) >= 5:
            features = Features(
                fixture,
                home[:20],
                away[:20],
                [m for m in home if m.is_home][:20],
                [m for m in away if not m.is_home][:20],
                context,
            )
            x.append(vectorize(features))
            sequence.append(sequences(features))
            corners = (
                int(row["home_corners"] + row["away_corners"])
                if row["home_corners"] is not None and row["away_corners"] is not None
                else -1
            )
            labels.append(
                [
                    min(6, row["home_goals"] + row["away_goals"]),
                    int(row["home_goals"] > 0 and row["away_goals"] > 0),
                    min(20, corners),
                ]
            )
            goals, corner_result = goal_model.predict(features), corner_model.predict(features)
            probabilities = {**goals.probabilities, **corner_result.probabilities}
            baselines.append([probabilities.get(m.value, np.nan) for m in markets])
            statistical.append(
                [
                    [model.probabilities.get(m.value, np.nan) for m in markets]
                    for model in goals.models + corner_result.models
                ]
            )
            league_ids.append(row["league_id"])
            timestamps.append(int(kickoff.timestamp()))
            sources.append(row["match_key"])
        available = kickoff + timedelta(days=embargo_days)
        for is_home, team, opponent, name, prefix, other in [
            (True, team_home, team_away, row["home"], "home", "away"),
            (False, team_away, team_home, row["away"], "away", "home"),
        ]:
            obs = MatchObservation(
                fixture_id=fixture.fixture_id,
                team_id=team,
                opponent_id=opponent,
                kickoff_utc=kickoff,
                completed_at=available,
                observed_at=available,
                is_home=is_home,
                goals_for=row[f"{prefix}_goals"],
                goals_against=row[f"{other}_goals"],
                corners_for=row[f"{prefix}_corners"],
                corners_against=row[f"{other}_corners"],
                shots=row[f"{prefix}_shots"],
                shots_on_target=row[f"{prefix}_shots_on_target"],
                league_id=row["league_id"],
                competition=row["league_name"],
                source="football_data_retrospective",
            )
            history[(league, name)].append(obs)
            if is_home:
                league_history[league].append(obs)
        if index % 100 == 0 or index == len(rows) - 1:
            message = f"Preparando datos anteriores al partido: {index + 1}/{len(rows)}"
            if progress and index % 1000 == 0:
                progress(message)
            if on_progress:
                on_progress(index + 1, len(rows), message)
    if not x:
        raise ValueError("No hay histórico suficiente para construir muestras de entrenamiento")
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output,
        x=np.asarray(x, np.float32),
        sequences=np.asarray(sequence, np.float32),
        y=np.asarray(labels, np.int64),
        dates=np.asarray(timestamps, np.int64),
        keys=np.asarray(sources),
        baseline=np.asarray(baselines, np.float32),
        leagues=np.asarray(league_ids, np.int64),
        statistical=np.asarray(statistical, np.float32),
    )
    metadata = {
        "rows": len(x),
        "historical_matches": len(rows),
        "feature_names": FEATURE_NAMES,
        "markets": [m.value for m in markets],
        "statistical_names": statistical_names,
        "embargo_days": embargo_days,
        "source": "football-data.co.uk",
        "source_revision": HistoricalRepository(db).revision(),
        "data_sha256": hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest(),
        "provenance": "retrospective result-derived features; publication times assumed with embargo",
        "first_date": datetime.fromtimestamp(timestamps[0], UTC).isoformat(),
        "last_date": datetime.fromtimestamp(timestamps[-1], UTC).isoformat(),
    }
    output.with_suffix(".json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def chronological_split(
    dates: np.ndarray, train=0.6, validation=0.15, calibration=0.1, embargo_days=2
) -> dict[str, np.ndarray]:
    unique = np.unique(dates)
    if len(unique) < 30:
        raise ValueError("Se necesitan al menos 30 fechas distintas")
    boundaries = [
        unique[int(len(unique) * fraction)]
        for fraction in (train, train + validation, train + validation + calibration)
    ]
    gap = embargo_days * 86400
    return {
        "train": np.flatnonzero(dates < boundaries[0] - gap),
        "validation": np.flatnonzero((dates >= boundaries[0]) & (dates < boundaries[1] - gap)),
        "calibration": np.flatnonzero((dates >= boundaries[1]) & (dates < boundaries[2] - gap)),
        "test": np.flatnonzero(dates >= boundaries[2]),
    }
