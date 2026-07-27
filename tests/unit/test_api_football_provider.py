import httpx

from football_providers.api_football import ApiFootballProvider


def test_provider_removes_none_parameters() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "unused" not in request.url.params
        assert request.headers["x-apisports-key"] == "secret"
        return httpx.Response(
            200,
            headers={
                "x-ratelimit-requests-limit": "100",
                "x-ratelimit-requests-remaining": "93",
                "x-ratelimit-limit": "10",
                "x-ratelimit-remaining": "7",
            },
            json={"errors": [], "response": [{"fixture": {"id": 1}}]},
        )

    provider = ApiFootballProvider("secret", "https://example.test")
    provider._client.close()
    provider._client = httpx.Client(
        base_url="https://example.test",
        headers={"x-apisports-key": "secret"},
        transport=httpx.MockTransport(handler),
    )
    response = provider._get("/fixtures", date="2026-07-17", unused=None)

    assert response.items[0]["fixture"]["id"] == 1
    assert provider.calls == 1
    assert provider.daily_remaining == 93
    assert provider.minute_limit == 10
    assert provider.can_call(configured_budget=100, reserve=5)
    provider.close()
