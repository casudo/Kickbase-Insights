"""Response models of the REST API. Serialized in camelCase for the frontend."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field
from pydantic.alias_generators import to_camel

from core import analytics
from core.analytics import MatchState, PlayerRole


class Schema(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class LeagueOut(Schema):
    id: str
    name: str
    image: str | None = None
    current_day: int | None = None
    number_of_days: int | None = None
    season_name: str | None = None
    synced_at: datetime | None = None
    market_values_updated_at: datetime | None = None


class LoginIn(Schema):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class UserOut(Schema):
    id: str
    name: str
    image: str | None = None


class MeOut(Schema):
    user: UserOut
    leagues: list[LeagueOut] # The viewer's leagues, the preferred one first


class SyncRunOut(Schema):
    id: int
    league_id: str | None = None
    trigger: str
    triggered_by: str | None = None
    status: str
    started_at: datetime
    finished_at: datetime | None = None
    requests: int = 0
    error: str | None = None
    stats: dict = {}


class SyncStatus(Schema):
    running: bool
    next_run: datetime | None = None
    last_run: SyncRunOut | None = None
    last_success_at: datetime | None = None


class StatusOut(Schema):
    version: str
    demo: bool
    authenticated: bool
    league: LeagueOut | None = None
    own_manager_id: str | None = None # The manager id of whoever is looking
    start_date: datetime | None = None
    start_money: int
    sync: SyncStatus
    live_now: bool = False # A Bundesliga match of the current matchday is running right now, judged by kick-off times
    warnings: list[str] = []


class SyncTriggerOut(Schema):
    started: bool
    reason: str | None = None


class TeamOut(Schema):
    id: str
    name: str
    image: str | None = None
    placement: int | None = None
    points: int | None = None
    matches: int | None = None
    goal_diff: int | None = None


class PlayerOut(Schema):
    id: str
    first_name: str | None = None
    last_name: str
    team_id: str | None = None
    image: str | None = None
    position: int
    status: int
    status_text: str | None = None
    market_value: int
    trend: int
    total_points: int | None = None
    average_points: int | None = None
    goals: int | None = None
    assists: int | None = None
    active: bool = True
    today: int | None = None
    yesterday: int | None = None
    two_days: int | None = None
    seven_days: int | None = None
    thirty_days: int | None = None
    owner_id: str | None = None
    purchase_price: int | None = None
    on_market: bool = False


class MarketPlayerOut(PlayerOut):
    seller_id: str | None = None
    seller_name: str | None = None
    price: int | None = None
    offer_count: int | None = None
    own_bid: int | None = None
    expires_at: datetime | None = None
    listed_at: datetime | None = None
    is_free_agent: bool = True


class TransferOut(Schema):
    id: str
    date: datetime
    player_id: str
    player_name: str | None = None
    team_id: str | None = None
    buyer: str | None = None
    buyer_id: str | None = None
    seller: str | None = None
    seller_id: str | None = None
    price: int


class PlayerDetailOut(PlayerOut):
    ### `[date, value]` pairs, oldest first
    history: list[tuple[str, int]] = []
    transfers: list[TransferOut] = []


class ManagerOut(Schema):
    id: str
    name: str
    image: str | None = None
    is_self: bool = False
    placement: int | None = None
    points: int | None = None
    points_behind: int | None = None
    average_points: int | None = None
    team_value: int | None = None
    matchday_wins: int | None = None
    budget: int | None = None # The real budget, only known for the logged in user
    estimated_balance: int | None = None
    max_bid: int | None = None
    squad_size: int = 0
    transfers: int = 0
    bought: int = 0
    sold: int = 0
    transfer_profit: int | None = None


class BattleEntryOut(Schema):
    manager_id: str
    name: str
    image: str | None = None
    placement: int | None = None
    value: float | None = None


class BattleOut(Schema):
    type: int
    name: str
    description: str = ""
    entries: list[BattleEntryOut] = []


class TurnoverOut(Schema):
    manager: str
    manager_id: str | None = None
    player_id: str
    player_name: str | None = None
    first_name: str | None = None
    image: str | None = None
    team_id: str | None = None
    position: int | None = None
    buy_price: int | None = None
    buy_date: datetime | None = None
    bought_from: str | None = None
    starter: bool = False
    sell_price: int
    sell_date: datetime
    sold_to: str | None = None
    profit: int | None = None
    days_held: int | None = None


class ChartManager(Schema):
    id: str
    name: str


class ChartOut(Schema):
    managers: list[ChartManager]
    ### One object per x value, e.g. `{"date": "2026-08-01", "<managerId>": 1200000}`
    rows: list[dict]


class MatchdayChartsOut(Schema):
    managers: list[ChartManager]
    team_values: list[dict]
    points: list[dict]
    placements: list[dict]


class MatchOut(Schema):
    id: str
    day: int
    kickoff: datetime | None = None
    team1_id: str | None = None
    team2_id: str | None = None
    team1_goals: int | None = None
    team2_goals: int | None = None
    status: int | None = None
    minute: str | None = None


class FixturesOut(Schema):
    day: int | None
    current_day: int | None
    number_of_days: int | None
    matches: list[MatchOut]


class LiveEventOut(Schema):
    name: str
    count: int
    points: int


class LivePlayerOut(Schema):
    id: str
    first_name: str | None = None
    last_name: str
    image: str | None = None
    team_id: str | None = None
    position: int = 0
    points: int = 0
    match_status: int | None = None
    match_state: MatchState = "upcoming"
    match_minute: str | None = None
    minute: int | None = None
    role: PlayerRole | None = None
    on_field: bool = False
    goals: int = 0
    assists: int = 0
    own_goals: int = 0
    yellow_cards: int = 0
    yellow_red_cards: int = 0
    red_cards: int = 0
    events: list[LiveEventOut] = []


class LiveManagerOut(Schema):
    id: str
    name: str
    image: str | None = None
    is_self: bool = False
    matchday_points: int = 0
    season_points: int | None = None
    placement: int | None = None
    players_started: int = 0
    lineup_size: int = 0
    players: list[LivePlayerOut] = []


class LiveOut(Schema):
    day: int | None
    updated_at: datetime
    matches: list[MatchOut]
    managers: list[LiveManagerOut]


class LineupsOut(Schema):
    day: int | None
    lineups: dict[str, list[str]] # Manager id -> the player ids of their current starting eleven
