from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from football_api.config import Settings
from football_api.models import Competition, Fixture, IngestionJob, Prediction, RawApiResponse, Team
from football_api.services.competition_coverage import (
    competition_priority,
    supports_fixture_statistics,
    supports_odds,
    supports_standings,
)
from football_api.services.demo import seed_demo_data
from football_api.services.persistence import (
    FINISHED_STATUSES,
    store_odds,
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
            now = datetime.now(UTC)
            prediction_fixtures = [
                fixture
                for fixture in fixtures
                if fixture.status in {"NS", "TBD"} and fixture.kickoff_at > now
            ]
            fixture_ids = [fixture.id for fixture in prediction_fixtures]
            prediction_cutoff = now - timedelta(
                minutes=self.settings.prediction_refresh_minutes
            )
            recently_predicted = set(
                self.db.scalars(
                    select(Prediction.fixture_id)
                    .where(
                        Prediction.fixture_id.in_(fixture_ids),
                        Prediction.generated_at >= prediction_cutoff,
                    )
                    .distinct()
                ).all()
            )
            for fixture in prediction_fixtures:
                if fixture.id in recently_predicted:
                    continue
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
            failed_job = self.db.get(IngestionJob, job.id)
            if failed_job is None:
                raise
            failed_job.status = "failed"
            failed_job.finished_at = datetime.now(UTC)
            failed_job.error_detail = str(exc)
            self.db.commit()
            raise

    def _ingest_real_data(self, target_date: date, job: IngestionJob) -> list[Fixture]:
        provider = ApiFootballProvider(
            api_key=self.settings.api_football_key,
            base_url=self.settings.api_football_base_url,
            timeout_seconds=self.settings.api_football_timeout_seconds,
        )
        try:
            if not self._requested_recently(
                "/leagues",
                {"current": "true"},
                timedelta(hours=self.settings.league_catalog_cache_hours),
            ):
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

            prioritized = sorted(fixtures, key=self._fixture_priority, reverse=True)
            provider_team_ids: list[int] = []
            for fixture in prioritized:
                for team_id in (fixture.home_team_id, fixture.away_team_id):
                    team = self.db.get(Team, team_id)
                    if team and team.provider_id not in provider_team_ids:
                        provider_team_ids.append(team.provider_id)
            histories_loaded = 0
            for team_provider_id in provider_team_ids:
                if histories_loaded >= self.settings.max_history_calls_per_run:
                    break
                parameters = {"team": team_provider_id, "last": 20, "status": "FT"}
                if self._requested_recently(
                    "/fixtures",
                    parameters,
                    timedelta(hours=self.settings.team_history_cache_hours),
                ):
                    continue
                if not self._can_call(provider):
                    break
                history_response = provider.recent_team_fixtures(team_provider_id, last=20)
                store_raw_response(self.db, history_response)
                for item in history_response.items:
                    upsert_fixture(self.db, item)
                self.db.commit()
                histories_loaded += 1

            team_ids = {
                team_id
                for fixture in fixtures
                for team_id in (fixture.home_team_id, fixture.away_team_id)
            }
            history = list(
                self.db.scalars(
                select(Fixture)
                .where(
                    Fixture.status.in_(FINISHED_STATUSES),
                    (Fixture.home_team_id.in_(team_ids) | Fixture.away_team_id.in_(team_ids)),
                    ~Fixture.statistics.any(),
                )
                .order_by(Fixture.kickoff_at.desc())
                .limit(self.settings.max_statistics_calls_per_run * 4)
                ).all()
            )
            history.sort(key=self._fixture_priority, reverse=True)
            statistics_loaded = 0
            for historical_fixture in history:
                if statistics_loaded >= self.settings.max_statistics_calls_per_run:
                    break
                if not supports_fixture_statistics(historical_fixture.competition.coverage):
                    continue
                if not self._can_call(provider):
                    break
                stats_response = provider.fixture_statistics(historical_fixture.provider_id)
                store_raw_response(self.db, stats_response)
                upsert_fixture_statistics(self.db, historical_fixture, stats_response.items)
                self.db.commit()
                statistics_loaded += 1

            league_seasons = {(fixture.competition_id, fixture.season) for fixture in fixtures}
            ordered_leagues = sorted(
                league_seasons,
                key=lambda item: self._competition_priority(self.db.get(Competition, item[0])),
                reverse=True,
            )
            standings_loaded = 0
            for competition_id, season in ordered_leagues:
                competition = self.db.get(Competition, competition_id)
                if competition is None or competition.is_friendly:
                    continue
                if not supports_standings(competition.coverage):
                    continue
                parameters = {"league": competition.provider_id, "season": season}
                if self._requested_recently(
                    "/standings",
                    parameters,
                    timedelta(hours=self.settings.standings_cache_hours),
                ):
                    continue
                if not self._can_call(provider):
                    break
                standings_response = provider.standings(competition.provider_id, season)
                store_raw_response(self.db, standings_response)
                store_standings(self.db, competition, season, standings_response.items)
                self.db.commit()
                standings_loaded += 1

            odds_loaded = 0
            now = datetime.now(UTC)
            for fixture in prioritized:
                if odds_loaded >= self.settings.max_odds_calls_per_run:
                    break
                if fixture.status not in {"NS", "TBD"}:
                    continue
                if fixture.kickoff_at < now or fixture.kickoff_at > now + timedelta(days=14):
                    continue
                if not supports_odds(fixture.competition.coverage):
                    continue
                parameters = {"fixture": fixture.provider_id}
                if self._requested_recently(
                    "/odds",
                    parameters,
                    timedelta(hours=self.settings.odds_cache_hours),
                ):
                    continue
                if not self._can_call(provider):
                    break
                odds_response = provider.odds(fixture.provider_id)
                store_raw_response(self.db, odds_response)
                store_odds(self.db, fixture, odds_response.items)
                self.db.commit()
                odds_loaded += 1

            job.api_calls = provider.calls
            remaining = (
                str(provider.daily_remaining)
                if provider.daily_remaining is not None
                else "desconocida"
            )
            job.message = (
                f"Cobertura mundial: {len(fixtures)} partidos; "
                f"{histories_loaded} historiales, {statistics_loaded} estadísticas, "
                f"{standings_loaded} clasificaciones y {odds_loaded} mercados actualizados. "
                f"Cuota diaria restante: {remaining}."
            )
            return fixtures
        finally:
            provider.close()

    def _requested_recently(
        self,
        endpoint: str,
        parameters: dict,
        maximum_age: timedelta,
    ) -> bool:
        candidates = self.db.scalars(
            select(RawApiResponse)
            .where(
                RawApiResponse.endpoint == endpoint,
                RawApiResponse.requested_at >= datetime.now(UTC) - maximum_age,
            )
            .order_by(RawApiResponse.requested_at.desc())
            .limit(500)
        ).all()
        return any(
            all(
                str(item.request_parameters.get(key)) == str(value)
                for key, value in parameters.items()
            )
            for item in candidates
        )

    def _can_call(self, provider: ApiFootballProvider) -> bool:
        return provider.can_call(
            self.settings.api_football_daily_call_budget,
            self.settings.api_football_quota_reserve,
        )

    @staticmethod
    def _competition_priority(competition: Competition | None) -> int:
        if competition is None:
            return 0
        return competition_priority(
            competition.name,
            competition.country,
            competition.coverage,
            competition.is_friendly,
        )

    def _fixture_priority(self, fixture: Fixture) -> int:
        return self._competition_priority(fixture.competition)
