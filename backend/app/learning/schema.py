SCHEMA = """
CREATE TABLE IF NOT EXISTS historical_matches (
    match_key VARCHAR PRIMARY KEY, league_code VARCHAR, match_date DATE,
    source VARCHAR, downloaded_at TIMESTAMPTZ, payload JSON
);
CREATE TABLE IF NOT EXISTS learning_runs (
    run_id VARCHAR PRIMARY KEY, created_at TIMESTAMPTZ, status VARCHAR,
    sample_count INTEGER, payload JSON
);
CREATE TABLE IF NOT EXISTS historical_imports (
    league_code VARCHAR, season VARCHAR, digest VARCHAR, row_count INTEGER,
    latest_match DATE, imported_at TIMESTAMPTZ, PRIMARY KEY (league_code, season)
);
"""
