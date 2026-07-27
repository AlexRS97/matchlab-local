select
    fixture_id,
    team_id,
    is_home,
    corners,
    shots_on_goal,
    total_shots,
    possession
from {{ source('app', 'team_fixture_statistics') }}

