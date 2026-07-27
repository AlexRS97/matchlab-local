from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from football_api.config import Settings
from football_api.models import Competition, Fixture, IngestionJob, Team
from football_api.services.demo import seed_demo_data
from football_api.services.persistence import (
    FINISHED_STATUSES,
    store_raw_response,
    store_standings,
    upsert_fixture,
    upsert_fixture_statistics,
    upsert_league_catalog,
)
from football_api.services.predictions import PredictionService
from football_providers import ApiFootballProvider


class IngestionService:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    def run_daily(self, target_date: date) -> IngestionJob:
        job = IngestionJob(target_date=target_date, status="running", started_at=datetime.now(UTC))
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        try:
            if not self.settings.api_football_key:
                if not self.settings.app_demo_mode:
                    raise RuntimeError(
                        "Falta API_FOOTBALL_KEY. Configurala en .env o activa APP_DEMO_MODE."
                    )
                fixtures = seed_demo_data(self.db, target_date, self.settings.timezone)
                job.message = (
                    "Datos de demostracion generados; configura "
                    "API_FOOTBALL_KEY para datos reales."
                )
            else:
                fixtures = self._ingest_real_data(target_date, job)

            predictor = PredictionService(self.db)
            generated = 0
            for fixture in fixtures:
                predictor.generate_for_fixture(fixture)
                generated += 1
            self.db.commit()
            job.status = "completed"
            job.finished_at = datetime.now(UTC)
            job.fixtures_found = len(fixtures)
            job.predictions_generated = generated
            self.db.commit()
            return job
        except Exception as exc:
            self.db.rollback()
            job = self.db.get(IngestionJob, job.id)
            job.status = "failed"
            job.finished_at = datetime.now(UTC)
            job.error_detail = str(exc)
            self.db.commit()
            raise

    def _ingest_real_data(self, target_date: date, job: IngestionJob) -> list[Fixture]:
        provider = ApiFootballProvider(
            api_key=self.settings.api_football_key,
            base_url=self.settings.api_football_base_url,
            timeout_seconds=self.settings.api_football_timeout_seconds,
        )
        try:
            leagues_response = provider.current_leagues()
            store_raw_response(self.db, leagues_response)
            upsert_league_catalog(self.db, leagues_response.items)
            self.db.commit()

            response = provider.fixtures_by_date(
                target_date.isoformat(), self.settings.app_timezone
            )
            store_raw_response(self.db, response)
            fixtures = [upsert_fixture(self.db, item) for item in response.items]
            self.db.commit()

            provider_team_ids = []
            for fixture in fixtures:
                for team_id in (fixture.home_team_id, fixture.away_team_id):
                    team = self.db.get(Team, team_id)
                    if team and team.provider_id not in provider_team_ids:
                        provider_team_ids.append(team.provider_id)
            for team_provider_id in provider_team_ids[: self.settings.max_history_calls_per_run]:
                if provider.calls >= self.settings.api_football_daily_call_budget:
                    break
                history_response = provider.recent_team_fixtures(team_provider_id, last=20)
                store_raw_response(self.db, history_response)
                for item in history_response.items:
                    upsert_fixture(self.db, item)
                self.db.commit()

            team_ids = {
                team_id
                for fixture in fixtures
                for team_id in (fixture.home_team_id, fixture.away_team_id)
            }
            history = self.db.scalars(
                select(Fixture)
                .where(
                    Fixture.status.in_(FINISHED_STATUSES),
                    (Fixture.home_team_id.in_(team_ids) | Fixture.away_team_id.in_(team_ids)),
                    ~Fixture.statistics.any(),
                )
                .order_by(Fixture.kickoff_at.desc())
                .limit(self.settings.max_statistics_calls_per_run)
            ).all()
            for historical_fixture in history:
                fixture_coverage = historical_fixture.competition.coverage.get("fixtures", {})
                if fixture_coverage.get("statistics_fixtures") is False:
                    continue
                if provider.calls >= self.settings.api_football_daily_call_budget:
                    break
                stats_response = provider.fixture_statistics(historical_fixture.provider_id)
                store_raw_response(self.db, stats_response)
                upsert_fixture_statistics(self.db, historical_fixture, stats_response.items)
                self.db.commit()

            league_seasons = {(fixture.competition_id, fixture.season) for fixture in fixtures}
            for competition_id, season in league_seasons:
                competition = self.db.get(Competition, competition_id)
                if competition is None or competition.is_friendly:
                    continue
                if competition.coverage.get("standings") is False:
                    continue
                if provider.calls >= self.settings.api_football_daily_call_budget:
                    break
                standings_response = provider.standings(competition.provider_id, season)
                store_raw_response(self.db, standings_response)
                store_standings(self.db, competition, season, standings_response.items)
                self.db.commit()
            job.api_calls = provider.calls
            job.message = "Ingesta incremental completada desde API-Football."
            return fixtures
        finally:
            provider.close()
