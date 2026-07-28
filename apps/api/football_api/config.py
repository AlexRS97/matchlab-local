"""Configuración tipada de la aplicación cargada exclusivamente desde el entorno."""

from functools import lru_cache
from zoneinfo import ZoneInfo

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Contrato central de configuración compartido por API, workers y scripts."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_env: str = "development"
    app_secret_key: str = "change-me"
    app_timezone: str = "Europe/Madrid"
    app_cors_origins: str = "http://localhost:3000"
    app_allowed_hosts: str = "localhost,127.0.0.1,api"
    app_demo_mode: bool = True
    app_log_level: str = "INFO"

    database_url: str = (
        "postgresql+psycopg://football:football_local_password@localhost:5432/football_analytics"
    )
    redis_url: str = "redis://localhost:6379/0"

    api_football_key: str = ""
    api_football_base_url: str = "https://v3.football.api-sports.io"
    api_football_timeout_seconds: int = 30
    api_football_daily_call_budget: int = 7000
    api_football_quota_reserve: int = 5
    max_history_calls_per_run: int = 80
    max_statistics_calls_per_run: int = 120
    max_odds_calls_per_run: int = 40
    league_catalog_cache_hours: int = 168
    team_history_cache_hours: int = 18
    standings_cache_hours: int = 12
    odds_cache_hours: int = 3
    prediction_refresh_minutes: int = 30
    automatic_refresh_minutes: int = 30
    enable_scheduled_ingestion: bool = True

    @field_validator("app_timezone")
    @classmethod
    def timezone_must_exist(cls, value: str) -> str:
        ZoneInfo(value)
        return value

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.app_cors_origins.split(",") if origin.strip()]

    @property
    def allowed_hosts(self) -> list[str]:
        """Hosts HTTP válidos; evita que una cabecera Host manipulada alcance la aplicación."""

        return [host.strip() for host in self.app_allowed_hosts.split(",") if host.strip()]

    @property
    def timezone(self) -> ZoneInfo:
        return ZoneInfo(self.app_timezone)


@lru_cache
def get_settings() -> Settings:
    """Devuelve una única configuración validada por proceso."""

    return Settings()
