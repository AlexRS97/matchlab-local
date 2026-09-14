import asyncio
import logging
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from app.core.config import read_config
from app.core.exceptions import ProviderError
from app.db.connection import encode
from app.domain.fixture import FixtureStatus

if TYPE_CHECKING:
    from app.services.runtime import AnalyticsRuntime

log = logging.getLogger("matchlab")


class RefreshPipeline:
    def __init__(self, runtime: "AnalyticsRuntime"):
        self.runtime = runtime

    def can_fetch(self):
        r = self.runtime
        return (
            r.football.configured
            and r.football.transport.usage.status()["requests_remaining"]
            > r.settings.api_football_quota_reserve
        )

    async def calculate(self, fixture, force=False):
        task = asyncio.create_task(
            asyncio.to_thread(self.runtime.prediction_service.calculate, fixture, force=force)
        )
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            # A normal API shutdown must not close DuckDB while this thread still uses it.
            await task
            raise

    async def run(self, target: date):
        r = self.runtime
        settings = r.user_settings.get()
        progress = r.progress
        assert progress is not None
        for key in ("fixtures_minutes", "standings_minutes", "stats_minutes"):
            r.football.refresh[key] = getattr(settings, key)
        progress.start("fixtures", detail="Consultando partidos disponibles")
        fixture_error = ""
        try:
            fixtures = await r.fixture_service.refresh(target)
        except ProviderError as exc:
            fixture_error = str(exc)
            r.job["errors"].append(str(exc))
            fixtures = r.fixtures.for_date(target)
        r.job["total"] = len(fixtures)
        pending = [f for f in fixtures if f.prematch(datetime.now(UTC))]
        progress.end(fixture_error)
        progress.start("form", len(pending))
        seen = set()
        for index, fixture in enumerate(pending):
            if not self.can_fetch():
                break
            for team in (fixture.home_team_id, fixture.away_team_id):
                if team in seen:
                    continue
                seen.add(team)
                try:
                    history = await r.football.get_recent_matches(
                        team, fixture.kickoff_utc, fixture.season
                    )
                    r.stats.save_matches(history)
                except ProviderError as exc:
                    r.job["errors"].append(str(exc))
            # Publish progressively so a long refresh never hides the first analysed fixtures.
            await self.calculate(fixture)
            progress.update(index + 1, detail=f"{fixture.home_team} · {fixture.away_team}")
            await asyncio.sleep(0)
        progress.end(
            "Cobertura limitada por disponibilidad o cuota"
            if pending and not self.can_fetch()
            else ""
        )
        leagues = list(dict.fromkeys((f.league_id, f.season) for f in pending))
        progress.start("standings", len(leagues))
        for index, (league, season) in enumerate(leagues):
            if not self.can_fetch():
                break
            try:
                standings = await r.football.get_standings(league, season)
                r.stats.save_standings(
                    league, season, standings, r.football.transport.last_response_at
                )
                r.stats.save_matches(await r.football.get_league_matches(league, season))
            except ProviderError as exc:
                r.job["errors"].append(str(exc))
            progress.update(index + 1, detail=f"Liga {league} · temporada {season}")
        progress.end(
            "Cobertura limitada por disponibilidad o cuota"
            if leagues and not self.can_fetch()
            else ""
        )
        progress.start("stats", len(pending))
        remaining = read_config("refresh")["max_stats_requests_per_refresh"]
        for index, fixture in enumerate(pending):
            if not self.can_fetch():
                break
            home = r.stats.matches(fixture.home_team_id, fixture.kickoff_utc)
            away = r.stats.matches(fixture.away_team_id, fixture.kickoff_utc)
            # Alternate teams to avoid exhausting the quota on only one side of a fixture.
            matches = (
                [m for pair in zip(home, away, strict=False) for m in pair]
                + home[len(away) :]
                + away[len(home) :]
            )
            try:
                remaining -= await r.team_service.enrich_statistics(matches, remaining)
            except ProviderError as exc:
                r.job["errors"].append(str(exc))
            progress.update(index + 1, detail=f"{fixture.home_team} · {fixture.away_team}")
            if remaining <= 0:
                break
        progress.end(
            "Estadísticas parciales por presupuesto"
            if pending and (remaining <= 0 or not self.can_fetch())
            else ""
        )
        progress.start("context", len(pending[:10]))
        for index, fixture in enumerate(pending[:10]):
            if not self.can_fetch():
                break
            try:
                rows = await r.football.get_head_to_head(fixture.home_team_id, fixture.away_team_id)
                history = [
                    m
                    for m in rows
                    if m.completed_at < fixture.kickoff_utc and m.fixture_id != fixture.fixture_id
                ]
                r.stats.save_matches(history)
                external = await r.football.get_predictions(fixture.fixture_id)
                r.football.transport.cache.put(
                    f"external:{fixture.fixture_id}",
                    "api_football",
                    external,
                    21600,
                    r.football.transport.last_response_at,
                )
            except ProviderError as exc:
                r.job["errors"].append(str(exc))
            progress.update(index + 1, detail=f"{fixture.home_team} · {fixture.away_team}")
        progress.end(
            "Contexto parcial por disponibilidad o cuota"
            if pending and not self.can_fetch()
            else ""
        )
        progress.start("models", len(fixtures))
        for fixture in fixtures:
            await self.calculate(fixture, force=r.job.get("force_analysis", False))
            r.job["completed"] += 1
            progress.update(r.job["completed"], detail=f"{fixture.home_team} · {fixture.away_team}")
            await asyncio.sleep(0)
        progress.end()
        progress.start("odds", detail="Consultando Betfair y PulseScore")
        odds_errors = await r.odds_refresh.refresh(target, fixtures, settings, progress=progress)
        r.job["errors"].extend(odds_errors)
        progress.end(" · ".join(odds_errors))
        r.performance.record(r.dashboard.rows(target, settings))
        for fixture in fixtures:
            r.performance.settle(fixture)
        # Recover results even when the application was closed across midnight.
        unresolved = r.db.query("""SELECT DISTINCT f.fixture_id FROM fixtures f JOIN prediction_results p USING(fixture_id)
            WHERE p.won IS NULL AND f.kickoff_utc<current_timestamp - INTERVAL '3 hours'
            AND f.kickoff_utc>current_timestamp - INTERVAL '14 days' ORDER BY f.fixture_id LIMIT 30""")
        progress.start("results", len(unresolved) + 1)
        for index, row in enumerate(unresolved):
            if not self.can_fetch():
                break
            try:
                fixture = await r.football.get_fixture(row["fixture_id"])
                if fixture is None:
                    continue
                r.fixtures.save(fixture)
                r.performance.settle(fixture)
                if fixture.status == FixtureStatus.FINISHED and fixture.source_status == "FT":
                    stats = await r.football.get_fixture_statistics(fixture.fixture_id)
                    fixture.home_corners = stats.get(fixture.home_team_id, {}).get("corners")
                    fixture.away_corners = stats.get(fixture.away_team_id, {}).get("corners")
                r.fixtures.save(fixture)
                r.performance.settle(fixture)
            except ProviderError as exc:
                r.job["errors"].append(str(exc))
            progress.update(index + 1, detail="Revisando resultados pendientes")
        # Only the default ranking snapshot is persisted; filters are evaluated on request.
        dashboard = r.dashboard.today(target, settings)
        for market, picks in dashboard["top_groups"].items():
            r.db.execute(
                "INSERT OR REPLACE INTO daily_rankings VALUES (?,?,?,?)",
                [target, market, datetime.now(UTC), encode(picks)],
            )
        r.job["stage"] = "Finalizado"
        progress.end()
        for step in progress.steps:
            if step["status"] == "warning":
                r.job["errors"].append(
                    f"{step['label']}: cobertura parcial; consulta los proveedores"
                )
