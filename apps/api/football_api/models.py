"""Modelo relacional transaccional y restricciones de integridad de MatchLab."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from football_api.database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Competition(Base, TimestampMixin):
    __tablename__ = "competitions"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), default="api_football", nullable=False)
    provider_id: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    country: Mapped[str | None] = mapped_column(String(120))
    competition_type: Mapped[str | None] = mapped_column(String(32))
    logo_url: Mapped[str | None] = mapped_column(Text)
    coverage: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    is_friendly: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    fixtures: Mapped[list["Fixture"]] = relationship(back_populates="competition")

    __table_args__ = (UniqueConstraint("provider", "provider_id", name="uq_competition_provider"),)


class Team(Base, TimestampMixin):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), default="api_football", nullable=False)
    provider_id: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    country: Mapped[str | None] = mapped_column(String(120))
    logo_url: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (UniqueConstraint("provider", "provider_id", name="uq_team_provider"),)


class Fixture(Base, TimestampMixin):
    __tablename__ = "fixtures"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), default="api_football", nullable=False)
    provider_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    competition_id: Mapped[int] = mapped_column(ForeignKey("competitions.id"), nullable=False)
    season: Mapped[int] = mapped_column(Integer, nullable=False)
    round_name: Mapped[str | None] = mapped_column(String(180))
    kickoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="NS")
    status_long: Mapped[str | None] = mapped_column(String(80))
    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    home_goals: Mapped[int | None] = mapped_column(Integer)
    away_goals: Mapped[int | None] = mapped_column(Integer)
    venue_name: Mapped[str | None] = mapped_column(String(180))
    referee: Mapped[str | None] = mapped_column(String(180))

    competition: Mapped[Competition] = relationship(back_populates="fixtures")
    home_team: Mapped[Team] = relationship(foreign_keys=[home_team_id])
    away_team: Mapped[Team] = relationship(foreign_keys=[away_team_id])
    statistics: Mapped[list["TeamFixtureStatistic"]] = relationship(
        back_populates="fixture", cascade="all, delete-orphan"
    )
    predictions: Mapped[list["Prediction"]] = relationship(
        back_populates="fixture", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("provider", "provider_id", name="uq_fixture_provider"),
        Index("ix_fixture_kickoff", "kickoff_at"),
        Index("ix_fixture_teams", "home_team_id", "away_team_id"),
    )


class TeamFixtureStatistic(Base, TimestampMixin):
    __tablename__ = "team_fixture_statistics"

    id: Mapped[int] = mapped_column(primary_key=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.id", ondelete="CASCADE"))
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    is_home: Mapped[bool] = mapped_column(Boolean, nullable=False)
    corners: Mapped[int | None] = mapped_column(Integer)
    shots_on_goal: Mapped[int | None] = mapped_column(Integer)
    total_shots: Mapped[int | None] = mapped_column(Integer)
    possession: Mapped[float | None] = mapped_column(Float)
    dangerous_attacks: Mapped[int | None] = mapped_column(Integer)
    raw_statistics: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    fixture: Mapped[Fixture] = relationship(back_populates="statistics")
    team: Mapped[Team] = relationship()

    __table_args__ = (UniqueConstraint("fixture_id", "team_id", name="uq_fixture_team_stat"),)


class StandingSnapshot(Base):
    __tablename__ = "standing_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    competition_id: Mapped[int] = mapped_column(ForeignKey("competitions.id"), nullable=False)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    season: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    rank: Mapped[int | None] = mapped_column(Integer)
    points: Mapped[int | None] = mapped_column(Integer)
    played: Mapped[int | None] = mapped_column(Integer)
    wins: Mapped[int | None] = mapped_column(Integer)
    draws: Mapped[int | None] = mapped_column(Integer)
    losses: Mapped[int | None] = mapped_column(Integer)
    goals_for: Mapped[int | None] = mapped_column(Integer)
    goals_against: Mapped[int | None] = mapped_column(Integer)
    form: Mapped[str | None] = mapped_column(String(16))

    __table_args__ = (Index("ix_standing_team_snapshot", "team_id", "snapshot_at"),)


class FeatureSnapshot(Base):
    __tablename__ = "feature_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.id", ondelete="CASCADE"))
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    features: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    __table_args__ = (Index("ix_feature_fixture_snapshot", "fixture_id", "snapshot_at"),)


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.id", ondelete="CASCADE"))
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    home_expected_goals: Mapped[float] = mapped_column(Float, nullable=False)
    away_expected_goals: Mapped[float] = mapped_column(Float, nullable=False)
    home_expected_corners: Mapped[float | None] = mapped_column(Float)
    away_expected_corners: Mapped[float | None] = mapped_column(Float)
    home_win_probability: Mapped[float] = mapped_column(Float, nullable=False)
    draw_probability: Mapped[float] = mapped_column(Float, nullable=False)
    away_win_probability: Mapped[float] = mapped_column(Float, nullable=False)
    over_2_5_probability: Mapped[float] = mapped_column(Float, nullable=False)
    btts_probability: Mapped[float] = mapped_column(Float, nullable=False)
    over_8_5_corners_probability: Mapped[float | None] = mapped_column(Float)
    over_9_5_corners_probability: Mapped[float | None] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    data_quality: Mapped[str] = mapped_column(String(16), nullable=False)
    likely_scores: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    explanation: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)

    fixture: Mapped[Fixture] = relationship(back_populates="predictions")

    __table_args__ = (Index("ix_prediction_fixture_generated", "fixture_id", "generated_at"),)


class OddsSnapshot(Base):
    __tablename__ = "odds_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.id", ondelete="CASCADE"))
    bookmaker: Mapped[str] = mapped_column(String(120), nullable=False)
    market: Mapped[str] = mapped_column(String(120), nullable=False)
    selection: Mapped[str] = mapped_column(String(120), nullable=False)
    decimal_odds: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (Index("ix_odds_fixture_captured", "fixture_id", "captured_at"),)


class RawApiResponse(Base):
    __tablename__ = "raw_api_responses"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(180), nullable=False)
    request_parameters: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    response_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    http_status: Mapped[int] = mapped_column(Integer, nullable=False)
    response_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (Index("ix_raw_endpoint_requested", "endpoint", "requested_at"),)


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    target_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    api_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fixtures_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    predictions_generated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    message: Mapped[str | None] = mapped_column(Text)
    error_detail: Mapped[str | None] = mapped_column(Text)
