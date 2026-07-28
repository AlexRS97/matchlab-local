import math
from dataclasses import asdict
from datetime import UTC, datetime
from statistics import fmean

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from football_api.models import (
    FeatureSnapshot,
    Fixture,
    Prediction,
    StandingSnapshot,
)
from football_api.services.persistence import FINISHED_STATUSES
from prediction_models import build_prediction

MODEL_VERSION = "baseline-poisson-nb-v2"


def _weighted_mean(values: list[float], fallback: float) -> float:
    if not values:
        return fallback
    weights = [math.exp(-index / 10) for index in range(len(values))]
    return sum(value * weight for value, weight in zip(values, weights, strict=True)) / sum(
        weights
    )


def _shrink(value: float, sample_size: int, prior: float, strength: float = 6.0) -> float:
    return (value * sample_size + prior * strength) / (sample_size + strength)


class PredictionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def generate_for_fixture(self, fixture: Fixture) -> Prediction:
        stored_fixture = self.db.scalar(
            select(Fixture)
            .options(
                selectinload(Fixture.home_team),
                selectinload(Fixture.away_team),
                selectinload(Fixture.competition),
            )
            .where(Fixture.id == fixture.id)
        )
        if stored_fixture is None:
            raise ValueError("Partido no encontrado")
        fixture = stored_fixture

        histories = list(
            self.db.scalars(
                select(Fixture)
                .options(selectinload(Fixture.statistics))
                .where(
                    Fixture.kickoff_at < fixture.kickoff_at,
                    Fixture.status.in_(FINISHED_STATUSES),
                    or_(
                        Fixture.home_team_id.in_(
                            [fixture.home_team_id, fixture.away_team_id]
                        ),
                        Fixture.away_team_id.in_(
                            [fixture.home_team_id, fixture.away_team_id]
                        ),
                    ),
                )
                .order_by(Fixture.kickoff_at.desc())
                .limit(100)
            ).all()
        )

        league_games = self.db.scalars(
            select(Fixture)
            .where(
                Fixture.competition_id == fixture.competition_id,
                Fixture.kickoff_at < fixture.kickoff_at,
                Fixture.status.in_(FINISHED_STATUSES),
                Fixture.home_goals.is_not(None),
                Fixture.away_goals.is_not(None),
            )
            .order_by(Fixture.kickoff_at.desc())
            .limit(300)
        ).all()
        league_home_goals = (
            fmean(
                [
                    float(game.home_goals)
                    for game in league_games
                    if game.home_goals is not None
                ]
            )
            if league_games
            else 1.45
        )
        league_away_goals = (
            fmean(
                [
                    float(game.away_goals)
                    for game in league_games
                    if game.away_goals is not None
                ]
            )
            if league_games
            else 1.15
        )

        home = self._team_history(histories, fixture.home_team_id, desired_home=True)
        away = self._team_history(histories, fixture.away_team_id, desired_home=False)
        home_for_all = _shrink(
            _weighted_mean(home["goals_for"], league_home_goals),
            len(home["goals_for"]),
            league_home_goals,
        )
        home_against_all = _shrink(
            _weighted_mean(home["goals_against"], league_away_goals),
            len(home["goals_against"]),
            league_away_goals,
        )
        away_for_all = _shrink(
            _weighted_mean(away["goals_for"], league_away_goals),
            len(away["goals_for"]),
            league_away_goals,
        )
        away_against_all = _shrink(
            _weighted_mean(away["goals_against"], league_home_goals),
            len(away["goals_against"]),
            league_home_goals,
        )
        home_for = _shrink(
            _weighted_mean(home["venue_goals_for"], home_for_all),
            len(home["venue_goals_for"]),
            home_for_all,
            strength=5,
        )
        home_against = _shrink(
            _weighted_mean(home["venue_goals_against"], home_against_all),
            len(home["venue_goals_against"]),
            home_against_all,
            strength=5,
        )
        away_for = _shrink(
            _weighted_mean(away["venue_goals_for"], away_for_all),
            len(away["venue_goals_for"]),
            away_for_all,
            strength=5,
        )
        away_against = _shrink(
            _weighted_mean(away["venue_goals_against"], away_against_all),
            len(away["venue_goals_against"]),
            away_against_all,
            strength=5,
        )

        home_xg = math.sqrt(max(0.1, home_for * away_against)) * 1.06
        away_xg = math.sqrt(max(0.1, away_for * home_against)) * 0.97

        cutoff = min(datetime.now(UTC), fixture.kickoff_at)
        home_standing = self._latest_standing(fixture.home_team_id, cutoff)
        away_standing = self._latest_standing(fixture.away_team_id, cutoff)
        if home_standing and away_standing and home_standing.rank and away_standing.rank:
            rank_delta = away_standing.rank - home_standing.rank
            adjustment = max(-0.15, min(0.15, rank_delta * 0.012))
            home_xg *= 1 + adjustment
            away_xg *= 1 - adjustment

        home_corners = self._expected_corners(home, away, is_home=True)
        away_corners = self._expected_corners(away, home, is_home=False)
        result = build_prediction(home_xg, away_xg, home_corners, away_corners)

        minimum_matches = min(len(home["goals_for"]), len(away["goals_for"]))
        corner_sample = min(len(home["corners_for"]), len(away["corners_for"]))
        confidence = min(0.92, 0.25 + minimum_matches * 0.025 + corner_sample * 0.012)
        if min(len(home["venue_goals_for"]), len(away["venue_goals_for"])) >= 5:
            confidence += 0.03
        if home_standing and away_standing:
            confidence += 0.05
        if fixture.competition.is_friendly:
            confidence *= 0.68
        confidence = round(min(confidence, 0.92), 2)
        quality = "alta" if confidence >= 0.75 else "media" if confidence >= 0.5 else "baja"

        features = {
            "home_matches": len(home["goals_for"]),
            "away_matches": len(away["goals_for"]),
            "home_venue_matches": len(home["venue_goals_for"]),
            "away_venue_matches": len(away["venue_goals_for"]),
            "home_goals_for_weighted": round(home_for, 3),
            "home_goals_against_weighted": round(home_against, 3),
            "away_goals_for_weighted": round(away_for, 3),
            "away_goals_against_weighted": round(away_against, 3),
            "league_home_goals": round(league_home_goals, 3),
            "league_away_goals": round(league_away_goals, 3),
            "home_rank": home_standing.rank if home_standing else None,
            "away_rank": away_standing.rank if away_standing else None,
            "home_corner_sample": len(home["corners_for"]),
            "away_corner_sample": len(away["corners_for"]),
            "is_friendly": fixture.competition.is_friendly,
        }
        now = datetime.now(UTC)
        self.db.add(
            FeatureSnapshot(
                fixture_id=fixture.id,
                snapshot_at=now,
                model_version=MODEL_VERSION,
                features=features,
            )
        )
        explanation = self._explanation(fixture, features, confidence, home_corners is not None)
        prediction = Prediction(
            fixture_id=fixture.id,
            generated_at=now,
            model_version=MODEL_VERSION,
            confidence=confidence,
            data_quality=quality,
            explanation=explanation,
            **asdict(result),
        )
        self.db.add(prediction)
        self.db.flush()
        return prediction

    @staticmethod
    def _team_history(
        histories: list[Fixture],
        team_id: int,
        *,
        desired_home: bool,
    ) -> dict[str, list[float]]:
        result: dict[str, list[float]] = {
            "goals_for": [],
            "goals_against": [],
            "venue_goals_for": [],
            "venue_goals_against": [],
            "corners_for": [],
            "corners_against": [],
        }
        for game in histories:
            if team_id not in (game.home_team_id, game.away_team_id):
                continue
            is_home = game.home_team_id == team_id
            own_goals = game.home_goals if is_home else game.away_goals
            opponent_goals = game.away_goals if is_home else game.home_goals
            if own_goals is not None and opponent_goals is not None:
                result["goals_for"].append(float(own_goals))
                result["goals_against"].append(float(opponent_goals))
                if is_home == desired_home:
                    result["venue_goals_for"].append(float(own_goals))
                    result["venue_goals_against"].append(float(opponent_goals))
            own_stat = next((stat for stat in game.statistics if stat.team_id == team_id), None)
            opponent_stat = next(
                (stat for stat in game.statistics if stat.team_id != team_id), None
            )
            if own_stat and own_stat.corners is not None:
                result["corners_for"].append(float(own_stat.corners))
            if opponent_stat and opponent_stat.corners is not None:
                result["corners_against"].append(float(opponent_stat.corners))
        return result

    @staticmethod
    def _expected_corners(
        team: dict[str, list[float]], opponent: dict[str, list[float]], *, is_home: bool
    ) -> float | None:
        if len(team["corners_for"]) < 3 or len(opponent["corners_against"]) < 3:
            return None
        baseline = 5.15 if is_home else 4.35
        team_for = _shrink(
            _weighted_mean(team["corners_for"], baseline), len(team["corners_for"]), baseline
        )
        opponent_against = _shrink(
            _weighted_mean(opponent["corners_against"], baseline),
            len(opponent["corners_against"]),
            baseline,
        )
        return max(1.5, min(8.5, math.sqrt(team_for * opponent_against)))

    def _latest_standing(self, team_id: int, cutoff: datetime) -> StandingSnapshot | None:
        return self.db.scalar(
            select(StandingSnapshot)
            .where(StandingSnapshot.team_id == team_id, StandingSnapshot.snapshot_at <= cutoff)
            .order_by(StandingSnapshot.snapshot_at.desc())
            .limit(1)
        )

    @staticmethod
    def _explanation(
        fixture: Fixture,
        features: dict,
        confidence: float,
        corners_available: bool,
    ) -> list[str]:
        reasons = [
            f"Forma ponderada: {features['home_matches']} partidos del local y "
            f"{features['away_matches']} del visitante, dando mas peso a los recientes.",
            f"Referencia de la competicion: {features['league_home_goals']:.2f} goles locales "
            f"y {features['league_away_goals']:.2f} visitantes por partido.",
        ]
        if features["home_rank"] and features["away_rank"]:
            reasons.append(
                f"Posiciones consideradas: {fixture.home_team.name} #{features['home_rank']} y "
                f"{fixture.away_team.name} #{features['away_rank']}."
            )
        if not corners_available:
            reasons.append(
                "No hay una muestra suficiente de corners; "
                "ese mercado queda sin estimacion."
            )
        if fixture.competition.is_friendly:
            reasons.append(
                "Es un amistoso: la confianza se reduce "
                "por rotaciones y motivacion incierta."
            )
        reasons.append(f"Confianza estadistica del analisis: {confidence:.0%}.")
        return reasons
