"""Regression tests for controls applied to every HTTP response."""

from fastapi.testclient import TestClient

from football_api.main import app


def test_health_response_has_browser_security_headers() -> None:
    with TestClient(app, base_url="http://localhost") as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_untrusted_host_is_rejected() -> None:
    with TestClient(app, base_url="http://untrusted.example") as client:
        response = client.get("/health")

    assert response.status_code == 400
