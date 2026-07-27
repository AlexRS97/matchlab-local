select
    id as fixture_id,
    provider,
    provider_id,
    competition_id,
    season,
    kickoff_at,
    status,
    home_team_id,
    away_team_id,
    home_goals,
    away_goals
from {{ source('app', 'fixtures') }}

