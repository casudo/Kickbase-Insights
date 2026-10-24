"""Application settings.

All settings are read from environment variables with the `KBI_` prefix. Nested settings use a
double underscore, e.g. `KBI_KICKBASE__EMAIL`.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any
from zoneinfo import ZoneInfo

from croniter import croniter
from pydantic import AwareDatetime, BaseModel, BeforeValidator, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from sqlalchemy.engine import URL

from core.version import __version__

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent


def _comma_separated(value: Any) -> Any:
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return value


class AuthSettings(BaseModel):
    ### League names or IDs this server is for, comma separated. Empty allows every league of whoever logs in
    allowed_leagues: Annotated[list[str], NoDecode, BeforeValidator(_comma_separated)] = []
    ### How long a login lasts at most. Kickbase may end it earlier when its token expires.
    session_days: int = 30
    ### Encrypts the stored Kickbase session tokens. Generated and kept in the data folder when not set
    secret_key: SecretStr | None = None
    ### Failed logins per e-mail address within 15 minutes before further attempts are refused
    max_failed_logins: int = 3

    def allows(self, league_id: str, league_name: str) -> bool:
        if not self.allowed_leagues:
            return True
        wanted = {entry.casefold() for entry in self.allowed_leagues}
        return league_id.casefold() in wanted or league_name.casefold() in wanted


class ApiSettings(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    ### Proxies whose X-Forwarded-* headers are trusted, e.g. "*" behind Traefik in a Docker network.
    ### Needed for secure cookies over HTTPS and per client rate limits
    forwarded_allow_ips: str = "127.0.0.1"
    ### Only needed when the frontend is served from a different origin (e.g. `npm run dev` without proxy)
    cors_origins: list[str] = []


class DatabaseSettings(BaseModel):
    ### A full SQLAlchemy URL wins over everything else, e.g. postgresql+psycopg://user:pw@host/db
    url: str | None = None
    ### PostgreSQL is used when configured, SQLite otherwise
    host: str | None = None
    port: int = 5432
    database: str = "kickbase"
    username: str = "kickbase"
    password: SecretStr | None = None

    def sqlalchemy_url(self, data_dir: Path) -> str:
        if self.url:
            return self.url
        if self.host:
            return URL.create(
                "postgresql+psycopg",
                username=self.username,
                password=self.password.get_secret_value() if self.password else None,
                host=self.host,
                port=self.port,
                database=self.database,
            ).render_as_string(hide_password=False)
        return f"sqlite:///{(data_dir / 'kickbase.db').as_posix()}"


class KickbaseSettings(BaseModel):
    email: str | None = None
    password: SecretStr | None = None
    league: str | None = None # Defaults to the first league of the account.
    competition_id: int = 1
    discord_webhook: SecretStr | None = None
    start_date: AwareDatetime | None = None # The instant the season started or the league was reset. Feed events before it are ignored.
    start_money: int = 50_000_000
    collect_bonus: bool = True # Collect the daily login bonus on every sync

    @property
    def has_credentials(self) -> bool:
        return bool(self.email and self.password and self.password.get_secret_value())


class SyncSettings(BaseModel):
    ### Cron expression, evaluated in `timezone`
    schedule: str = "10 2,6,10,14,18,22 * * *"
    ### Sync right after startup when the last successful sync is older than this many minutes
    startup_if_older_than_minutes: int = 30
    ### Parallel requests against the Kickbase API
    concurrency: int = 12
    ### Player details (first name, points, injury notes) are re-fetched once they are this old
    player_details_max_age_hours: float = 12
    ### How long a live points response is reused before Kickbase is asked again
    live_cache_seconds: int = 45
    ### Minimum pause between two manually triggered syncs
    manual_cooldown_seconds: int = 120
    timezone: str = os.environ.get("TZ") or "Europe/Berlin"

    @field_validator("schedule")
    @classmethod
    def _valid_cron(cls, value: str) -> str:
        if not croniter.is_valid(value):
            raise ValueError(f"'{value}' is not a valid cron expression")
        return value

    @field_validator("timezone")
    @classmethod
    def _valid_timezone(cls, value: str) -> str:
        ZoneInfo(value)
        return value

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="KBI_",
        env_nested_delimiter="__",
        env_file=(BACKEND_DIR / ".env", ".env"),
        extra="ignore",
    )

    debug: bool = False
    version: str = __version__
    ### Where the SQLite database lives when no PostgreSQL server is configured
    data_dir: Path = BACKEND_DIR / "data"
    ### The built frontend. Served on / when the folder exists.
    frontend_dir: Path = REPO_DIR / "frontend" / "dist"
    ### Demo mode
    demo: bool = False

    api: ApiSettings = ApiSettings()
    auth: AuthSettings = AuthSettings()
    database: DatabaseSettings = DatabaseSettings()
    kickbase: KickbaseSettings = KickbaseSettings()
    sync: SyncSettings = SyncSettings()

    @property
    def database_url(self) -> str:
        return self.database.sqlalchemy_url(self.data_dir)


@lru_cache
def get_settings() -> Settings:
    return Settings()
