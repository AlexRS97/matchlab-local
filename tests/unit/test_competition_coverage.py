from football_api.services.competition_coverage import competition_priority, competition_region


def test_regions_cover_major_continents() -> None:
    assert competition_region("Premier League", "England") == "Europa"
    assert competition_region("La Liga", "España") == "Europa"
    assert competition_region("Copa Libertadores", "World") == "América"
    assert competition_region("J1 League", "Japan") == "Asia"


def test_major_tournaments_are_prioritized_over_friendlies() -> None:
    coverage = {
        "fixtures": {"statistics_fixtures": True},
        "standings": True,
        "odds": True,
    }
    champions = competition_priority("UEFA Champions League", "World", coverage, False)
    friendly = competition_priority("Club Friendlies", "World", coverage, True)
    assert champions == 100
    assert friendly < 20
