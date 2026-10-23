"""File to calculate and analyze data given by the Kickbase API."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Literal

POSITIONS = {1: "TW", 2: "ABW", 3: "MF", 4: "ANG"}

### Kickbase counts market value days from the unix epoch
EPOCH = date(1970, 1, 1)

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
    """A transfer as stored from the activity feed. `None` on either side means Kickbase."""
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

    Rows look like `{"date": "2026-08-01", "Alice": 0, "Bob": 120000}`. Sales without a known buy
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
### Balances
### ===============================================================================

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
### Live points
### ===============================================================================

EventKind = Literal["goal", "assist", "own_goal", "yellow", "yellow_red", "red"]

_EVENT_PREFIXES: list[tuple[EventKind, tuple[str, ...]]] = [
    ("own_goal", ("own goal", "eigentor")),
    ("yellow_red", ("2nd yellow", "yellow-red", "yellow red", "gelb-rot", "gelb-rote")),
    ("red", ("red card", "rote karte")),
    ("yellow", ("yellow card", "gelbe karte")),
    ("assist", ("assist (", "assist", "vorlage (", "vorlage")),
    ("goal", ("goal (", "tor (")),
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
