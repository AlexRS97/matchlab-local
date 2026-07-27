from __future__ import annotations

import unicodedata
from typing import Any

EUROPE = {
    "albania",
    "andorra",
    "armenia",
    "austria",
    "azerbaijan",
    "belarus",
    "belgium",
    "bosnia",
    "bulgaria",
    "croatia",
    "cyprus",
    "czech-republic",
    "denmark",
    "england",
    "estonia",
    "faroe-islands",
    "finland",
    "france",
    "georgia",
    "germany",
    "gibraltar",
    "greece",
    "hungary",
    "iceland",
    "ireland",
    "israel",
    "italy",
    "kazakhstan",
    "kosovo",
    "latvia",
    "liechtenstein",
    "lithuania",
    "luxembourg",
    "malta",
    "moldova",
    "montenegro",
    "netherlands",
    "north-macedonia",
    "northern-ireland",
    "norway",
    "poland",
    "portugal",
    "romania",
    "russia",
    "san-marino",
    "scotland",
    "serbia",
    "slovakia",
    "slovenia",
    "spain",
    "espana",
    "sweden",
    "switzerland",
    "turkey",
    "ukraine",
    "wales",
}

AMERICAS = {
    "argentina",
    "bolivia",
    "brazil",
    "canada",
    "chile",
    "colombia",
    "costa-rica",
    "ecuador",
    "el-salvador",
    "guatemala",
    "honduras",
    "jamaica",
    "mexico",
    "nicaragua",
    "panama",
    "paraguay",
    "peru",
    "puerto-rico",
    "trinidad-and-tobago",
    "uruguay",
    "usa",
    "united-states",
    "estados-unidos",
    "venezuela",
}

ASIA = {
    "australia",
    "bahrain",
    "bangladesh",
    "china",
    "hong-kong",
    "india",
    "indonesia",
    "iran",
    "iraq",
    "japan",
    "jordan",
    "kuwait",
    "lebanon",
    "malaysia",
    "oman",
    "philippines",
    "qatar",
    "saudi-arabia",
    "singapore",
    "south-korea",
    "syria",
    "thailand",
    "united-arab-emirates",
    "uzbekistan",
    "vietnam",
}

AFRICA = {
    "algeria",
    "angola",
    "benin",
    "botswana",
    "burkina-faso",
    "cameroon",
    "congo",
    "dr-congo",
    "egypt",
    "ethiopia",
    "ghana",
    "guinea",
    "ivory-coast",
    "kenya",
    "libya",
    "mali",
    "morocco",
    "mozambique",
    "nigeria",
    "rwanda",
    "senegal",
    "south-africa",
    "sudan",
    "tanzania",
    "tunisia",
    "uganda",
    "zambia",
    "zimbabwe",
}

TOP_PATTERNS: tuple[tuple[str, int], ...] = (
    ("uefa-champions-league", 100),
    ("uefa-europa-league", 98),
    ("uefa-europa-conference-league", 95),
    ("copa-libertadores", 98),
    ("conmebol-libertadores", 98),
    ("copa-sudamericana", 94),
    ("conmebol-sudamericana", 94),
    ("afc-champions-league", 94),
    ("caf-champions-league", 92),
    ("world-cup", 100),
    ("euro-championship", 100),
    ("copa-america", 100),
    ("premier-league", 96),
    ("la-liga", 96),
    ("serie-a", 96),
    ("bundesliga", 96),
    ("ligue-1", 96),
    ("major-league-soccer", 90),
    ("liga-mx", 90),
    ("brasileirao", 90),
    ("serie-a-brazil", 90),
    ("primera-division", 86),
    ("eredivisie", 88),
    ("primeira-liga", 88),
    ("saudi-pro-league", 86),
    ("j1-league", 86),
    ("k-league", 84),
)


def _slug(value: str | None) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_value = normalized.encode("ascii", "ignore").decode().lower()
    return "-".join(ascii_value.replace("&", " and ").split())


def supports_fixture_statistics(coverage: dict[str, Any] | None) -> bool:
    fixtures = (coverage or {}).get("fixtures") or {}
    return fixtures.get("statistics_fixtures") is True


def supports_standings(coverage: dict[str, Any] | None) -> bool:
    return (coverage or {}).get("standings") is True


def supports_odds(coverage: dict[str, Any] | None) -> bool:
    return (coverage or {}).get("odds") is True


def competition_region(name: str, country: str | None) -> str:
    name_slug = _slug(name)
    country_slug = _slug(country)
    if any(token in name_slug for token in ("uefa", "euro-championship")):
        return "Europa"
    if any(
        token in name_slug
        for token in ("conmebol", "libertadores", "sudamericana", "copa-america", "concacaf")
    ):
        return "América"
    if any(token in name_slug for token in ("afc-", "asian", "asean")):
        return "Asia"
    if any(token in name_slug for token in ("caf-", "africa")):
        return "África"
    if country_slug in EUROPE:
        return "Europa"
    if country_slug in AMERICAS:
        return "América"
    if country_slug in ASIA:
        return "Asia"
    if country_slug in AFRICA:
        return "África"
    if country_slug in {"world", "international", ""}:
        return "Mundo"
    return "Otros"


def competition_priority(
    name: str,
    country: str | None,
    coverage: dict[str, Any] | None,
    is_friendly: bool,
) -> int:
    name_slug = _slug(name)
    country_slug = _slug(country)
    score = 35
    for pattern, priority in TOP_PATTERNS:
        if pattern in name_slug:
            score = max(score, priority)
    if (
        (country_slug == "england" and name_slug == "premier-league")
        or (country_slug == "spain" and name_slug == "la-liga")
        or (country_slug == "italy" and name_slug == "serie-a")
        or (country_slug == "germany" and name_slug == "bundesliga")
        or (country_slug == "france" and name_slug == "ligue-1")
    ):
        score = 100
    if supports_fixture_statistics(coverage):
        score += 8
    if supports_standings(coverage):
        score += 4
    if supports_odds(coverage):
        score += 3
    if is_friendly:
        score -= 45
    return max(0, min(score, 100))
