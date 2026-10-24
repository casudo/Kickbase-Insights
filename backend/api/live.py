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
        ### Players looked up by the search on the live page, by (league, player)
        self._players: dict[tuple[str, str], tuple[float, LivePlayerOut]] = {}
        ### Codes Kickbase sent that are not documented, each logged once so they can be looked into
        self._unknown_codes: set[tuple[str, int]] = set()
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

    async def player(self, league: League, client: KickbaseClient, player_id: str) -> LivePlayerOut:
        """Live points and events of any player of the matchday, also of those nobody fielded."""
        ttl = self.settings.sync.live_cache_seconds
        now = time.monotonic()
        self._players = {key: entry for key, entry in self._players.items() if now - entry[0] < ttl}
        cached = self._players.get((league.id, player_id))
        if cached:
            return cached[1]
        shared = self._cache.get(league.id)
        day = (shared[1].day if shared else None) or league.current_day
        player, _ = await asyncio.gather(
            asyncio.to_thread(self._load_player, player_id), self._load_event_types(client)
        )
        center = await self._player_center(client, league.competition_id, player_id, day, league.id)
        team_states = {}
        if shared:
            for match in shared[1].matches:
                team_states[match.team1_id] = team_states[match.team2_id] = match.state
        result = self._live_player(player_id, center, player, team_states)
        self._players[(league.id, player_id)] = (time.monotonic(), result)
        return result

    def _load_player(self, player_id: str) -> Player | None:
        with Session(self.engine) as session:
            return session.get(Player, player_id)

    def _note_code(self, kind: str, code: int | None, known: set[int]) -> None:
        if code is None or code in known or (kind, code) in self._unknown_codes:
            return
        self._unknown_codes.add((kind, code))
        log.info("Kickbase sent the undocumented %s code %s", kind, code)

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
        team_states = {}
        for match in matches:
            self._note_code("match status", match.status, analytics.KNOWN_MATCH_CODES)
            team_states[match.team1_id] = team_states[match.team2_id] = match.state

        result_managers = []
        for user in ranking.users:
            fielded = [pid for pid in user.lineup if pid]
            lineup = [
                self._live_player(pid, center_by_id.get(pid), players.get(pid), team_states)
                for pid in fielded
            ]
            lineup.sort(key=lambda p: (p.position, -p.points))
            manager = managers.get(user.id)
            ### Kickbase updates the totals of the ranking with a delay, the points of the players are live.
            ### Their sum is what the manager gets, as long as every one of them could be fetched.
            live_sum = sum(p.points for p in lineup)
            complete = all(pid in center_by_id for pid in fielded)
            matchday_points = live_sum if complete or user.matchday_points is None else user.matchday_points
            season_points = user.season_points
            if season_points is not None and user.matchday_points is not None:
                season_points += matchday_points - user.matchday_points
            result_managers.append(
                LiveManagerOut(
                    id=user.id,
                    name=user.name or (manager.name if manager else user.id),
                    image=user.image or (manager.image if manager else None),
                    matchday_points=matchday_points,
                    season_points=season_points,
                    placement=user.season_placement,
                    players_started=sum(1 for p in lineup if p.match_state != "upcoming"),
                    players_on_field=sum(1 for p in lineup if p.on_field),
                    lineup_size=len(lineup),
                    players=lineup,
                )
            )
        result_managers.sort(key=lambda m: m.matchday_points, reverse=True)

        return LiveOut(
            day=day,
            updated_at=datetime.now(UTC),
            cache_seconds=self.settings.sync.live_cache_seconds,
            matches=matches,
            managers=result_managers,
        )

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
        self,
        player_id: str,
        center: kb.PlayerCenter | None,
        player: Player | None,
        team_states: dict[str | None, analytics.MatchState],
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

        team_id = (player.team_id if player else None) or (center.team_id if center else None)
        if center:
            self._note_code("match status", center.match_status, analytics.KNOWN_MATCH_CODES)
            self._note_code("player status", center.status, analytics.KNOWN_PLAYER_CODES)
        state = analytics.later_state(
            analytics.match_state(center.match_status, center.match_minute) if center else None,
            team_states.get(team_id),
        )
        role = analytics.player_role(center.status if center else None)
        sent_off = kinds["red"] + kinds["yellow_red"] > 0
        return LivePlayerOut(
            id=player_id,
            first_name=player.first_name if player else None,
            last_name=(player.last_name if player else None) or (center.last_name if center else player_id),
            image=(player.image if player else None) or (center.image if center else None),
            team_id=team_id,
            position=player.position if player else 0,
            points=center.points if center else 0,
            match_status=center.match_status if center else None,
            match_state=state,
            match_minute=center.match_minute if center else None,
            minute=center.minute if center else None,
            role=role,
            on_field=analytics.on_field(state, role, sent_off),
            goals=kinds["goal"],
            assists=kinds["assist"],
            own_goals=kinds["own_goal"],
            yellow_cards=kinds["yellow"],
            yellow_red_cards=kinds["yellow_red"],
            red_cards=kinds["red"],
            events=events,
        )
