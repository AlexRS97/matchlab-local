import json
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from test_models import features

from app.core.config import ROOT, Settings
from app.domain.market import Market
from app.main import create_app

# Browser contract scenario only. It is never inserted into the user's database.
if __name__ == "__main__":
    settings = Settings(_env_file=None, duckdb_path=":memory:", enable_scheduler=False)
    with TestClient(create_app(settings)) as client:
        runtime = client.app.state.runtime
        f = features()
        for match in f.home + f.away:
            match.shots = 12
            match.shots_on_target = 5
        runtime.stats.save_matches(f.home + f.away)
        runtime.stats.save_standings(
            140,
            f.fixture.season,
            [
                {
                    "position": 1,
                    "team_id": 1,
                    "team": "Prueba Local",
                    "points": 35,
                    "goal_difference": 14,
                    "played": 15,
                    "wins": 10,
                    "draws": 5,
                    "losses": 0,
                    "goals_for": 30,
                    "goals_against": 16,
                    "source": "test",
                    "observed_at": datetime.now(UTC).isoformat(),
                }
            ],
            datetime.now(UTC),
        )
        for i in range(6):
            fixture = f.fixture.model_copy(
                update={
                    "fixture_id": 1000 + i,
                    "provider_fixture_id": str(1000 + i),
                    "home_team": f"Prueba Local {i + 1}",
                    "away_team": f"Prueba Visitante {i + 1}",
                }
            )
            runtime.fixtures.save(fixture)
            runtime.prediction_service.calculate(fixture)
            for market in Market:
                for index, book in enumerate(["BETFAIR", "BET365", "WINAMAX"]):
                    response = client.post(
                        "/api/odds/manual",
                        json={
                            "fixture_id": fixture.fixture_id,
                            "bookmaker": book,
                            "market": market.value,
                            "line": market.line,
                            "odds": 1.55 + 0.05 * index,
                        },
                    )
                    assert response.status_code == 201, response.text
        target = f.fixture.kickoff_utc.astimezone(settings.timezone).date()
        payload = {
            "today": client.get(f"/api/today?date={target}").json(),
            "top": {
                m.value: client.get(f"/api/top?date={target}&market={m.value}").json()
                for m in Market
            },
            "detail": client.get("/api/fixtures/1000").json(),
            "odds": client.get("/api/fixtures/1000/odds").json(),
            "analysis": client.get("/api/fixtures/1000/analysis").json(),
            "settings": client.get("/api/settings").json(),
        }
        output = ROOT / ".runtime/ui-scenario.json"
        output.parent.mkdir(exist_ok=True)
        output.write_text(json.dumps(payload), encoding="utf-8")
        print(
            f"Browser scenario: {len(payload['today']['fixtures'])} matches, {len(payload['top']['OVER_2_5_GOALS'])} top picks"
        )
