with team_matches as (
    select
        fixture_id,
        kickoff_at,
        home_team_id as team_id,
        home_goals as goals_for,
        away_goals as goals_against
    from {{ ref('stg_fixtures') }}
    where status in ('FT', 'AET', 'PEN')

    union all

    select
        fixture_id,
        kickoff_at,
        away_team_id as team_id,
        away_goals as goals_for,
        home_goals as goals_against
    from {{ ref('stg_fixtures') }}
    where status in ('FT', 'AET', 'PEN')
)

select
    fixture_id,
    kickoff_at,
    team_id,
    avg(goals_for) over (
        partition by team_id order by kickoff_at rows between 5 preceding and 1 preceding
    ) as goals_for_previous_5,
    avg(goals_against) over (
        partition by team_id order by kickoff_at rows between 5 preceding and 1 preceding
    ) as goals_against_previous_5
from team_matches

