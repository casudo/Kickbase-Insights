"""Live matchday points, fetched on demand.

As in Kickbase only the starting eleven counts: this reads each manager's lineup from the ranking
and the points of exactly those players from the player center.

Kickbase only has new points while a real match runs. Otherwise the last answer is kept until
somebody explicitly asks for a refresh.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta

from sqlalchemy import Engine
from sqlmodel import Session, select

from api.schemas import (
    LineupsOut,
    LiveEventOut,
    LiveManagerOut,
    LiveOut,
    LivePlayerOut,
    LiveTimelineEventOut,
    MatchOut,
    PlayerMatchesOut,
    PlayerMatchOut,
)
from core import analytics
from core.config import Settings
from db.models import Fixture, League, Manager, Player, utcnow
from kickbase import KickbaseAuthError, KickbaseClient, KickbaseError
from kickbase import models as kb

log = logging.getLogger(__name__)

EVENT_TYPES_MAX_AGE = timedelta(hours=24)
### Lineups change rarely, and only through the managers themselves
LINEUPS_MAX_AGE_SECONDS = 120
### A player's matches change once per match
MATCHES_MAX_AGE_SECONDS = 10 * 60
### Kick-off to final whistle including half time and stoppage time
MATCH_LENGTH = timedelta(minutes=115)
### A match Kickbase still reports as running this long after kick-off is not believed anymore
MAX_MATCH_LENGTH = timedelta(hours=4)


class LiveService:
    def __init__(self, settings: Settings, engine: Engine):
        self.settings = settings
        self.engine = engine
        self._cache: dict[str, tuple[float, LiveOut]] = {}
        self._lineups: dict[str, tuple[float, LineupsOut]] = {}
        ### Players looked up by the search on the live page, by (league, player)
        self._players: dict[tuple[str, str], tuple[float, LivePlayerOut]] = {}
        self._matches: dict[tuple[int, str], tuple[float, PlayerMatchesOut]] = {}
        ### Minutes played in a finished match, they do not change anymore. By (competition, player, day)
        self._minutes: dict[tuple[int, str, int], int] = {}
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

    async def get(
        self, league: League, client: KickbaseClient, viewer_id: str | None = None, refresh: bool = False
    ) -> LiveOut:
        """Live data of a league, fetched with the viewer's own token and shared by all its members.

        Kickbase is only asked again while a match runs, or when `refresh` asks for it explicitly.
        """
        result = await self._shared(league, client, refresh)
        running = await asyncio.to_thread(self.match_running, league)
        ### The cached copy is the same for everyone, only "is that me" differs
        return result.model_copy(
            update={
                "match_running": running,
                "managers": [m.model_copy(update={"is_self": m.id == viewer_id}) for m in result.managers],
            }
        )

    def match_running(self, league: League) -> bool:
        """Whether a real match of the league's competition is on, the only time new points come in.

        That is from the planned kick-off until Kickbase reports the final whistle, as a match may run
        longer than planned and Kickbase may lag behind the kick-off.
        """
        now = utcnow()
        cached = self._cache.get(league.id)
        reported = {match.id: match for match in cached[1].matches} if cached else {}
        if any(
            match.state == "running" and (match.kickoff is None or now < match.kickoff + MAX_MATCH_LENGTH)
            for match in reported.values()
        ):
            return True
        with Session(self.engine) as session:
            kicked_off = session.exec(
                select(Fixture.id).where(
                    Fixture.competition_id == league.competition_id,
                    Fixture.kickoff <= now,
                    Fixture.kickoff > now - MATCH_LENGTH,
                )
            ).all()
        ### Unless Kickbase already reported the final whistle
        return any(mid not in reported or reported[mid].state != "finished" for mid in kicked_off)

    async def _outdated(self, league: League, refresh: bool) -> bool:
        cached = self._cache.get(league.id)
        if cached is None:
            return True
        if time.monotonic() - cached[0] < self.settings.sync.live_cache_seconds:
            return False
        return refresh or await asyncio.to_thread(self.match_running, league)

    async def _shared(self, league: League, client: KickbaseClient, refresh: bool) -> LiveOut:
        if not await self._outdated(league, refresh):
            return self._cache[league.id][1]
        ### Concurrent viewers share one fetch instead of each hammering Kickbase
        async with self._lock:
            if not await self._outdated(league, refresh):
                return self._cache[league.id][1]
            result = await self._build(league, client)
            self._cache[league.id] = (time.monotonic(), result)
            return result

    async def player(self, league: League, client: KickbaseClient, player_id: str) -> LivePlayerOut:
        """Live points and events of any player of the matchday, also of those nobody fielded.
        Looked up on demand by the search, so the frontend only asks again on its own while a match runs."""
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
        await self._add_minutes(league, client, [result], day)
        self._players[(league.id, player_id)] = (time.monotonic(), result)
        return result

    async def matches(self, league: League, client: KickbaseClient, player_id: str) -> PlayerMatchesOut:
        """A player's matches of the current season: the played ones with result, minutes and points,
        and the opponents still to come."""
        key = (league.competition_id, player_id)
        cached = self._matches.get(key)
        if cached and time.monotonic() - cached[0] < MATCHES_MAX_AGE_SECONDS:
            return cached[1]
        performance, player = await asyncio.gather(
            client.player_performance(league.competition_id, player_id),
            asyncio.to_thread(self._load_player, player_id),
        )
        ### Oldest season first, the last one is the current
        season = performance.seasons[-1] if performance.seasons else None
        matches = season.matches if season else []
        ### Kickbase names the player's club only for the matches already played,
        ### the ones to come are the current club's
        last_club = next((match.team_id for match in reversed(matches) if match.team_id), None)
        club = (player.team_id if player else None) or last_club
        result = PlayerMatchesOut(
            season=season.title if season else None,
            matches=[_player_match(match, club) for match in matches],
        )
        self._matches[key] = (time.monotonic(), result)
        return result

    async def _add_minutes(
        self, league: League, client: KickbaseClient, players: list[LivePlayerOut], day: int | None
    ) -> None:
        """Fills in the minutes the players played in their finished match of the day.

        The player center only tells how long the match lasted, so the minutes come from the
        player's matches, like on the player screen. Fetched once per player and matchday.
        """
        if day is None:
            return
        played = [p for p in players if p.match_state == "finished" and p.role in ("start", "sub")]
        missing = {p.id for p in played if (league.competition_id, p.id, day) not in self._minutes}
        await asyncio.gather(*(self._load_minutes(league, client, pid, day) for pid in missing))
        for p in played:
            p.minute = self._minutes.get((league.competition_id, p.id, day))

    async def _load_minutes(self, league: League, client: KickbaseClient, player_id: str, day: int) -> None:
        try:
            result = await self.matches(league, client, player_id)
        except KickbaseAuthError:
            raise
        except KickbaseError as e:
            log.debug("No minutes played for player %s: %s", player_id, e)
            return
        match = next((m for m in result.matches if m.day == day), None)
        ### Final only once Kickbase counts the match as finished there too
        if match and match.state == "finished" and match.minutes is not None:
            self._minutes[(league.competition_id, player_id, day)] = match.minutes

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

        live_players = {
            pid: self._live_player(pid, center_by_id.get(pid), players.get(pid), team_states)
            for pid in lineup_ids
        }
        await self._add_minutes(league, client, list(live_players.values()), day)

        result_managers = []
        for user in ranking.users:
            fielded = [pid for pid in user.lineup if pid]
            lineup = [live_players[pid] for pid in fielded]
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
        timeline: list[LiveTimelineEventOut] = []
        if center:
            for event in analytics.effective_events(center.events):
                name, kind = self._event_types.get(event.type or -1, (f"Ereignis {event.type}", None))
                grouped[name].append(event.points)
                timeline.append(
                    LiveTimelineEventOut(name=name, points=event.points, minute=event.minute, kind=kind)
                )
                if kind:
                    kinds[kind] += 1

        events = [
            LiveEventOut(name=name, count=len(points), points=sum(points)) for name, points in grouped.items()
        ]
        events.sort(key=lambda e: abs(e.points), reverse=True)
        ### Stable, so events of the same minute keep Kickbase's order. Without a minute at the start
        timeline.sort(key=lambda e: e.minute if e.minute is not None else -1)

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
            role=role,
            on_field=analytics.on_field(state, role, sent_off),
            goals=kinds["goal"],
            assists=kinds["assist"],
            own_goals=kinds["own_goal"],
            yellow_cards=kinds["yellow"],
            yellow_red_cards=kinds["yellow_red"],
            red_cards=kinds["red"],
            events=events,
            timeline=timeline,
        )


def _player_match(match: kb.PerformanceMatch, club: str | None) -> PlayerMatchOut:
    """A match from the player's point of view: their club's goals first, the other club as opponent.
    `club` stands in for the player's club where Kickbase leaves it out."""
    team_id = match.team_id or club
    home = team_id is None or team_id == match.team1_id
    state = analytics.match_state(match.match_status)
    role = analytics.player_role(match.status)
    minutes = re.match(r"\d+", match.minutes or "")
    points = match.points
    if points is None and state != "upcoming" and role in ("start", "sub"):
        ### Kickbase leaves the points out when they are zero
        points = 0
    return PlayerMatchOut(
        day=match.day,
        kickoff=match.kickoff,
        opponent_id=match.team2_id if home else match.team1_id,
        home=home,
        goals=match.team1_goals if home else match.team2_goals,
        opponent_goals=match.team2_goals if home else match.team1_goals,
        points=points,
        minutes=int(minutes.group()) if minutes else None,
        role=role,
        state=state,
        current=match.current,
    )
