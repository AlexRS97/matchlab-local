from fastapi.testclient import TestClient
from test_models import features

from app.core.config import Settings
from app.main import create_app


def test_stored_football_to_models_to_today():
    f = features()
    settings = Settings(_env_file=None, duckdb_path=":memory:", enable_scheduler=False)
    with TestClient(create_app(settings)) as client:
        runtime = client.app.state.runtime
        runtime.fixtures.save(f.fixture)
        runtime.stats.save_matches(f.home + f.away)
        runtime.prediction_service.calculate(f.fixture)
        target = f.fixture.kickoff_utc.astimezone(settings.timezone).date()
        data = client.get(f"/api/today?date={target}").json()
        assert data["fixtures_found"] == 1
        prediction = data["fixtures"][0]["prediction"]
        assert 0 < prediction["goals"]["probabilities"]["OVER_2_5_GOALS"] < 1
        assert {m["name"] for m in prediction["goals"]["models"]} == {
            "poisson",
            "dixon_coles",
            "negative_binomial",
            "recent_form",
            "home_away",
            "xg",
            "external",
        }
        assert len(prediction["corners"]["models"]) == 4
        analysis = client.get(f"/api/fixtures/{f.fixture.fixture_id}/analysis").json()
        assert len(analysis["paragraphs"]) >= 4
        assert any("ensemble" in paragraph for paragraph in analysis["paragraphs"])
        assert client.get(f"/api/fixtures/{f.fixture.fixture_id}/goals").status_code == 200
