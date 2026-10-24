"""Live matchday points, fetched on demand.

As in Kickbase only the starting eleven counts: this reads each manager's lineup from the ranking
and the points of exactly those players from the player center.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta

from sqlalchemy import Engine
from sqlmodel import Session, select

from api.schemas import LineupsOut, LiveEventOut, LiveManagerOut, LiveOut, LivePlayerOut, MatchOut
from core import analytics
from core.config import Settings
from db.models import League, Manager, Player
from kickbase import KickbaseAuthError, KickbaseClient, KickbaseError
from kickbase import models as kb

log = logging.getLogger(__name__)

EVENT_TYPES_MAX_AGE = timedelta(hours=24)
### Lineups change rarely, and only through the managers themselves
LINEUPS_MAX_AGE_SECONDS = 120


class LiveService:
    def __init__(self, settings: Settings, engine: Engine):
        self.settings = settings
        self.engine = engine
        self._cache: dict[str, tuple[float, LiveOut]] = {}
        self._lineups: dict[str, tuple[float, LineupsOut]] = {}
        self._lock = asyncio.Lock()
        ### event type id -> (display name, kind)
        self._event_types: dict[int, tuple[str, analytics.EventKind | None]] = {}
        self._event_types_at: datetime | None = None

    async def lineups(self, league: League, client: KickbaseClient) -> LineupsOut:
        """Every manager's current starting eleven, as the ranking of the current matchday lists it."""
        cached = self._lineups.get(league.id)
        if cached and time.monotonic() - cached[0] < LINEUPS_MAX_AGE_SECONDS:
            return cached[1]
        ranking = await client.ranking(league.id, league.current_day)
        result = LineupsOut(
            day=ranking.day or league.current_day,
            lineups={user.id: [pid for pid in user.lineup if pid] for user in ranking.users},
        )
        self._lineups[league.id] = (time.monotonic(), result)
        return result

    async def get(self, league: League, client: KickbaseClient, viewer_id: str | None = None) -> LiveOut:
        """Live data of a league, fetched with the viewer's own token and shared by all its members."""
        result = await self._shared(league, client)
        ### The cached copy is the same for everyone, only "is that me" differs
        return result.model_copy(
            update={
                "managers": [m.model_copy(update={"is_self": m.id == viewer_id}) for m in result.managers]
            }
        )

    async def _shared(self, league: League, client: KickbaseClient) -> LiveOut:
        ttl = self.settings.sync.live_cache_seconds
        cached = self._cache.get(league.id)
        if cached and time.monotonic() - cached[0] < ttl:
            return cached[1]
        ### Concurrent viewers share one fetch instead of each hammering Kickbase
        async with self._lock:
            cached = self._cache.get(league.id)
            if cached and time.monotonic() - cached[0] < ttl:
                return cached[1]
            result = await self._build(league, client)
            self._cache[league.id] = (time.monotonic(), result)
            return result

    async def _load_event_types(self, client: KickbaseClient) -> None:
        now = datetime.now(UTC)
        if self._event_types_at and now - self._event_types_at < EVENT_TYPES_MAX_AGE:
            return
        try:
            ### English names are stable enough to classify, the German ones are shown
            english, german = await asyncio.gather(client.event_types("en-US"), client.event_types("de-DE"))
        except KickbaseError as e:
            log.warning("Could not load live event types: %s", e)
            return
        display = {t.id: t.name for t in german.types}
        self._event_types = {
            t.id: (display.get(t.id) or t.name, analytics.classify_event(t.name)) for t in english.types
        }
        self._event_types_at = now

    def _load_db(self, league_id: str) -> tuple[dict[str, Player], dict[str, Manager]]:
        with Session(self.engine) as session:
            managers = {m.id: m for m in session.exec(select(Manager).where(Manager.league_id == league_id))}
            players = {p.id: p for p in session.exec(select(Player))}
        return players, managers

    async def _build(self, league: League, client: KickbaseClient) -> LiveOut:
        competition_id = league.competition_id
        players, managers = await asyncio.to_thread(self._load_db, league.id)
        matchdays, _ = await asyncio.gather(client.matchdays(competition_id), self._load_event_types(client))
        day = matchdays.current_day or league.current_day
        ranking = await client.ranking(league.id, day)

        lineup_ids = sorted({pid for user in ranking.users for pid in user.lineup if pid})
        centers = await asyncio.gather(
            *(self._player_center(client, competition_id, pid, day, league.id) for pid in lineup_ids)
        )
        center_by_id = {pid: center for pid, center in zip(lineup_ids, centers, strict=True) if center}

        result_managers = []
        for user in ranking.users:
            lineup = [
                self._live_player(pid, center_by_id.get(pid), players.get(pid)) for pid in user.lineup if pid
            ]
            lineup.sort(key=lambda p: (p.position, -p.points))
            manager = managers.get(user.id)
            result_managers.append(
                LiveManagerOut(
                    id=user.id,
                    name=user.name or (manager.name if manager else user.id),
                    image=user.image or (manager.image if manager else None),
                    ### Kickbase's own total stays authoritative, the per player sum can lag behind
                    matchday_points=user.matchday_points
                    if user.matchday_points is not None
                    else sum(p.points for p in lineup),
                    season_points=user.season_points,
                    placement=user.season_placement,
                    players_started=sum(1 for p in lineup if p.match_status),
                    lineup_size=len(lineup),
                    players=lineup,
                )
            )
        result_managers.sort(key=lambda m: m.matchday_points, reverse=True)

        current = next((group for group in matchdays.days if group.day == day), None)
        matches = [
            MatchOut(
                id=m.id,
                day=m.day or day or 0,
                kickoff=m.kickoff,
                team1_id=m.team1_id,
                team2_id=m.team2_id,
                team1_goals=m.team1_goals,
                team2_goals=m.team2_goals,
                status=m.status,
                minute=m.minute,
            )
            for m in (current.matches if current else [])
        ]
        return LiveOut(day=day, updated_at=datetime.now(UTC), matches=matches, managers=result_managers)

    async def _player_center(
        self, client: KickbaseClient, competition_id: int, player_id: str, day: int | None, league_id: str
    ):
        try:
            return await client.player_center(competition_id, player_id, day=day, league_id=league_id)
        except KickbaseAuthError:
            raise
        except KickbaseError as e:
            log.debug("No live data for player %s: %s", player_id, e)
            return None

    def _live_player(
        self, player_id: str, center: kb.PlayerCenter | None, player: Player | None
    ) -> LivePlayerOut:
        kinds: Counter[str] = Counter()
        grouped: dict[str, list[int]] = defaultdict(list)
        if center:
            for event in analytics.effective_events(center.events):
                name, kind = self._event_types.get(event.type or -1, (f"Ereignis {event.type}", None))
                grouped[name].append(event.points)
                if kind:
                    kinds[kind] += 1

        events = [
            LiveEventOut(name=name, count=len(points), points=sum(points)) for name, points in grouped.items()
        ]
        events.sort(key=lambda e: abs(e.points), reverse=True)
        return LivePlayerOut(
            id=player_id,
            first_name=player.first_name if player else None,
            last_name=(player.last_name if player else None) or (center.last_name if center else player_id),
            image=(player.image if player else None) or (center.image if center else None),
            team_id=(player.team_id if player else None) or (center.team_id if center else None),
            position=player.position if player else 0,
            points=center.points if center else 0,
            match_status=center.match_status if center else None,
            minute=center.minute if center else None,
            goals=kinds["goal"],
            assists=kinds["assist"],
            own_goals=kinds["own_goal"],
            yellow_cards=kinds["yellow"],
            yellow_red_cards=kinds["yellow_red"],
            red_cards=kinds["red"],
            events=events,
        )
