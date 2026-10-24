"""DB tables."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, BigInteger, Column, DateTime, Index
from sqlalchemy.types import TypeDecorator
from sqlmodel import Field, SQLModel

### Bump when a table changes. Older databases are rebuilt on startup, see db.init_db.
SCHEMA_VERSION = 1


class UTCDateTime(TypeDecorator):
    """Stores timezone aware datetimes as UTC and always hands them back timezone aware.

    SQLite has no timezone support and would otherwise return naive datetimes.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Naive datetimes are not allowed, use timezone aware UTC datetimes")
        value = value.astimezone(UTC)
        return value.replace(tzinfo=None) if dialect.name == "sqlite" else value

    def process_result_value(self, value: datetime | None, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def utcnow() -> datetime:
    return datetime.now(UTC)


def _ts(nullable: bool = True, index: bool = False):
    return Field(default=None, sa_type=UTCDateTime, nullable=nullable, index=index)


def _money(default: int | None = None):
    ### Team values reach several hundred million, beyond a 32 bit integer
    return Field(default=default, sa_type=BigInteger)


### ===============================================================================
### Competition
### ===============================================================================


class Team(SQLModel, table=True):
    id: str = Field(primary_key=True)
    competition_id: int = Field(default=1, index=True)
    name: str
    image: str | None = None
    placement: int | None = None
    points: int | None = None
    matches: int | None = None
    goal_diff: int | None = None
    updated_at: datetime = Field(default_factory=utcnow, sa_type=UTCDateTime)


class Player(SQLModel, table=True):
    id: str = Field(primary_key=True)
    team_id: str | None = Field(default=None, index=True)
    first_name: str | None = None
    last_name: str = ""
    position: int = 0 # 1 goalkeeper, 2 defender, 3 midfielder, 4 forward, 0 unknown
    status: int = 0
    status_text: str | None = None
    market_value: int = _money(0)
    market_value_trend: int = 0 # 0 flat, 1 rising, 2 falling
    total_points: int | None = None
    average_points: int | None = None
    goals: int | None = None
    assists: int | None = None
    image: str | None = None
    active: bool = True # False once the player no longer shows up in any team (left the league)
    details_synced_at: datetime | None = _ts()
    updated_at: datetime = Field(default_factory=utcnow, sa_type=UTCDateTime)


class MarketValueHistory(SQLModel, table=True):
    """One row per player, the history is a list of `[day, value]` pairs, oldest first.

    `day` counts days since 1970-01-01, exactly as Kickbase sends it.
    """
    player_id: str = Field(primary_key=True)
    points: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    synced_at: datetime = Field(default_factory=utcnow, sa_type=UTCDateTime)


class Fixture(SQLModel, table=True):
    id: str = Field(primary_key=True)
    competition_id: int = Field(default=1, index=True)
    day: int = Field(index=True)
    kickoff: datetime | None = _ts()
    team1_id: str | None = None
    team2_id: str | None = None
    team1_goals: int | None = None
    team2_goals: int | None = None
    status: int | None = None
    minute: str | None = None


### ===============================================================================
### League
### ===============================================================================

class League(SQLModel, table=True):
    id: str = Field(primary_key=True)
    name: str
    image: str | None = None
    competition_id: int = 1
    current_day: int | None = None
    number_of_days: int | None = None
    season_name: str | None = None
    market_values_updated_at: datetime | None = _ts()
    synced_at: datetime | None = _ts()


class Manager(SQLModel, table=True):
    league_id: str = Field(primary_key=True)
    id: str = Field(primary_key=True)
    name: str
    image: str | None = None
    placement: int | None = None
    points: int | None = None
    average_points: int | None = None
    team_value: int | None = _money()
    matchday_wins: int | None = None


class SquadEntry(SQLModel, table=True):
    """Which manager owns which player, and what they paid."""
    league_id: str = Field(primary_key=True)
    player_id: str = Field(primary_key=True)
    manager_id: str = Field(index=True)
    purchase_price: int | None = _money()
    market_value_gain: int | None = _money()


class MarketListing(SQLModel, table=True):
    league_id: str = Field(primary_key=True)
    player_id: str = Field(primary_key=True)
    seller_id: str | None = None
    seller_name: str | None = None
    price: int | None = _money()
    offer_count: int | None = None
    expires_at: datetime | None = _ts()
    listed_at: datetime | None = _ts()


class Transfer(SQLModel, table=True):
    """A transfer from the activity feed. Kept forever, the feed itself forgets old entries."""
    __table_args__ = (Index("ix_transfer_league_date", "league_id", "date"),)

    id: str = Field(primary_key=True)
    league_id: str
    date: datetime = Field(sa_type=UTCDateTime)
    player_id: str = Field(index=True)
    player_name: str | None = None
    team_id: str | None = None
    buyer: str | None = None
    seller: str | None = None
    price: int = _money(0)


class MatchdayRanking(SQLModel, table=True):
    league_id: str = Field(primary_key=True)
    day: int = Field(primary_key=True)
    manager_id: str = Field(primary_key=True)
    points: int | None = None
    season_points: int | None = None
    team_value: int | None = _money()
    placement: int | None = None
    final: bool = False # True once the matchday is over


class Battle(SQLModel, table=True):
    league_id: str = Field(primary_key=True)
    type: int = Field(primary_key=True)
    name: str
    description: str = ""
    sort_order: int = 0


class BattleEntry(SQLModel, table=True):
    league_id: str = Field(primary_key=True)
    type: int = Field(primary_key=True)
    manager_id: str = Field(primary_key=True)
    placement: int | None = None
    value: float | None = None


class SyncRun(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    league_id: str | None = None
    trigger: str = "schedule" # startup, schedule, login or manual
    triggered_by: str | None = None
    status: str = "running" # running, success or failed
    started_at: datetime = Field(default_factory=utcnow, sa_type=UTCDateTime, index=True)
    finished_at: datetime | None = _ts()
    requests: int = 0
    error: str | None = None
    stats: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))


### ===============================================================================
### Users
### ===============================================================================

class User(SQLModel, table=True):
    """A Kickbase account that logged, or the account from the environment."""
    id: str = Field(primary_key=True)
    name: str
    email: str | None = None
    image: str | None = None
    last_login_at: datetime | None = _ts()


class UserLeague(SQLModel, table=True):
    """Which leagues a user is in, and their real budget there. Only shown to the user themselves."""
    user_id: str = Field(primary_key=True)
    league_id: str = Field(primary_key=True, index=True)
    budget: int | None = _money()
    budget_updated_at: datetime | None = _ts()


class UserSession(SQLModel, table=True):
    """A login. The id is the SHA-256 of the cookie value, the Kickbase token is stored encrypted."""
    id: str = Field(primary_key=True)
    user_id: str = Field(index=True)
    token_encrypted: str
    token_expires_at: datetime = Field(sa_type=UTCDateTime)
    created_at: datetime = Field(default_factory=utcnow, sa_type=UTCDateTime)
    expires_at: datetime = Field(sa_type=UTCDateTime, index=True)
    last_seen_at: datetime = Field(default_factory=utcnow, sa_type=UTCDateTime)


class MarketBid(SQLModel, table=True):
    """A user's own offer for a player on the market."""
    league_id: str = Field(primary_key=True)
    user_id: str = Field(primary_key=True)
    player_id: str = Field(primary_key=True)
    price: int = _money(0)


class SchemaInfo(SQLModel, table=True):
    id: int = Field(default=1, primary_key=True)
    version: int
