from dataclasses import dataclass, field
from typing import cast

import numpy as np
import polars as pl

from app.domain.fixture import Fixture, MatchObservation


@dataclass
class Features:
    fixture: Fixture
    home: list[MatchObservation]
    away: list[MatchObservation]
    home_split: list[MatchObservation]
    away_split: list[MatchObservation]
    league: dict | None = None
    standings: list[dict] = field(default_factory=list)
    h2h: list[MatchObservation] = field(default_factory=list)
    external: dict = field(default_factory=dict)


def eligible(matches: list[MatchObservation], fixture: Fixture) -> list[MatchObservation]:
    unique = {
        m.fixture_id: m
        for m in matches
        if m.fixture_id != fixture.fixture_id
        and m.completed_at < fixture.kickoff_utc
        and m.observed_at < fixture.kickoff_utc
    }
    return sorted(unique.values(), key=lambda m: m.kickoff_utc, reverse=True)


def build_features(
    fixture: Fixture,
    home: list[MatchObservation],
    away: list[MatchObservation],
    league_matches: list[MatchObservation],
    standings: list[dict],
    minimum_league: int = 30,
) -> Features:
    home, away = eligible(home, fixture), eligible(away, fixture)
    league_sample = [
        m
        for m in eligible(league_matches, fixture)
        if m.is_home and m.league_id == fixture.league_id
    ][:200]
    league = None
    if len(league_sample) >= minimum_league:
        league = summarize(league_sample)
        league["home_goals"] = league["goals_for"]
        league["away_goals"] = league["goals_against"]
        league["label"] = "Muestra de la competición"
        if league["corners_sample"] < minimum_league:
            league["average_total_corners"] = None
    h2h = [m for m in home if m.opponent_id == fixture.away_team_id][:10]
    return Features(
        fixture,
        home[:20],
        away[:20],
        [m for m in home if m.is_home][:20],
        [m for m in away if not m.is_home][:20],
        league,
        standings,
        h2h,
    )


def mean(matches: list[MatchObservation], field: str) -> float | None:
    values = [getattr(m, field) for m in matches if getattr(m, field) is not None]
    return float(np.mean(values)) if values else None


def summarize(matches: list[MatchObservation]) -> dict:
    if not matches:
        return {"sample_size": 0, "source": "api_football"}
    frame = pl.DataFrame([m.model_dump(mode="json") for m in matches])
    totals = frame["goals_for"] + frame["goals_against"]
    result = {
        "sample_size": len(matches),
        "source": matches[0].source,
        "last_updated": max(m.observed_at for m in matches).isoformat(),
        "goals_for": float(cast(float, frame["goals_for"].mean())),
        "goals_against": float(cast(float, frame["goals_against"].mean())),
        "total_goals_average": float(cast(float, totals.mean())),
        "btts_rate": float(
            cast(float, ((frame["goals_for"] > 0) & (frame["goals_against"] > 0)).mean())
        ),
    }
    for line in (0.5, 1.5, 2.5, 3.5, 4.5):
        result[f"over{str(line).replace('.', '')}_rate"] = float(
            cast(float, (totals > line).mean())
        )
    for name in (
        "shots",
        "shots_on_target",
        "possession",
        "xg",
        "xga",
        "corners_for",
        "corners_against",
    ):
        result[name] = mean(matches, name)
        result[f"{name}_sample"] = sum(getattr(m, name) is not None for m in matches)
    corners = [
        m.corners_for + m.corners_against
        for m in matches
        if m.corners_for is not None and m.corners_against is not None
    ]
    result["average_total_corners"] = float(np.mean(corners)) if corners else None
    result["corners_sample"] = len(corners)
    return result


def feature_summary(features: Features) -> dict:
    return {
        "home": {str(n): summarize(features.home[:n]) for n in (5, 10, 20)},
        "away": {str(n): summarize(features.away[:n]) for n in (5, 10, 20)},
        "home_split": summarize(features.home_split),
        "away_split": summarize(features.away_split),
        "league": features.league,
        "standings": features.standings,
        "h2h": {
            "summary": summarize(features.h2h),
            "matches": [m.model_dump(mode="json") for m in features.h2h],
        },
        "recent_home": [m.model_dump(mode="json") for m in features.home],
        "recent_away": [m.model_dump(mode="json") for m in features.away],
    }
