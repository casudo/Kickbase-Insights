"""File to calculate and analyze data given by the Kickbase API."""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from statistics import mean, median
from typing import Literal
from zoneinfo import ZoneInfo

POSITIONS = {1: "TW", 2: "ABW", 3: "MF", 4: "ANG"}

### Kickbase counts market value days from the unix epoch
EPOCH = date(1970, 1, 1)

### Kickbase sets the market values at 22:00 German time and files them under that day
MARKET_VALUE_TIMEZONE = ZoneInfo("Europe/Berlin")
MARKET_VALUE_UPDATE_HOUR = 22

### ===============================================================================
### Helper functions
### ===============================================================================


def day_number(value: date | datetime) -> int:
    if isinstance(value, datetime):
        value = value.astimezone(UTC).date()
    return (value - EPOCH).days


def day_to_date(day: int) -> date:
    return EPOCH + timedelta(days=day)


### ===============================================================================
### Market values
### ===============================================================================


def market_value_deltas(points: Sequence[Sequence[int]]) -> dict[str, int | None]:
    """How much a market value moved over the usual periods.

    `points` is the history as `[day, value]` pairs, oldest first, one entry per day. A delta the
    history is too short for is None: a player who just joined the competition has only a few entries.
    """
    values = [value for _, value in points]

    def delta(newer: int, older: int) -> int | None:
        if len(values) < abs(older):
            return None
        return values[newer] - values[older]

    return {
        "today": delta(-1, -2),
        "yesterday": delta(-2, -3),
        "two_days": delta(-3, -4),
        "seven_days": delta(-1, -8),
        "thirty_days": delta(-1, -31),
    }


def value_on_day(points: Sequence[Sequence[int]], day: int) -> int | None:
    """The market value on `day`, or on the closest earlier day the history has."""
    result = None
    for point_day, value in points:
        if point_day > day:
            break
        result = value
    return result


def market_value_day(moment: datetime) -> int:
    """The history day whose market value is in force at `moment`.

    A day's entry only takes effect with that evening's update, until then the one before still counts.
    """
    local = moment.astimezone(MARKET_VALUE_TIMEZONE).replace(tzinfo=None)
    return day_number((local - timedelta(hours=MARKET_VALUE_UPDATE_HOUR)).date())


def last_market_value_update(moment: datetime) -> datetime:
    """The latest market value update at or before `moment`.

    It comes from the clock because Kickbase only tells when the next update is due (`mvud`).
    """
    local = moment.astimezone(MARKET_VALUE_TIMEZONE)
    update = local.replace(hour=MARKET_VALUE_UPDATE_HOUR, minute=0, second=0, microsecond=0)
    if update > local:
        ### Moves the local date, so it stays 22:00 when the clocks change
        update -= timedelta(days=1)
    return update.astimezone(UTC)


def merge_history(
    existing: Iterable[Sequence[int]], new: Iterable[Sequence[int]], keep_days: int = 730
) -> list[list[int]]:
    """Combine a stored history with freshly fetched points. New values win on the same day."""
    by_day = {int(day): int(value) for day, value in existing}
    by_day.update({int(day): int(value) for day, value in new})
    if not by_day:
        return []
    cutoff = max(by_day) - keep_days
    return [[day, by_day[day]] for day in sorted(by_day) if day >= cutoff]


### ===============================================================================
### Player pictures
### ===============================================================================


@dataclass(frozen=True)
class PictureChoice:
    path: str | None
    photo: bool # False for the club's placeholder or no picture at all


def choose_player_images(
    candidates: dict[str, list[tuple[int, str]]], stored: dict[str, str | None]
) -> dict[str, PictureChoice]:
    """Pick one picture per player from everything a sync saw.

    `candidates` maps a player to `(priority, path)` pairs, a lower priority meaning a more specific
    endpoint. Without a photo Kickbase sends the club's placeholder (a mannequin in the kit), the same
    path for every such player. A path shared by several players is therefore a placeholder, while a
    player's own photo belongs to them alone and wins over any placeholder. A photo stored by an
    earlier sync is kept when this one only saw placeholders.
    """
    players_by_path: dict[str, set[str]] = defaultdict(set)
    for player_id, entries in candidates.items():
        for _, path in entries:
            players_by_path[path].add(player_id)
    ### A placeholder an earlier sync stored for several players is one, even if this sync did not see it
    for player_id, path in stored.items():
        if path:
            players_by_path[path].add(player_id)

    def placeholder(path: str) -> bool:
        return len(players_by_path.get(path, ())) > 1

    result: dict[str, PictureChoice] = {}
    for player_id in set(candidates) | set(stored):
        entries = sorted(candidates.get(player_id, []))
        photos = [path for _, path in entries if not placeholder(path)]
        current = stored.get(player_id)
        if photos:
            result[player_id] = PictureChoice(photos[0], photo=True)
        elif current and not placeholder(current):
            result[player_id] = PictureChoice(current, photo=True)
        elif entries:
            result[player_id] = PictureChoice(entries[0][1], photo=False)
        else:
            result[player_id] = PictureChoice(current, photo=False)
    return result


### ===============================================================================
### Transfers
### ===============================================================================


@dataclass(frozen=True)
class TransferRecord:
    """A transfer as stored. `None` on either side means Kickbase."""
    id: str
    date: datetime
    player_id: str
    player_name: str | None
    team_id: str | None
    buyer: str | None
    seller: str | None
    price: int


@dataclass(frozen=True)
class TransferEvent:
    """One side of a transfer, from the point of view of a single manager."""
    manager: str
    kind: Literal["buy", "sell"]
    player_id: str
    player_name: str | None
    team_id: str | None
    price: int
    date: datetime
    counterparty: str | None # The other side, None for Kickbase


@dataclass(frozen=True)
class Turnover:
    manager: str
    player_id: str
    player_name: str | None
    team_id: str | None
    buy_price: int | None
    buy_date: datetime | None
    bought_from: str | None
    starter: bool # Assigned at the season start instead of bought
    sell_price: int
    sell_date: datetime
    sold_to: str | None

    @property
    def profit(self) -> int | None:
        return None if self.buy_price is None else self.sell_price - self.buy_price

    @property
    def days_held(self) -> int | None:
        return None if self.buy_date is None else max(0, (self.sell_date - self.buy_date).days)


def transfers_since(transfers: Iterable[TransferRecord], start: datetime | None) -> list[TransferRecord]:
    """Drop transfers from before a league reset. The boundary is inclusive."""
    items = sorted(transfers, key=lambda t: (t.date, t.id))
    return items if start is None else [t for t in items if t.date >= start]


def transfer_events(transfers: Iterable[TransferRecord]) -> list[TransferEvent]:
    """Split every transfer into the buy and sell it means for the managers involved.

    A sale between two managers is a sale for one and a purchase for the other.
    """
    events: list[TransferEvent] = []
    for t in transfers_since(transfers, None):
        if t.seller:
            events.append(
                TransferEvent(
                    t.seller, "sell", t.player_id, t.player_name, t.team_id, t.price, t.date, t.buyer
                )
            )
        if t.buyer:
            events.append(
                TransferEvent(
                    t.buyer, "buy", t.player_id, t.player_name, t.team_id, t.price, t.date, t.seller
                )
            )
    return events


def pair_turnovers(
    events: Iterable[TransferEvent],
    starter_price: Callable[[str], int | None],
    season_start: datetime | None,
) -> list[Turnover]:
    """Match every sale with the purchase it closes.

    A sale without a preceding purchase by the same manager is a player that was assigned at the
    season start. Its buy price is the market value back then, as `starter_price` reports it.
    """
    open_buys: dict[tuple[str, str], list[TransferEvent]] = defaultdict(list)
    turnovers: list[Turnover] = []

    for event in events:
        key = (event.manager, event.player_id)
        if event.kind == "buy":
            open_buys[key].append(event)
            continue

        if open_buys[key]:
            buy = open_buys[key].pop(0)
            turnovers.append(
                Turnover(
                    manager=event.manager,
                    player_id=event.player_id,
                    player_name=event.player_name or buy.player_name,
                    team_id=event.team_id or buy.team_id,
                    buy_price=buy.price,
                    buy_date=buy.date,
                    bought_from=buy.counterparty,
                    starter=False,
                    sell_price=event.price,
                    sell_date=event.date,
                    sold_to=event.counterparty,
                )
            )
        else:
            turnovers.append(
                Turnover(
                    manager=event.manager,
                    player_id=event.player_id,
                    player_name=event.player_name,
                    team_id=event.team_id,
                    buy_price=starter_price(event.player_id),
                    buy_date=season_start,
                    bought_from=None,
                    starter=True,
                    sell_price=event.price,
                    sell_date=event.date,
                    sold_to=event.counterparty,
                )
            )
    return turnovers


def cumulative_profit_rows(
    turnovers: Iterable[Turnover], managers: Sequence[str], start: date, end: date
) -> list[dict]:
    """Chart rows of the summed transfer profit per manager, one row per day something changed.

    Rows look like `{"date": "2026-08-01", "1001": 0, "1002": 120000}`. Sales without a known buy
    price are left out.
    """
    daily: dict[date, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for turnover in turnovers:
        if turnover.profit is None or turnover.manager not in managers:
            continue
        daily[turnover.sell_date.astimezone(UTC).date()][turnover.manager] += turnover.profit

    totals = dict.fromkeys(managers, 0)
    rows = [{"date": start.isoformat(), **totals}]
    for day in sorted(d for d in daily if start <= d <= end):
        for manager, profit in daily[day].items():
            totals[manager] += profit
        rows.append({"date": day.isoformat(), **totals})
    if rows[-1]["date"] != end.isoformat():
        rows.append({"date": end.isoformat(), **totals})
    return rows


### ===============================================================================
### Overpay
### ===============================================================================

### The suggested bids outbid these shares of the comparable purchases
BID_QUANTILES = (0.5, 0.75, 0.9)
### Fewer purchases than this are too little to suggest a bid from
MIN_COMPARABLE = 8
### Two players are comparable up to this factor between their market values
SIMILAR_VALUE_FACTOR = 2
BID_STEP = 1000


@dataclass(frozen=True)
class Purchase:
    """A purchase from Kickbase."""
    transfer: TransferRecord
    market_value: int

    @property
    def overpay(self) -> int:
        return self.transfer.price - self.market_value

    @property
    def overpay_share(self) -> float:
        return self.overpay / self.market_value


@dataclass(frozen=True)
class OverpayStats:
    purchases: int
    median: float
    average: float
    total: int
    average_amount: int # per purchase
    highest: float


@dataclass(frozen=True)
class BidAdvice:
    amounts: list[int] # The suggested bids, lowest first
    comparable: list[float] # The overpay shares they come from, lowest first
    similar: bool # players of a similar market value


def kickbase_purchases(
    transfers: Iterable[TransferRecord], history: Callable[[str], Sequence[Sequence[int]]]
) -> list[Purchase]:
    """Every purchase from Kickbase, only sales where the highest bid wins."""
    purchases = []
    for transfer in transfers:
        if not transfer.buyer or transfer.seller or not transfer.price:
            continue
        value = value_on_day(history(transfer.player_id), market_value_day(transfer.date))
        if value:
            purchases.append(Purchase(transfer, value))
    return purchases


def overpay_stats(purchases: Sequence[Purchase]) -> OverpayStats:
    """Summarizes at least one purchase."""
    shares = [p.overpay_share for p in purchases]
    total = sum(p.overpay for p in purchases)
    return OverpayStats(
        purchases=len(shares),
        median=median(shares),
        average=mean(shares),
        total=total,
        average_amount=round(total / len(shares)),
        highest=max(shares),
    )


def bid_advice(purchases: Sequence[Purchase], market_value: int) -> BidAdvice | None:
    """Suggests bids for a player of `market_value` based on comparable purchases."""
    if market_value <= 0:
        return None
    lowest, highest = market_value / SIMILAR_VALUE_FACTOR, market_value * SIMILAR_VALUE_FACTOR
    similar = [p.overpay_share for p in purchases if lowest <= p.market_value <= highest]
    enough_similar = len(similar) >= MIN_COMPARABLE
    shares = sorted(similar if enough_similar else (p.overpay_share for p in purchases))
    if len(shares) < MIN_COMPARABLE:
        return None
    ### Kickbase takes no bids below the market value
    amounts = [
        math.ceil(market_value * (1 + max(0, shares[int(q * len(shares))])) / BID_STEP) * BID_STEP
        for q in BID_QUANTILES
    ]
    return BidAdvice(amounts, shares, enough_similar)


### ===============================================================================
### Fair value
### ===============================================================================

### The fair value answers one question: WHAT DO PLAYERS ACTUALLY COST?
### It compares players with each other at one moment, so it is no forecast. It only knows points,
### position and market value. It knows nothing about injuries, rivals for a place or trends.
###
### 1. Find the regular players (`games_played()`, `regular_games()`)
###    Kickbase sends no number of games, so it is total points / average points. A player needs two
###    thirds of the games of the busiest player, and at least 3. Rotation players cost far less than
###    their average points suggest, so they would all look cheap.
###
###    Example: The busiest player has 8 games, so everyone needs ceil(8 * 2 / 3) = 6 games.
###             717 total points / 120 average = 6 games: this player is rated.
###             400 total points / 100 average = 4 games: this player gets no fair value.
###
### 2. Fit one curve through the regular players (`fair_curve()`, `least_squares()`)
###    The curve gives the logarithm of the market value, because values grow by percent and not by a
###    fixed amount:
###
###        log(value) = position offset + a * x + b * x^2 + c * x^3      with x = average points / 100
###
###    `least_squares()` finds the numbers that fit all regular players best. All positions share a, b
###    and c, only the offset is different. One position alone can be too small for its own curve: in
###    this league only 15 goalkeepers play regularly.
###
###    Example: a = 3.45, b = -1.26, c = 0.18
###             Offsets: goalkeeper 13.90, defender 14.12, midfielder 14.20, forward 14.34
###
### 3. Stop the curve from falling (`fair_curve()`)
###    There are few top players, so a curve can bend down at its end. But more points must never mean
###    a lower value, so the curve may only go up or stay level.
###
### 4. Read the fair value (`FairCurve.value()`)
###    Example: A midfielder with 100 average points, so x = 1:
###             log(value) = 14.20 + 3.45 * 1 - 1.26 * 1 + 0.18 * 1 = 16.57
###             value = e^16.57 = 15.7 million
###
###    The whole curve of this league, in millions:
###
###        Average points    Goalkeeper    Defender    Midfielder    Forward
###                    50           4.5         5.7           6.1        7.0
###                   100          11.6        14.5          15.7       18.0
###                   150          20.8        26.0          28.1       32.2
###                   200          29.9        37.3          40.3       46.3
###
### 5. Compare it with the market value (`fair_rating()`)
###    gap = market value / fair value - 1. The curve is about 20% off for a typical player, so a small
###    gap means nothing. Only a gap of at least 25% counts as cheap or expensive.
###
###    Example: A midfielder with a fair value of 15.7 million:
###             Market value 10.0 million: 10.0 / 15.7 - 1 = -36%, cheap
###             Market value 14.0 million: 14.0 / 15.7 - 1 = -11%, fair
###             Market value 22.0 million: 22.0 / 15.7 - 1 = +40%, expensive
###
### A big gap is no buying advice. When a market value falls fast, the market often knows more than
### the points do, for example that a player lost their place in the team.

### A player must have played this share of the matchdays. Rotation players cost far less than their
### average points suggest, so they would all look cheap.
REGULAR_SHARE = 2 / 3
MIN_GAMES = 3
### Too few regular players to fit a curve
MIN_FAIR_PLAYERS = 30
### The curve is about 20% off for a typical player, so only a bigger gap means something
FAIR_BAND = 0.25

FairRating = Literal["cheap", "fair", "expensive"]


@dataclass(frozen=True)
class FairInput:
    position: int
    average_points: int
    market_value: int


@dataclass(frozen=True)
class FairCurve:
    """The usual market value for a number of points. One shape, moved up or down per position."""
    offsets: dict[int, float] # By position, as a logarithm
    low: int # The lowest points the curve knows
    shape: list[float] # One value per point from `low` on, as a logarithm. It never falls.

    def value(self, position: int, points: int) -> int:
        index = min(max(points - self.low, 0), len(self.shape) - 1)
        return round(math.exp(self.offsets[position] + self.shape[index]))

    def line(self, position: int, step: int = 5) -> list[tuple[int, int]]:
        """`(points, value)` pairs to draw the curve of a position."""
        top = self.low + len(self.shape) - 1
        return [(points, self.value(position, points)) for points in (*range(self.low, top, step), top)]


def games_played(total_points: int | None, average_points: int | None) -> int:
    """Kickbase sends no number of games, but it follows from the total and the average points."""
    if not total_points or not average_points or average_points <= 0:
        return 0
    return round(total_points / average_points)


def regular_games(games: Iterable[int]) -> int:
    """How many games make a regular player, going by whoever played the most so far."""
    return max(MIN_GAMES, math.ceil(max(games, default=0) * REGULAR_SHARE))


def least_squares(rows: Sequence[Sequence[float]], targets: Sequence[float]) -> list[float] | None:
    """The best fit of `rows` to `targets`. None when the data cannot decide it."""
    size = len(rows[0])
    matrix = [
        [sum(row[i] * row[j] for row in rows) for j in range(size)]
        + [sum(row[i] * target for row, target in zip(rows, targets, strict=True))]
        for i in range(size)
    ]
    for column in range(size):
        pivot = max(range(column, size), key=lambda index: abs(matrix[index][column]))
        if abs(matrix[pivot][column]) < 1e-9:
            return None
        matrix[column], matrix[pivot] = matrix[pivot], matrix[column]
        for index in range(size):
            if index != column:
                factor = matrix[index][column] / matrix[column][column]
                for part in range(column, size + 1):
                    matrix[index][part] -= factor * matrix[column][part]
    return [matrix[index][size] / matrix[index][index] for index in range(size)]


def _powers(points: int) -> list[float]:
    x = points / 100
    return [x, x**2, x**3]


def fair_curve(players: Sequence[FairInput]) -> FairCurve | None:
    """Fits the market value of regular players to their average points.

    All positions share one shape, because a single position can be too small for it: only a few
    goalkeepers play every match. None when there are too few players.
    """
    if len(players) < MIN_FAIR_PLAYERS:
        return None
    positions = sorted({player.position for player in players})
    rows = [
        [float(player.position == position) for position in positions] + _powers(player.average_points)
        for player in players
    ]
    solution = least_squares(rows, [math.log(player.market_value) for player in players])
    if solution is None:
        return None
    slopes = solution[len(positions) :]
    low = min(player.average_points for player in players)
    high = max(player.average_points for player in players)
    ### More points must never mean a lower value, so the curve only ever goes up or stays
    shape: list[float] = []
    for points in range(low, high + 1):
        value = sum(slope * power for slope, power in zip(slopes, _powers(points), strict=True))
        shape.append(max(value, shape[-1]) if shape else value)
    return FairCurve(dict(zip(positions, solution, strict=False)), low, shape)


def fair_rating(gap: float) -> FairRating:
    """`gap` is the market value against the fair value, -0.3 means 30% below it."""
    return "cheap" if gap <= -FAIR_BAND else "expensive" if gap >= FAIR_BAND else "fair"


### ===============================================================================
### Balances
### ===============================================================================

### Only used until Kickbase has reported the start money of a league
DEFAULT_START_MONEY = 50_000_000


def estimate_balance(manager: str, events: Iterable[TransferEvent], start_money: int) -> int:
    """Start money minus purchases plus sales. Login bonuses and achievements are not visible."""
    balance = start_money
    for event in events:
        if event.manager != manager:
            continue
        balance += event.price if event.kind == "sell" else -event.price
    return balance


def max_bid(balance: int, team_value: int) -> int:
    """The highest bid a manager can place.

    The debt limit is a third of the team value including the balance.
    """
    debt_limit = (team_value + balance) * 0.33
    bid = debt_limit + balance if balance < 0 else debt_limit
    return max(0, round(bid))


### ===============================================================================
### Matches
### ===============================================================================

MatchState = Literal["upcoming", "running", "finished"]
PlayerRole = Literal["start", "sub", "bench"]

MATCH_UPCOMING, MATCH_FINISHED = 0, 2
KNOWN_MATCH_CODES = {0, 1, 2}

PLAYER_ROLES: dict[int, PlayerRole] = {5: "start", 3: "sub", 4: "bench"}
KNOWN_PLAYER_CODES = {0, 3, 4, 5}
_STATE_ORDER: dict[MatchState, int] = {"upcoming": 0, "running": 1, "finished": 2}


def match_state(status: int | None, minute: str | int | None = None) -> MatchState:
    if status == MATCH_FINISHED:
        return "finished"
    if status is not None and status != MATCH_UPCOMING:
        return "running"
    ### Without a telling code, a match clock still shows that the match runs
    return "running" if str(minute or "").strip() not in ("", "0") else "upcoming"


def later_state(*states: MatchState | None) -> MatchState:
    """The furthest of several reports on the same match, as one source may lag behind the other."""
    known = [state for state in states if state]
    return max(known, key=_STATE_ORDER.__getitem__) if known else "upcoming"


def player_role(status: int | None) -> PlayerRole | None:
    return PLAYER_ROLES.get(status) if status is not None else None


def on_field(state: MatchState, role: PlayerRole | None, sent_off: bool) -> bool:
    """Whether a player is on the pitch right now. A starter who was substituted stays on it here,
    Kickbase's live data does not tell that apart."""
    return state == "running" and role in ("start", "sub") and not sent_off


### ===============================================================================
### Live points
### ===============================================================================

EventKind = Literal["goal", "assist", "own_goal", "yellow", "yellow_red", "red"]

_EVENT_PREFIXES: list[tuple[EventKind, tuple[str, ...]]] = [
    ("own_goal", ("own goal", "eigentor")),
    ("yellow_red", ("2nd yellow", "yellow-red", "yellow red", "gelb-rot", "gelb-rote")),
    ("red", ("red card", "rote karte")),
    ("yellow", ("yellow card", "gelbe karte")),
    ("assist", ("assist (", "assist", "vorlage (", "vorlage")),
    ("goal", ("goal (", "tor (", "penalty scored", "elfmeter verwandelt")),
]


def classify_event(name: str) -> EventKind | None:
    """Map an (English) Kickbase event type name onto the few kinds the live view counts."""
    lowered = name.strip().lower()
    if lowered in ("goal", "tor"):
        return "goal"
    for kind, prefixes in _EVENT_PREFIXES:
        if lowered.startswith(prefixes):
            ### "Own Goal forced" is a bonus for the attacker, not an own goal
            if kind == "own_goal" and "forced" in lowered:
                return None
            return kind
    return None


def effective_events(events: Sequence) -> list:
    """Events minus everything Kickbase corrected afterwards.

    A correction carries the id of the event it cancels in `corrects`. Both sides are dropped.
    """
    cancelled = {e.corrects for e in events if e.corrects}
    return [e for e in events if not e.corrects and e.id not in cancelled]
