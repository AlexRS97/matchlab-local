import asyncio
import csv
import hashlib
import io
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

from app.core.config import ROOT
from app.db.connection import Database
from app.learning.schema import SCHEMA
from app.repositories.historical_repository import HistoricalRepository

LEAGUES = {
    "E0": (39, "Premier League", "England"),
    "D1": (78, "Bundesliga", "Germany"),
    "SP1": (140, "La Liga", "Spain"),
    "I1": (135, "Serie A", "Italy"),
    "F1": (61, "Ligue 1", "France"),
}


class FootballDataProvider:
    name = "football_data"

    def __init__(self, db: Database, directory: Path | None = None):
        self.db = db
        self.directory = directory or ROOT / "data/historical"
        self.directory.mkdir(parents=True, exist_ok=True)
        self.db.execute(SCHEMA)
        self.repository = HistoricalRepository(db)

    @staticmethod
    def parse(content: str, league: str, season: str) -> list[dict]:
        rows = []
        for row in csv.DictReader(io.StringIO(content.lstrip("\ufeff"))):
            if not row.get("HomeTeam") or not row.get("AwayTeam"):
                continue
            try:
                day = datetime.strptime(row["Date"], "%d/%m/%Y").date()
            except (ValueError, KeyError):
                try:
                    day = datetime.strptime(row["Date"], "%d/%m/%y").date()
                except (ValueError, KeyError):
                    continue
            if day >= datetime.now(UTC).date():
                continue
            try:
                goals_home, goals_away = int(row["FTHG"]), int(row["FTAG"])
            except (ValueError, KeyError, TypeError):
                continue
            if min(goals_home, goals_away) < 0:
                continue
            key = hashlib.sha256(
                f"{league}:{day}:{row['HomeTeam']}:{row['AwayTeam']}".encode()
            ).hexdigest()
            normalized = {
                "match_key": key,
                "date": day.isoformat(),
                "league_code": league,
                "league_id": LEAGUES[league][0],
                "league_name": LEAGUES[league][1],
                "season": season,
                "home": row["HomeTeam"],
                "away": row["AwayTeam"],
                "home_goals": goals_home,
                "away_goals": goals_away,
                "source": "football_data",
                "source_url": f"https://www.football-data.co.uk/mmz4281/{season}/{league}.csv",
            }
            # Strict whitelist: odds columns, closing prices and match outcomes never become input features.
            for original, field in {
                "HC": "home_corners",
                "AC": "away_corners",
                "HS": "home_shots",
                "AS": "away_shots",
                "HST": "home_shots_on_target",
                "AST": "away_shots_on_target",
            }.items():
                try:
                    value = float(row[original])
                    normalized[field] = value if 0 <= value < 100 else None
                except (ValueError, KeyError, TypeError):
                    normalized[field] = None
            rows.append(normalized)
        return rows

    async def update(
        self, leagues: list[str], seasons: list[str], progress=None, on_progress=None
    ) -> dict:
        errors, downloaded, imported, changed = [], 0, 0, 0
        total = sum(code in LEAGUES for code in leagues) * sum(
            len(s) == 4 and s.isdigit() for s in seasons
        )
        processed = 0
        async with httpx.AsyncClient(
            timeout=45, follow_redirects=True, headers={"User-Agent": "MatchLab-local/1.0"}
        ) as client:
            for league in leagues:
                if league not in LEAGUES:
                    continue
                for season in seasons:
                    if len(season) != 4 or not season.isdigit():
                        continue
                    if on_progress:
                        on_progress(processed, total, f"Revisando {league} {season}")
                    processed += 1
                    path = self.directory / f"{league}_{season}.csv"
                    content = None
                    now = datetime.now(UTC)
                    current = int(season[:2]) + 2000 >= now.year - 1
                    ttl = timedelta(hours=24) if current else timedelta(days=365)
                    fresh = (
                        path.exists()
                        and now - datetime.fromtimestamp(path.stat().st_mtime, UTC) < ttl
                    )
                    if fresh and current:
                        fresh = (
                            datetime.fromtimestamp(path.stat().st_mtime, UTC).date() == now.date()
                        )
                    if not fresh:
                        try:
                            response = await client.get(
                                f"https://www.football-data.co.uk/mmz4281/{season}/{league}.csv"
                            )
                            response.raise_for_status()
                            content = response.content.decode("utf-8-sig", errors="replace")
                            if "HomeTeam" not in content or "FTHG" not in content:
                                raise ValueError("CSV sin las columnas esperadas")
                            downloaded += 1
                        except (httpx.HTTPError, ValueError) as exc:
                            content = None
                            errors.append(f"{league} {season}: {type(exc).__name__}")
                            if not path.exists():
                                if on_progress:
                                    on_progress(
                                        processed, total, f"{league} {season}: fuente no disponible"
                                    )
                                continue
                    rows = self.parse(
                        content if content is not None else path.read_text(encoding="utf-8"),
                        league,
                        season,
                    )
                    try:
                        changed += await asyncio.to_thread(
                            self.repository.replace, league, season, rows
                        )
                        imported += len(rows)
                        if content is not None:
                            temporary = path.with_suffix(".tmp")
                            temporary.write_text(content, encoding="utf-8")
                            temporary.replace(path)
                    except ValueError as exc:
                        errors.append(str(exc))
                    if progress:
                        progress(f"Histórico {league} {season}: {len(rows)} partidos")
                    if on_progress:
                        on_progress(
                            processed,
                            total,
                            f"{processed}/{total} archivos · {league} {season}: {len(rows)} partidos",
                        )
        return {
            "downloaded_files": downloaded,
            "imported_rows": imported,
            "changed_files": changed,
            "source_revision": self.repository.revision(),
            "errors": errors,
            "stored_matches": self.db.query("SELECT count(*) AS n FROM historical_matches")[0]["n"],
        }
