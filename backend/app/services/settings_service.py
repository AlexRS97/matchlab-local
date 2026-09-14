from app.core.config import Settings, read_config
from app.db.connection import Database
from app.domain.settings import UserSettings


class SettingsService:
    def __init__(self, db: Database, environment: Settings):
        self.db, self.environment = db, environment

    def get(self) -> UserSettings:
        rows = self.db.query("SELECT payload FROM settings WHERE key='user'")
        if rows:
            return UserSettings.model_validate_json(rows[0]["payload"])
        refresh, ranking, providers = (
            read_config("refresh"),
            read_config("ranking"),
            read_config("providers"),
        )
        defaults = ranking["defaults"]
        return UserSettings(
            minimum_odds=self.environment.default_min_odds,
            top_n=defaults["top_n"],
            minimum_confidence=defaults["minimum_confidence"],
            minimum_data_quality=defaults["minimum_data_quality"],
            betfair_fallback=providers["pulsescore"].get("betfair_fallback", False),
            **{key: value for key, value in refresh.items() if key in UserSettings.model_fields},
        )

    def save(self, settings: UserSettings):
        self.db.execute(
            "INSERT OR REPLACE INTO settings VALUES ('user', ?)", [settings.model_dump_json()]
        )
        return settings
