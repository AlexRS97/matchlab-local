with latest_prediction as (
    select *, row_number() over (partition by fixture_id order by generated_at desc) as row_number
    from {{ source('app', 'predictions') }}
)

select
    f.fixture_id,
    f.kickoff_at,
    c.name as competition_name,
    home.name as home_team,
    away.name as away_team,
    p.home_expected_goals,
    p.away_expected_goals,
    p.home_expected_corners,
    p.away_expected_corners,
    p.confidence,
    p.data_quality
from {{ ref('stg_fixtures') }} f
join {{ source('app', 'competitions') }} c on c.id = f.competition_id
join {{ source('app', 'teams') }} home on home.id = f.home_team_id
join {{ source('app', 'teams') }} away on away.id = f.away_team_id
left join latest_prediction p on p.fixture_id = f.fixture_id and p.row_number = 1

