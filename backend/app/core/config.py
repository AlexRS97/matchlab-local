from pathlib import Path
from zoneinfo import ZoneInfo

import yaml
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ROOT / ".env", ROOT / "backend/.env"), extra="ignore", env_file_encoding="utf-8"
    )
    app_timezone: str = "Europe/Madrid"
    duckdb_path: str = str(ROOT / "data/football.duckdb")
    api_football_key: SecretStr = SecretStr("")
    api_football_base_url: str = "https://v3.football.api-sports.io"
    api_football_daily_call_budget: int = Field(100, ge=1)
    api_football_quota_reserve: int = Field(5, ge=0)
    api_football_history_mode: str = "season"
    betfair_username: SecretStr = SecretStr("")
    betfair_password: SecretStr = SecretStr("")
    betfair_app_key: SecretStr = SecretStr("")
    betfair_cert_path: str = ""
    betfair_key_path: str = ""
    betfair_identity_domain: str = "betfair.com"
    pulsescore_api_key: SecretStr = SecretStr("")
    pulsescore_base_url: str = "https://api.pulsescore.net"
    pulsescore_monthly_budget: int = Field(500, ge=1)
    pulsescore_max_pages: int = Field(20, ge=1, le=1000)
    default_min_odds: float = Field(1.35, gt=1)
    enable_scheduler: bool = True
    ollama_enabled: bool = False
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = ""

    @field_validator("app_timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        ZoneInfo(value)
        return value

    @property
    def timezone(self) -> ZoneInfo:
        return ZoneInfo(self.app_timezone)


def read_config(name: str) -> dict:
    with (ROOT / "config" / f"{name}.yaml").open(encoding="utf-8") as stream:
        return yaml.safe_load(stream) or {}
