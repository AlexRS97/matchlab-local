import numpy as np

from app.services.features import Features

FIELDS = (
    "goals_for",
    "goals_against",
    "corners_for",
    "corners_against",
    "shots",
    "shots_on_target",
)
GROUPS = ("home5", "home10", "home20", "away5", "away10", "away20", "home_split", "away_split")
FEATURE_NAMES = [
    f"{group}_{name}" for group in GROUPS for name in (*FIELDS, "over25", "btts", "sample")
]
FEATURE_NAMES += ["home_rest_days", "away_rest_days", "league_home_goals", "league_away_goals"]


def vectorize(f: Features) -> np.ndarray:
    values = []
    groups = [
        f.home[:5],
        f.home[:10],
        f.home[:20],
        f.away[:5],
        f.away[:10],
        f.away[:20],
        f.home_split[:10],
        f.away_split[:10],
    ]
    for matches in groups:
        for name in FIELDS:
            observed = [getattr(m, name) for m in matches if getattr(m, name) is not None]
            values.append(float(np.mean(observed)) if observed else np.nan)
        values.extend(
            [
                float(np.mean([m.goals_for + m.goals_against > 2.5 for m in matches]))
                if matches
                else np.nan,
                float(np.mean([m.goals_for > 0 and m.goals_against > 0 for m in matches]))
                if matches
                else np.nan,
                len(matches),
            ]
        )
    values.extend(
        [
            min(60, (f.fixture.kickoff_utc - group[0].kickoff_utc).total_seconds() / 86400)
            if group
            else np.nan
            for group in (f.home, f.away)
        ]
    )
    values.extend(
        [
            f.league.get("home_goals", np.nan) if f.league else np.nan,
            f.league.get("away_goals", np.nan) if f.league else np.nan,
        ]
    )
    return np.asarray(values, dtype=np.float32)


def sequences(f: Features) -> np.ndarray:
    # Two histories aligned by recency, oldest to newest, with explicit missing-value masks.
    result = np.full((10, 14), np.nan, dtype=np.float32)
    for team_index, group in enumerate((f.home, f.away)):
        recent = list(reversed(group[:10]))
        for index, match in enumerate(recent, start=10 - len(recent)):
            result[index, team_index * 7 : (team_index + 1) * 7] = [
                *(
                    getattr(match, field) if getattr(match, field) is not None else np.nan
                    for field in FIELDS
                ),
                float(match.is_home),
            ]
    return result


class Preprocessor:
    def __init__(self, median=None, scale=None):
        self.median = np.asarray(median, dtype=np.float32) if median is not None else None
        self.scale = np.asarray(scale, dtype=np.float32) if scale is not None else None

    def fit(self, x: np.ndarray):
        flat = x.reshape(-1, x.shape[-1])
        self.median = np.asarray(
            [np.nanmedian(col) if np.isfinite(col).any() else 0 for col in flat.T], dtype=np.float32
        )
        clean = np.where(np.isfinite(flat), flat, self.median)
        self.scale = np.maximum(clean.std(axis=0), 0.1)
        return self

    def transform(self, x: np.ndarray) -> np.ndarray:
        if self.median is None or self.scale is None:
            raise ValueError("El preprocesador no está ajustado")
        missing = ~np.isfinite(x)
        clean = (np.where(missing, self.median, x) - self.median) / self.scale
        return np.concatenate(
            [np.clip(clean, -10, 10), missing.astype(np.float32)], axis=-1
        ).astype(np.float32)

    def state(self):
        if self.median is None or self.scale is None:
            raise ValueError("El preprocesador no está ajustado")
        return {"median": self.median.tolist(), "scale": self.scale.tolist()}
