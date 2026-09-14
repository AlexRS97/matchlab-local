import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from rapidfuzz.fuzz import ratio, token_set_ratio

from app.db.connection import Database
from app.domain.fixture import Fixture
from app.domain.odds import ProviderEvent

ALIASES = {
    "psg": "paris saint germain",
    "paris sg": "paris saint germain",
    "inter milan": "internazionale",
    "inter": "internazionale",
    "man utd": "manchester united",
    "man united": "manchester united",
    "man city": "manchester city",
    "atletico madrid": "atletico de madrid",
    "ath bilbao": "athletic club",
    "barca": "barcelona",
}


def normalize_name(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(token for token in value.split() if token not in {"fc", "cf", "afc"})


class MatchConfidence(StrEnum):
    EXACT = "EXACT"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNMATCHED = "UNMATCHED"


@dataclass
class MatchResult:
    fixture_id: int | None
    confidence: MatchConfidence
    score: float


class FixtureMatcher:
    def __init__(self, db: Database):
        self.db = db
        for alias, canonical in ALIASES.items():
            self.db.execute(
                "INSERT INTO team_aliases VALUES (?,?) ON CONFLICT DO NOTHING", [alias, canonical]
            )

    def canonical(self, name: str) -> str:
        normalized = normalize_name(name)
        rows = self.db.query("SELECT canonical FROM team_aliases WHERE alias=?", [normalized])
        return rows[0]["canonical"] if rows else normalized

    def search(self, query: str, fixture: Fixture) -> bool:
        query = self.canonical(query)
        return any(query in self.canonical(name) for name in (fixture.home_team, fixture.away_team))

    @staticmethod
    def variant(name: str) -> set[str]:
        return set(
            re.findall(r"\bu\d{2}\b|\bwomen\b|\bfemenin\w*\b|\breserves\b|\bii\b|\bb\b", name)
        )

    def match(self, event: ProviderEvent, fixtures: list[Fixture]) -> MatchResult:
        candidates = []
        home, away = self.canonical(event.home_team), self.canonical(event.away_team)
        for fixture in fixtures:
            delta = abs((fixture.kickoff_utc - event.kickoff_utc).total_seconds())
            if delta > 1800:
                continue
            fh, fa = self.canonical(fixture.home_team), self.canonical(fixture.away_team)
            if self.variant(home) != self.variant(fh) or self.variant(away) != self.variant(fa):
                continue
            hs, aws = ratio(home, fh) / 100, ratio(away, fa) / 100
            competition = (
                token_set_ratio(
                    normalize_name(event.competition), normalize_name(fixture.league_name)
                )
                / 100
            )
            if min(hs, aws) < 0.82 or competition < 0.55:
                continue
            score = 0.4 * hs + 0.4 * aws + 0.15 * competition + 0.05 * (1 - delta / 1800)
            safe = min(hs, aws) >= 0.90 and competition >= 0.65 and delta <= 900
            exact = hs == aws == 1 and delta <= 60 and competition >= 0.85
            candidates.append((score, fixture.fixture_id, exact, safe))
        candidates.sort(reverse=True)
        if not candidates:
            return MatchResult(None, MatchConfidence.UNMATCHED, 0)
        score, fixture_id, exact, safe = candidates[0]
        if len(candidates) > 1 and score - candidates[1][0] < 0.07:
            return MatchResult(None, MatchConfidence.MEDIUM, score)
        if not safe:
            return MatchResult(
                None, MatchConfidence.MEDIUM if score >= 0.85 else MatchConfidence.LOW, score
            )
        confidence = MatchConfidence.EXACT if exact else MatchConfidence.HIGH
        namespace = f"{event.provider}:{event.bookmaker.value}"
        self.db.execute(
            "INSERT OR REPLACE INTO provider_fixture_mappings VALUES (?,?,?,?,?,?)",
            [
                namespace,
                event.provider_event_id,
                fixture_id,
                confidence.value,
                score,
                datetime.now(UTC),
            ],
        )
        fixture = next(f for f in fixtures if f.fixture_id == fixture_id)
        for provider_id, team in [
            (event.home_provider_id, fixture.home_team_id),
            (event.away_provider_id, fixture.away_team_id),
        ]:
            if provider_id:
                self.db.execute(
                    "INSERT OR REPLACE INTO provider_team_mappings VALUES (?,?,?)",
                    [namespace, provider_id, team],
                )
        return MatchResult(fixture_id, confidence, score)
