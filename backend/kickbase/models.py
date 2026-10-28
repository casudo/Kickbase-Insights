"""Map JSON keys to readable names from the Kickbase API v4 responses.

Kickbase answers with very short keys (`mv`, `mvt`, `prc`, ...). Every model below maps them to
readable names through aliases and ignores everything it does not know. All fields have defaults,
so a key Kickbase stops sending degrades a single value instead of failing the whole sync.

For more info: https://github.com/kevinskyba/kickbase-api-doc
Kickbase itself does not document its API publicly.

NOTE THAT NOT ALL FIELDS IN THE RESPONSE ARE NEEDED AND THEREFORE ONLY THE RELEVANT ONES ARE MAPPED BELOW.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

### ===============================================================================
### Helpers
### ===============================================================================

def _to_str(value: Any) -> Any:
    return str(value) if isinstance(value, int) else value


def _lenient_datetime(value: Any) -> datetime | None:
    """Kickbase sometimes sends placeholders like `1970-00-00T00:00:00Z`. Those become None."""
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


Id = Annotated[str, BeforeValidator(_to_str)]
Timestamp = Annotated[datetime | None, BeforeValidator(_lenient_datetime)]

### ===============================================================================
### Base model for Kickbase API responses
### ===============================================================================

class KBModel(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


### ===============================================================================
### User
### ===============================================================================

class LoginUser(KBModel):
    id: Id = ""
    name: str = ""
    email: str | None = None
    image: str | None = Field(None, alias="uim")


class LoginResponse(KBModel):
    user: LoginUser = Field(default_factory=LoginUser, alias="u")
    token: str = Field("", alias="tkn")
    token_expiry: Timestamp = Field(None, alias="tknex")


### ===============================================================================
### Leagues
### ===============================================================================

CLASSIC_GAME_MODE = 1 # 'gpm' parameter. 1 Classic, 3 Rush, 4 Arena


class LeagueInfo(KBModel):
    """An entry of `/v4/leagues/selection`."""
    id: Id = Field("", alias="i")
    name: str = Field("", alias="n")
    ### The real league: 1 Bundesliga, 2 2. Bundesliga, 3 La Liga, 4 Frauen-Bundesliga, 9 MLS
    competition_id: Id = Field("1", alias="cpi")
    game_mode: int = Field(CLASSIC_GAME_MODE, alias="gpm")
    budget: int | None = Field(None, alias="b")
    team_value: int | None = Field(None, alias="tv")
    placement: int | None = Field(None, alias="pl")
    image: str | None = Field(None, alias="lim")

    @property
    def supported(self) -> bool:
        return self.game_mode == CLASSIC_GAME_MODE


class OverviewManager(KBModel):
    id: Id = Field("", alias="i")
    name: str = Field("", alias="n")
    image: str | None = Field(None, alias="uim")


class OverviewBattle(KBModel):
    type: int = Field(0, alias="t")
    name: str = Field("", alias="n")
    description: str = Field("", alias="d")


class LeagueOverview(KBModel):
    """`/v4/leagues/{leagueId}/overview?includeManagersAndBattles=true`"""
    id: Id = Field("", alias="i")
    name: str = Field("", alias="lnm")
    competition_id: Id = Field("1", alias="cpi")
    start_budget: int | None = Field(None, alias="b")
    managers: list[OverviewManager] = Field(default_factory=list, alias="us")
    battles: list[OverviewBattle] = Field(default_factory=list, alias="btls")


class Budget(KBModel):
    """`/v4/leagues/{leagueId}/me/budget`, the logged in user's real budget."""
    budget: int | None = Field(None, alias="b")


class ManagerDashboard(KBModel):
    """`/v4/leagues/{leagueId}/managers/{managerId}/dashboard`"""
    id: Id = Field("", alias="u")
    name: str = Field("", alias="unm")
    image: str | None = Field(None, alias="uim")
    average_points: int | None = Field(None, alias="ap")
    total_points: int | None = Field(None, alias="tp")
    matchday_wins: int | None = Field(None, alias="mdw")
    placement: int | None = Field(None, alias="pl")
    team_value: int | None = Field(None, alias="tv")


class SquadPlayer(KBModel):
    id: Id = Field("", alias="pi")
    last_name: str = Field("", alias="pn")
    team_id: Id | None = Field(None, alias="tid")
    position: int = Field(0, alias="pos")
    status: int = Field(0, alias="st")
    points: int | None = Field(None, alias="p")
    average_points: int | None = Field(None, alias="ap")
    market_value: int = Field(0, alias="mv")
    market_value_trend: int = Field(0, alias="mvt")
    market_value_change: int | None = Field(None, alias="sdmvt")
    purchase_price: int | None = Field(None, alias="prc") # What the manager paid. For players assigned at the season start this is their value back then.
    market_value_gain: int | None = Field(None, alias="mvgl")
    image: str | None = Field(None, alias="pim")


class ManagerSquad(KBModel):
    """`/v4/leagues/{leagueId}/managers/{managerId}/squad`"""
    id: Id = Field("", alias="u")
    name: str = Field("", alias="unm")
    image: str | None = Field(None, alias="uim")
    players: list[SquadPlayer] = Field(default_factory=list, alias="it")


class BattleUser(KBModel):
    id: Id = Field("", alias="i")
    name: str = Field("", alias="n")
    image: str | None = Field(None, alias="uim")


class BattleEntry(KBModel):
    user: BattleUser = Field(default_factory=BattleUser, alias="u")
    placement: int | None = Field(None, alias="pl")
    value: float | None = Field(None, alias="v")


class BattleUsers(KBModel):
    """`/v4/leagues/{leagueId}/battles/{type}/users`"""
    entries: list[BattleEntry] = Field(default_factory=list, alias="us")


class RankingUser(KBModel):
    id: Id = Field("", alias="i")
    name: str = Field("", alias="n")
    image: str | None = Field(None, alias="uim")
    season_points: int | None = Field(None, alias="sp")
    matchday_points: int | None = Field(None, alias="mdp")
    team_value: int | None = Field(None, alias="tv")
    season_placement: int | None = Field(None, alias="spl")
    matchday_placement: int | None = Field(None, alias="mdpl")
    lineup: list[Id | None] = Field(default_factory=list, alias="lp") # Player IDs of the S11


class Ranking(KBModel):
    """`/v4/leagues/{leagueId}/ranking?dayNumber=N`"""
    users: list[RankingUser] = Field(default_factory=list, alias="us")
    day: int | None = None
    number_of_days: int | None = Field(None, alias="nd")
    season_name: str | None = Field(None, alias="sn")


class MarketOffer(KBModel):
    id: Id | None = Field(None, alias="i")
    user_id: Id | None = Field(None, alias="u")
    owner_id: Id | None = Field(None, alias="uoid")
    price: int | None = Field(None, alias="uop")


class MarketSeller(KBModel):
    id: Id | None = Field(None, alias="i")
    name: str | None = Field(None, alias="n")


class MarketPlayer(KBModel):
    id: Id = Field("", alias="i")
    first_name: str | None = Field(None, alias="fn")
    last_name: str = Field("", alias="n")
    team_id: Id | None = Field(None, alias="tid")
    position: int = Field(0, alias="pos")
    status: int = Field(0, alias="st")
    market_value: int = Field(0, alias="mv")
    market_value_trend: int = Field(0, alias="mvt")
    total_points: int | None = Field(None, alias="p")
    average_points: int | None = Field(None, alias="ap")
    offer_count: int | None = Field(None, alias="ofc")
    expires_in: int | None = Field(None, alias="exs")
    seller: MarketSeller | None = Field(None, alias="u")
    price: int | None = Field(None, alias="prc")
    offers: list[MarketOffer] = Field(default_factory=list, alias="ofs")
    own_offer_user_id: Id | None = Field(None, alias="uoid")
    own_offer_price: int | None = Field(None, alias="uop")
    listed_at: Timestamp = Field(None, alias="dt")
    image: str | None = Field(None, alias="pim")

    def own_bid(self, own_user_id: str) -> int | None:
        """What the logged in user currently bids for this player, if anything.

        "ofs" is read first, the "uoid"/"uop" mirror on the item itself is the fallback because some
        items only carry that.
        """
        for offer in self.offers:
            bidder = offer.user_id or offer.owner_id
            if bidder is not None and bidder == own_user_id:
                return offer.price
        if self.own_offer_user_id is not None and self.own_offer_user_id == own_user_id:
            return self.own_offer_price
        return None

    def own_offer_id(self, own_user_id: str) -> str | None:
        """The id of the logged in user's offer, needed to withdraw it."""
        for offer in self.offers:
            bidder = offer.user_id or offer.owner_id
            if bidder is not None and bidder == own_user_id:
                return offer.id
        return None


class Market(KBModel):
    """`/v4/leagues/{leagueId}/market`"""
    players: list[MarketPlayer] = Field(default_factory=list, alias="it")
    market_values_updated_at: Timestamp = Field(None, alias="mvud")
    day: int | None = None


class FeedItem(KBModel):
    """An entry of `/v4/leagues/{leagueId}/activitiesFeed`.

    Known types: 3 player listed by Kickbase, 5 user joined, 15 transfer, 17 matchday result,
    22 login bonus, 26 achievement. For type 15 `data` holds `byr` (buyer name), `slr` (seller name),
    `pi`/`pn` (player id/name), `tid` (team) and `trp` (price).
    """
    id: Id = Field("", alias="i")
    type: int = Field(0, alias="t")
    date: Timestamp = Field(None, alias="dt")
    data: dict[str, Any] = Field(default_factory=dict)


class FeedPage(KBModel):
    items: list[FeedItem] = Field(default_factory=list, alias="af")


### ===============================================================================
### Competitions
### ===============================================================================

class TableTeam(KBModel):
    """An entry of `/v4/competitions/{competitionId}/table`."""
    id: Id = Field("", alias="tid")
    name: str = Field("", alias="tn")
    image: str | None = Field(None, alias="tim")
    points: int | None = Field(None, alias="cp")
    placement: int | None = Field(None, alias="cpl")
    matches: int | None = Field(None, alias="mc")
    goal_diff: int | None = Field(None, alias="gd")


class CompetitionTable(KBModel):
    teams: list[TableTeam] = Field(default_factory=list, alias="it")


class Match(KBModel):
    id: Id = Field("", alias="mi")
    day: int = 0
    kickoff: Timestamp = Field(None, alias="dt")
    team1_id: Id | None = Field(None, alias="t1")
    team2_id: Id | None = Field(None, alias="t2")
    team1_symbol: str | None = Field(None, alias="t1sy")
    team2_symbol: str | None = Field(None, alias="t2sy")
    team1_goals: int | None = Field(None, alias="t1g")
    team2_goals: int | None = Field(None, alias="t2g")
    status: int | None = Field(None, alias="st") # 0 upcoming, 1 running, 2 finished
    minute: str | None = Field(None, alias="mtd")
    team1_image: str | None = Field(None, alias="t1im")
    team2_image: str | None = Field(None, alias="t2im")


class MatchdayGroup(KBModel):
    day: int = 0
    matches: list[Match] = Field(default_factory=list, alias="it")


class Matchdays(KBModel):
    """`/v4/competitions/{competitionId}/matchdays`"""
    current_day: int | None = Field(None, alias="day")
    days: list[MatchdayGroup] = Field(default_factory=list, alias="it")


class TeamProfilePlayer(KBModel):
    id: Id = Field("", alias="i")
    last_name: str = Field("", alias="n")
    team_id: Id | None = Field(None, alias="tid")
    position: int = Field(0, alias="pos")
    status: int = Field(0, alias="st")
    market_value: int = Field(0, alias="mv")
    market_value_trend: int = Field(0, alias="mvt")
    market_value_change: int | None = Field(None, alias="sdmvt")
    average_points: int | None = Field(None, alias="ap")
    image: str | None = Field(None, alias="pim")


class TeamProfile(KBModel):
    """`/v4/competitions/{competitionId}/teams/{teamId}/teamprofile`"""
    id: Id = Field("", alias="tid")
    name: str = Field("", alias="tn")
    players: list[TeamProfilePlayer] = Field(default_factory=list, alias="it")


class PlayerDetails(KBModel):
    """`/v4/competitions/{competitionId}/players/{playerId}`"""
    id: Id = Field("", alias="i")
    first_name: str | None = Field(None, alias="fn")
    last_name: str = Field("", alias="ln")
    team_id: Id | None = Field(None, alias="tid")
    position: int = Field(0, alias="pos")
    status: int = Field(0, alias="st")
    status_text: str | None = Field(None, alias="stxt") # Localized injury or suspension note, e.g. "Muskuläre Probleme"
    total_points: int | None = Field(None, alias="tp")
    average_points: int | None = Field(None, alias="ap")
    goals: int | None = Field(None, alias="g")
    assists: int | None = Field(None, alias="a")
    yellow_cards: int | None = Field(None, alias="y")
    red_cards: int | None = Field(None, alias="r")
    seconds_played: int | None = Field(None, alias="sec")
    shirt_number: int | None = Field(None, alias="shn")
    market_value: int | None = Field(None, alias="mv")
    market_value_trend: int | None = Field(None, alias="mvt")
    image: str | None = Field(None, alias="pim")


class MarketValuePoint(KBModel):
    ### Days since 1970-01-01
    day: int = Field(0, alias="dt")
    value: int = Field(0, alias="mv")


class MarketValueHistory(KBModel):
    """`/v4/competitions/{competitionId}/players/{playerId}/marketValue/{days}`"""
    points: list[MarketValuePoint] = Field(default_factory=list, alias="it")


class LiveEvent(KBModel):
    id: Id | None = Field(None, alias="ei")
    type: int | None = Field(None, alias="eti")
    points: int = Field(0, alias="p")
    minute: int | None = Field(None, alias="mt")
    ### Set on a correction: the id of the event this one cancels out
    corrects: Id | None = Field(None, alias="cei")


class PlayerCenter(KBModel):
    """`/v4/competitions/{competitionId}/playercenter/{playerId}` - live points of one player."""
    id: Id = Field("", alias="i")
    team_id: Id | None = Field(None, alias="tid")
    last_name: str = Field("", alias="n")
    team1_id: Id | None = Field(None, alias="t1")
    team2_id: Id | None = Field(None, alias="t2")
    team1_goals: int | None = Field(None, alias="t1g")
    team2_goals: int | None = Field(None, alias="t2g")
    points: int = Field(0, alias="p")
    status: int | None = Field(None, alias="st")
    minute: int | None = Field(None, alias="mt")
    kickoff: Timestamp = Field(None, alias="md")
    match_status: int | None = Field(None, alias="mst")
    match_minute: str | None = Field(None, alias="mtd")
    events: list[LiveEvent] = Field(default_factory=list)
    image: str | None = Field(None, alias="pim")


class EventType(KBModel):
    id: int = Field(0, alias="i")
    name: str = Field("", alias="ti")


class EventTypes(KBModel):
    """`/v4/live/eventtypes`"""
    types: list[EventType] = Field(default_factory=list, alias="it")


class PerformanceMatch(KBModel):
    """One match of a player, played or still to come."""
    day: int | None = Field(None, alias="day")
    points: int | None = Field(None, alias="p") # Left out when the player scored nothing
    minutes: str | None = Field(None, alias="mp") # Minutes played, e.g. "92'"
    kickoff: Timestamp = Field(None, alias="md")
    team1_id: Id | None = Field(None, alias="t1")
    team2_id: Id | None = Field(None, alias="t2")
    team1_goals: int | None = Field(None, alias="t1g")
    team2_goals: int | None = Field(None, alias="t2g")
    team_id: Id | None = Field(None, alias="pt") # The player's club at the time
    status: int | None = Field(None, alias="st") # The player's part, see analytics.PLAYER_ROLES
    match_status: int | None = Field(None, alias="mdst")
    current: bool = Field(False, alias="cur")


class PerformanceSeason(KBModel):
    title: str | None = Field(None, alias="ti")
    competition: str | None = Field(None, alias="n")
    matches: list[PerformanceMatch] = Field(default_factory=list, alias="ph")


class PlayerPerformance(KBModel):
    """`/v4/competitions/{competitionId}/players/{playerId}/performance`, oldest season first"""
    seasons: list[PerformanceSeason] = Field(default_factory=list, alias="it")

