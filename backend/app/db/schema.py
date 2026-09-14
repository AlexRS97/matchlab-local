SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_versions(version INTEGER PRIMARY KEY, applied_at TIMESTAMPTZ);
INSERT INTO schema_versions VALUES (1, current_timestamp) ON CONFLICT DO NOTHING;
CREATE TABLE IF NOT EXISTS fixtures (
    fixture_id BIGINT PRIMARY KEY, provider VARCHAR, provider_fixture_id VARCHAR,
    date DATE, kickoff_utc TIMESTAMPTZ, kickoff_local VARCHAR, country VARCHAR,
    league_id BIGINT, league_name VARCHAR, season INTEGER,
    home_team_id BIGINT, home_team VARCHAR, away_team_id BIGINT, away_team VARCHAR,
    status VARCHAR, updated_at TIMESTAMPTZ, payload JSON
);
CREATE TABLE IF NOT EXISTS teams(team_id BIGINT PRIMARY KEY, name VARCHAR, source VARCHAR);
CREATE TABLE IF NOT EXISTS leagues(league_id BIGINT PRIMARY KEY, name VARCHAR, country VARCHAR);
CREATE TABLE IF NOT EXISTS recent_matches(
    fixture_id BIGINT, team_id BIGINT, kickoff_utc TIMESTAMPTZ, observed_at TIMESTAMPTZ,
    payload JSON, PRIMARY KEY(fixture_id, team_id)
);
CREATE TABLE IF NOT EXISTS standings_snapshots(
    id VARCHAR PRIMARY KEY, league_id BIGINT, season INTEGER, timestamp TIMESTAMPTZ, payload JSON
);
CREATE TABLE IF NOT EXISTS team_stats_snapshots(
    id VARCHAR PRIMARY KEY, team_id BIGINT, timestamp TIMESTAMPTZ, payload JSON
);
CREATE TABLE IF NOT EXISTS fixture_statistics(
    fixture_id BIGINT PRIMARY KEY, timestamp TIMESTAMPTZ, payload JSON
);
CREATE TABLE IF NOT EXISTS odds_snapshots(
    id VARCHAR PRIMARY KEY, fixture_id BIGINT, bookmaker VARCHAR, provider VARCHAR,
    market VARCHAR, line DOUBLE, side VARCHAR, decimal_odds DOUBLE,
    timestamp TIMESTAMPTZ, payload JSON
);
CREATE TABLE IF NOT EXISTS provider_fixture_mappings(
    provider VARCHAR, event_id VARCHAR, fixture_id BIGINT, confidence VARCHAR, score DOUBLE,
    timestamp TIMESTAMPTZ, PRIMARY KEY(provider, event_id)
);
CREATE TABLE IF NOT EXISTS provider_team_mappings(
    provider VARCHAR, provider_team_id VARCHAR, team_id BIGINT,
    PRIMARY KEY(provider, provider_team_id)
);
CREATE TABLE IF NOT EXISTS team_aliases(alias VARCHAR PRIMARY KEY, canonical VARCHAR);
CREATE TABLE IF NOT EXISTS predictions(
    id VARCHAR PRIMARY KEY, fixture_id BIGINT, timestamp TIMESTAMPTZ, version VARCHAR, payload JSON
);
CREATE TABLE IF NOT EXISTS corner_predictions(
    id VARCHAR PRIMARY KEY, fixture_id BIGINT, timestamp TIMESTAMPTZ, payload JSON
);
CREATE TABLE IF NOT EXISTS daily_rankings(
    date DATE, market VARCHAR, timestamp TIMESTAMPTZ, payload JSON, PRIMARY KEY(date, market)
);
CREATE TABLE IF NOT EXISTS analysis_cache(
    cache_key VARCHAR PRIMARY KEY, provider VARCHAR, created_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ, payload JSON
);
CREATE TABLE IF NOT EXISTS api_usage(
    provider VARCHAR, period VARCHAR, requests INTEGER, requests_remaining INTEGER,
    last_request TIMESTAMPTZ, reset_time TIMESTAMPTZ, PRIMARY KEY(provider, period)
);
CREATE TABLE IF NOT EXISTS settings(key VARCHAR PRIMARY KEY, payload JSON);
CREATE TABLE IF NOT EXISTS provider_status(
    provider VARCHAR PRIMARY KEY, last_success TIMESTAMPTZ, last_error VARCHAR,
    failures INTEGER DEFAULT 0, circuit_until TIMESTAMPTZ, last_request TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS prediction_results(
    fixture_id BIGINT, prediction_timestamp TIMESTAMPTZ, market VARCHAR,
    predicted_probability DOUBLE, odds_at_prediction DOUBLE, result DOUBLE,
    won BOOLEAN, bookmaker VARCHAR, settled_at TIMESTAMPTZ,
    PRIMARY KEY(fixture_id, market)
);
CREATE TABLE IF NOT EXISTS odds_boards(
    fixture_id BIGINT, provider VARCHAR, bookmaker VARCHAR, timestamp TIMESTAMPTZ, payload JSON,
    PRIMARY KEY(fixture_id,provider,bookmaker,timestamp)
);
"""
