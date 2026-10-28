"""Fetches information from a league in Kickbase and stores it in the database.

A sync is incremental:

- the teams come from the competition table, one request
- ownership and purchase prices come from one squad request per manager
- matchday rankings that are over are stored and never fetched again
- the activity feed is only paged until the first already known entry
- player details and market value histories are only re-fetched when they can have changed

A league is synced with the token of one of its members. What only a user may see (their budget and
their bids) is refreshed for every member with an active session, two requests each.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from collections import defaultdict
from collections.abc import Awaitable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, TypeVar

from sqlalchemy import Engine, delete, update
from sqlmodel import Session, select

from core import analytics
from core.config import Settings
from db.models import (
    Battle,
    BattleEntry,
    Fixture,
    League,
    Manager,
    MarketBid,
    MarketListing,
    MarketValueHistory,
    MatchdayRanking,
    Player,
    SquadEntry,
    SyncRun,
    Team,
    Transfer,
    UserLeague,
    utcnow,
)
from kickbase import KickbaseAuthError, KickbaseClient, KickbaseError, PicturePool
from kickbase import models as kb
from sync import notify

if TYPE_CHECKING:
    from auth.accounts import Accounts, Viewer

log = logging.getLogger(__name__)

T = TypeVar("T")

### Used when the league overview does not list its battles
FALLBACK_BATTLES = [
    kb.OverviewBattle(t=4, n="Saubermann", d="Die meisten Punkte mit dem Torwart"),
    kb.OverviewBattle(t=5, n="Abwehrbollwerk", d="Die meisten Punkte mit Abwehrspielern"),
    kb.OverviewBattle(t=6, n="Fädenzieher", d="Die meisten Punkte mit Mittelfeldspielern"),
    kb.OverviewBattle(t=7, n="Angriffslustig", d="Die meisten Punkte mit Angreifern"),
    kb.OverviewBattle(t=8, n="Punktejäger", d="Die meisten Punkte an einem Spieltag"),
]

TRANSFER_FEED_TYPE = 15
### Market value histories are refreshed at least this often, even if Kickbase reports no update
HISTORY_MAX_AGE = timedelta(hours=20)
KEEP_SYNC_RUNS = 500


@dataclass
class PlayerState:
    status: int
    details_synced_at: datetime | None
    history_synced_at: datetime | None
    image: str | None = None


@dataclass
class FetchResult:
    league: kb.LeagueInfo
    competition_id: int
    user_id: str
    table: kb.CompetitionTable
    matchdays: kb.Matchdays
    overview: kb.LeagueOverview
    market: kb.Market
    budget: int | None
    profiles: list[kb.TeamProfile]
    squads: list[kb.ManagerSquad]
    dashboards: dict[str, kb.ManagerDashboard]
    battles: list[tuple[kb.OverviewBattle, kb.BattleUsers]]
    rankings: dict[int, kb.Ranking]
    current_day: int | None
    feed: list[kb.FeedItem]
    details: dict[str, kb.PlayerDetails]
    histories: dict[str, list[list[int]]]
    ### The picture of every player, see SyncService._pictures
    images: dict[str, str | None] = field(default_factory=dict)
    failures: list[str] = field(default_factory=list)


def competition_id_of(league: kb.LeagueInfo) -> int:
    try:
        return int(league.competition_id)
    except (TypeError, ValueError):
        return 1 # The Bundesliga


class SyncService:
    def __init__(
        self, settings: Settings, engine: Engine, accounts: Accounts, pictures: PicturePool | None = None
    ):
        self.settings = settings
        self.engine = engine
        self.accounts = accounts
        self.pictures = pictures
        self._locks: dict[str, asyncio.Lock] = {}
        self._active = 0
        self._idle = asyncio.Event()
        self._idle.set()
        self._closed = False
        self.last_manual_trigger: dict[str, datetime] = {}

    def running(self, league_id: str | None = None) -> bool:
        if league_id is None:
            return any(lock.locked() for lock in self._locks.values())
        lock = self._locks.get(league_id)
        return lock is not None and lock.locked()

    async def shutdown(self, grace_seconds: float = 60) -> None:
        """Refuse new syncs and wait for running ones.

        A sync writes from a worker thread, which cancelling the task cannot stop. Closing the database
        underneath it would crash the process, so it gets to finish first.
        """
        self._closed = True
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(self._idle.wait(), grace_seconds)

    async def run(
        self,
        league_id: str,
        client: KickbaseClient,
        trigger: str = "schedule",
        triggered_by: str | None = None,
    ) -> SyncRun | None:
        """Sync one league. Returns None if it is already being synced."""
        if self._closed:
            return None
        lock = self._locks.setdefault(league_id, asyncio.Lock())
        if lock.locked():
            log.info("League %s is already being synced, skipping the %s trigger", league_id, trigger)
            return None

        async with lock:
            self._active += 1
            self._idle.clear()
            try:
                return await self._run(league_id, client, trigger, triggered_by)
            finally:
                self._active -= 1
                if self._active == 0:
                    self._idle.set()

    async def run_all(self, trigger: str, stale_after: timedelta | None = None) -> list[SyncRun]:
        """Sync every league somebody can sync, one after the other.

        With `stale_after`, leagues synced more recently than that are skipped.
        """
        targets = await asyncio.to_thread(self.accounts.sync_targets)
        if stale_after is not None:
            fresh = await asyncio.to_thread(self._fresh_leagues, stale_after)
            targets = [(league_id, client) for league_id, client in targets if league_id not in fresh]
        runs = []
        for league_id, client in targets:
            run = await self.run(league_id, client, trigger)
            if run:
                runs.append(run)
        return runs

    async def sync_for_viewer(self, viewer: Viewer, client: KickbaseClient) -> None:
        """After a login: sync leagues without fresh data, refresh the user's own data in the rest."""
        stale_after = timedelta(minutes=self.settings.sync.startup_if_older_than_minutes)
        fresh = await asyncio.to_thread(self._fresh_leagues, stale_after)
        for league_id in viewer.league_ids:
            if league_id in fresh:
                await self.refresh_personal(league_id, client)
            else:
                await self.run(league_id, client, "login", viewer.name)

    def _fresh_leagues(self, max_age: timedelta) -> set[str]:
        cutoff = utcnow() - max_age
        with Session(self.engine) as session:
            return set(
                session.exec(
                    select(League.id).where(League.synced_at.is_not(None), League.synced_at > cutoff)
                )
            )

    async def refresh_personal(self, league_id: str, client: KickbaseClient) -> bool:
        """Fetch what only this user can see: their budget and their own bids."""
        try:
            user = await client.ensure_login()
            budget, market = await asyncio.gather(client.own_budget(league_id), client.market(league_id))
        except KickbaseAuthError:
            await asyncio.to_thread(self.accounts.forget_client, client)
            return False
        except KickbaseError as e:
            log.warning("Could not refresh the private data of a user in league %s: %s", league_id, e)
            return False
        await asyncio.to_thread(self._store_personal, league_id, user.id, budget.budget, market)
        return True

    async def _run(
        self, league_id: str, client: KickbaseClient, trigger: str, triggered_by: str | None
    ) -> SyncRun:
        run_id = await asyncio.to_thread(self._start_run, league_id, trigger, triggered_by)
        requests_before = client.request_count
        started = time.monotonic()
        stats: dict = {}
        league_name = league_id
        try:
            result = await self._fetch(league_id, client)
            league_name = result.league.name or league_id
            stats = await asyncio.to_thread(self._store, result)

            members = await asyncio.to_thread(self.accounts.member_clients, league_id, result.user_id)
            refreshed = [await self.refresh_personal(league_id, member) for member in members]
            stats["members_refreshed"] = sum(refreshed)
            status, error = "success", None
        except KickbaseAuthError as e:
            ### The session behind this client is over, the user has to log in again
            await asyncio.to_thread(self.accounts.forget_client, client)
            log.warning("Sync of league %s failed, the session is no longer valid", league_id)
            status, error = "failed", f"{type(e).__name__}: {e}"
        except Exception as e:
            log.exception("Sync of league %s failed", league_id)
            status, error = "failed", f"{type(e).__name__}: {e}"
            await notify.discord(self._webhook, f"Sync von {league_name} fehlgeschlagen", error, notify.RED)

        ### Collect the bonus for the configured account, even if the league sync failed
        if client is self.accounts.service and self.settings.kickbase.collect_bonus:
            await self._collect_bonus(client)

        stats["duration_seconds"] = round(time.monotonic() - started, 1)
        requests = client.request_count - requests_before
        run = await asyncio.to_thread(self._finish_run, run_id, status, error, requests, stats)
        log.info(
            "Sync of %s %s after %.1fs with %d requests",
            league_name,
            status,
            stats["duration_seconds"],
            requests,
        )
        return run

    @property
    def _webhook(self) -> str | None:
        hook = self.settings.kickbase.discord_webhook
        return hook.get_secret_value() if hook else None

    ### ============================================================================================
    ### Fetching
    ### ============================================================================================

    async def _optional(self, coro: Awaitable[T], what: str, failures: list[str]) -> T | None:
        """Await a request whose failure should not abort the whole sync."""
        try:
            return await coro
        except KickbaseAuthError:
            raise
        except KickbaseError as e:
            log.warning("Could not fetch %s: %s", what, e)
            failures.append(what)
            return None

    async def _fetch(self, league_id: str, client: KickbaseClient) -> FetchResult:
        failures: list[str] = []

        user = await client.ensure_login()
        league = next((info for info in await client.leagues() if info.id == league_id), None)
        if league is None:
            raise KickbaseError(f"{user.name or user.id} is no longer a member of league {league_id}.")
        competition_id = competition_id_of(league)
        log.info("Syncing league '%s' (%s)", league.name, league_id)

        table, matchdays, overview, market, budget = await asyncio.gather(
            client.competition_table(competition_id),
            client.matchdays(competition_id),
            client.league_overview(league_id),
            client.market(league_id),
            self._optional(client.own_budget(league_id), "own budget", failures),
        )
        team_ids = [team.id for team in table.teams if team.id]
        if not team_ids:
            raise KickbaseError("The competition table is empty, cannot discover the teams.")

        current_day = matchdays.current_day or market.day
        manager_ids = [manager.id for manager in overview.managers]
        battle_types = overview.battles or FALLBACK_BATTLES
        final_days, known_transfers, player_state = await asyncio.to_thread(self._load_state, league_id)
        days = [day for day in range(1, (current_day or 0) + 1) if day not in final_days]

        profiles, squads, dashboards, battles, rankings, feed = await asyncio.gather(
            asyncio.gather(*(client.team_profile(competition_id, tid) for tid in team_ids)),
            asyncio.gather(*(client.manager_squad(league_id, mid) for mid in manager_ids)),
            asyncio.gather(
                *(
                    self._optional(client.manager_dashboard(league_id, mid), f"dashboard {mid}", failures)
                    for mid in manager_ids
                )
            ),
            asyncio.gather(
                *(
                    self._optional(client.battle(league_id, b.type), f"battle {b.type}", failures)
                    for b in battle_types
                )
            ),
            asyncio.gather(
                *(self._optional(client.ranking(league_id, day), f"ranking {day}", failures) for day in days)
            ),
            client.feed_until(league_id, known_transfers),
        )

        ### Every player that shows up anywhere, with their current status
        statuses: dict[str, int] = {}
        for profile in profiles:
            for player in profile.players:
                statuses[player.id] = player.status
        for squad in squads:
            for player in squad.players:
                statuses.setdefault(player.id, player.status)
        for player in market.players:
            statuses.setdefault(player.id, player.status)

        now = utcnow()
        details_max_age = timedelta(hours=self.settings.sync.player_details_max_age_hours)
        market_ids = {player.id for player in market.players}
        mv_updated = market.market_values_updated_at

        need_details = [
            pid
            for pid, status in statuses.items()
            if pid in market_ids or _details_stale(player_state.get(pid), status, now, details_max_age)
        ]
        need_history = [pid for pid in statuses if _history_stale(player_state.get(pid), mv_updated, now)]
        log.info(
            "%d players, refreshing %d details and %d market value histories",
            len(statuses),
            len(need_details),
            len(need_history),
        )

        def history_days(pid: str) -> int:
            ### The first fetch reaches back a full year, afterwards a quarter is plenty to merge
            state = player_state.get(pid)
            return 92 if state and state.history_synced_at else 365

        details_list, history_list = await asyncio.gather(
            asyncio.gather(
                *(
                    self._optional(client.player(competition_id, pid), f"player {pid}", failures)
                    for pid in need_details
                )
            ),
            asyncio.gather(
                *(
                    self._optional(
                        client.market_value_history(competition_id, pid, history_days(pid)),
                        f"history {pid}",
                        failures,
                    )
                    for pid in need_history
                )
            ),
        )

        details = {d.id or pid: d for pid, d in zip(need_details, details_list, strict=True) if d}
        images = await self._pictures(profiles, squads, market, details, player_state)

        return FetchResult(
            league=league,
            competition_id=competition_id,
            user_id=user.id,
            table=table,
            matchdays=matchdays,
            overview=overview,
            market=market,
            budget=budget.budget if budget else None,
            profiles=list(profiles),
            squads=list(squads),
            dashboards={d.id or mid: d for mid, d in zip(manager_ids, dashboards, strict=True) if d},
            battles=[(b, users) for b, users in zip(battle_types, battles, strict=True) if users],
            rankings={day: r for day, r in zip(days, rankings, strict=True) if r},
            current_day=current_day,
            feed=feed,
            details=details,
            histories={
                pid: [[p.day, p.value] for p in h.points]
                for pid, h in zip(need_history, history_list, strict=True)
                if h
            },
            images=images,
            failures=failures,
        )

    async def _pictures(
        self,
        profiles: list[kb.TeamProfile],
        squads: list[kb.ManagerSquad],
        market: kb.Market,
        details: dict[str, kb.PlayerDetails],
        state: dict[str, PlayerState],
    ) -> dict[str, str | None]:
        """One picture per player: their own photo from Kickbase, else a portrait from the picture
        pool, else the club's placeholder. See analytics.choose_player_images."""
        sources = [
            ### The most specific endpoint first
            (0, [(pid, d.image) for pid, d in details.items()]),
            (1, [(entry.id, entry.image) for squad in squads for entry in squad.players]),
            (2, [(entry.id, entry.image) for entry in market.players]),
            (3, [(entry.id, entry.image) for profile in profiles for entry in profile.players]),
        ]
        candidates: dict[str, list[tuple[int, str]]] = defaultdict(list)
        seen: set[str] = set()
        for priority, entries in sources:
            for pid, path in entries:
                seen.add(pid)
                if path:
                    candidates[pid].append((priority, path))

        chosen = analytics.choose_player_images(candidates, {pid: s.image for pid, s in state.items()})
        without_photo = [pid for pid in seen if not (pid in chosen and chosen[pid].photo)]
        pooled = await self.pictures.find(without_photo) if self.pictures and without_photo else {}
        log.info(
            "Pictures: %d players with a photo, %d of them new from the picture pool, %d with a placeholder",
            len(seen) - len(without_photo) + len(pooled),
            len(pooled),
            len(without_photo) - len(pooled),
        )
        images = {pid: choice.path for pid, choice in chosen.items()}
        images.update(pooled)
        return images

    async def _collect_bonus(self, client: KickbaseClient) -> None:
        try:
            gift = await client.collect_bonus()
        except KickbaseError as e:
            log.info("No login bonus collected: %s", e)
            return
        items = gift.get("it") or [] if isinstance(gift, dict) else []
        if not items:
            log.info("The login bonus has already been collected")
            return
        first = items[0]
        log.info("Collected the login bonus in %s", first.get("lnm", "a league"))
        await notify.discord(
            self._webhook,
            "Kickbase Bonus abgeholt",
            f"Betrag: {first.get('v', '?')}\nStufe: {first.get('day', '?')}",
        )

    ### ============================================================================================
    ### Database
    ### ============================================================================================

    def _load_state(self, league_id: str) -> tuple[set[int], set[str], dict[str, PlayerState]]:
        with Session(self.engine) as session:
            final_days = set(
                session.exec(
                    select(MatchdayRanking.day)
                    .where(MatchdayRanking.league_id == league_id, MatchdayRanking.final == True)  # noqa: E712
                    .distinct()
                )
            )
            known_transfers = set(session.exec(select(Transfer.id).where(Transfer.league_id == league_id)))
            histories = dict(
                session.exec(select(MarketValueHistory.player_id, MarketValueHistory.synced_at)).all()
            )
            state = {
                pid: PlayerState(status, details_at, histories.get(pid), image)
                for pid, status, details_at, image in session.exec(
                    select(Player.id, Player.status, Player.details_synced_at, Player.image)
                ).all()
            }
        return final_days, known_transfers, state

    def _start_run(self, league_id: str, trigger: str, triggered_by: str | None) -> int:
        with Session(self.engine) as session:
            run = SyncRun(league_id=league_id, trigger=trigger, triggered_by=triggered_by)
            session.add(run)
            session.commit()
            assert run.id is not None
            return run.id

    def _finish_run(self, run_id: int, status: str, error: str | None, requests: int, stats: dict) -> SyncRun:
        with Session(self.engine) as session:
            run = session.get(SyncRun, run_id)
            assert run is not None
            run.status = status
            run.error = error
            run.requests = requests
            run.stats = stats
            run.finished_at = utcnow()
            session.add(run)

            ### Keep the run log from growing forever
            old = session.exec(select(SyncRun.id).order_by(SyncRun.id.desc()).offset(KEEP_SYNC_RUNS)).all()
            if old:
                session.exec(delete(SyncRun).where(SyncRun.id.in_(old)))
            session.commit()
            session.refresh(run)
            return run

    def _store_personal(self, league_id: str, user_id: str, budget: int | None, market: kb.Market) -> None:
        with Session(self.engine) as session:
            _write_personal(session, league_id, user_id, budget, market)
            session.commit()

    def _store(self, r: FetchResult) -> dict:
        now = utcnow()
        league_id = r.league.id
        competition_id = r.competition_id

        with Session(self.engine) as session:
            ### Teams
            teams = {t.id: t for t in session.exec(select(Team))}
            for entry in r.table.teams:
                team = teams.get(entry.id) or Team(id=entry.id, name=entry.name)
                team.competition_id = competition_id
                team.name = entry.name or team.name
                team.image = entry.image or team.image
                team.placement = entry.placement
                team.points = entry.points
                team.matches = entry.matches
                team.goal_diff = entry.goal_diff
                team.updated_at = now
                session.add(team)

            ### Players
            players = {p.id: p for p in session.exec(select(Player))}

            def player(pid: str) -> Player:
                if pid not in players:
                    players[pid] = Player(id=pid)
                return players[pid]

            seen: set[str] = set()
            for profile in r.profiles:
                for entry in profile.players:
                    p = player(entry.id)
                    p.team_id = entry.team_id or profile.id
                    p.last_name = entry.last_name or p.last_name
                    p.position = entry.position
                    p.status = entry.status
                    p.market_value = entry.market_value
                    p.market_value_trend = entry.market_value_trend
                    p.average_points = entry.average_points
                    p.active = True
                    p.updated_at = now
                    seen.add(entry.id)

            ### Players that left the competition but are still owned, or listed on the market
            for squad in r.squads:
                for entry in squad.players:
                    if entry.id in seen:
                        continue
                    p = player(entry.id)
                    p.team_id = entry.team_id or p.team_id
                    p.last_name = entry.last_name or p.last_name
                    p.position = entry.position
                    p.status = entry.status
                    p.market_value = entry.market_value
                    p.market_value_trend = entry.market_value_trend
                    p.average_points = entry.average_points
                    p.total_points = entry.points if entry.points is not None else p.total_points
                    p.active = False
                    p.updated_at = now
                    seen.add(entry.id)
            for entry in r.market.players:
                if entry.id in seen:
                    continue
                p = player(entry.id)
                p.team_id = entry.team_id or p.team_id
                p.first_name = entry.first_name or p.first_name
                p.last_name = entry.last_name or p.last_name
                p.position = entry.position
                p.status = entry.status
                p.market_value = entry.market_value
                p.market_value_trend = entry.market_value_trend
                p.average_points = entry.average_points
                p.total_points = entry.total_points
                p.updated_at = now
                seen.add(entry.id)

            for pid, details in r.details.items():
                p = player(pid)
                p.first_name = details.first_name or p.first_name
                p.last_name = details.last_name or p.last_name
                ### The note is only meaningful while the player is not fit
                p.status_text = (details.status_text or "").strip() or None if details.status else None
                p.total_points = details.total_points
                p.average_points = (
                    details.average_points if details.average_points is not None else p.average_points
                )
                p.goals = details.goals
                p.assists = details.assists
                p.details_synced_at = now

            for pid, path in r.images.items():
                if pid in players:
                    players[pid].image = path

            for pid, p in players.items():
                if pid not in seen:
                    p.active = False
                session.add(p)

            ### Market value histories
            stored = (
                {
                    h.player_id: h
                    for h in session.exec(
                        select(MarketValueHistory).where(MarketValueHistory.player_id.in_(list(r.histories)))
                    )
                }
                if r.histories
                else {}
            )
            for pid, points in r.histories.items():
                history = stored.get(pid) or MarketValueHistory(player_id=pid)
                history.points = analytics.merge_history(history.points or [], points)
                history.synced_at = now
                session.add(history)

            ### Fixtures
            fixtures = {
                f.id: f for f in session.exec(select(Fixture).where(Fixture.competition_id == competition_id))
            }
            for group in r.matchdays.days:
                for match in group.matches:
                    if not match.id:
                        continue
                    fixture = fixtures.get(match.id) or Fixture(
                        id=match.id, competition_id=competition_id, day=group.day
                    )
                    fixture.day = match.day or group.day
                    fixture.kickoff = match.kickoff
                    fixture.team1_id = match.team1_id
                    fixture.team2_id = match.team2_id
                    fixture.team1_goals = match.team1_goals
                    fixture.team2_goals = match.team2_goals
                    fixture.status = match.status
                    fixture.minute = match.minute
                    session.add(fixture)

            ### League
            current_ranking = r.rankings.get(r.current_day) if r.current_day else None
            league = session.get(League, league_id) or League(id=league_id, name=r.league.name)
            league.name = r.overview.name or r.league.name
            league.image = r.league.image or league.image
            league.competition_id = competition_id
            league.current_day = r.current_day
            if current_ranking:
                league.number_of_days = current_ranking.number_of_days or league.number_of_days
                league.season_name = current_ranking.season_name or league.season_name
            league.market_values_updated_at = r.market.market_values_updated_at
            league.synced_at = now
            session.add(league)

            ### Managers, rebuilt from scratch so people who left the league disappear
            session.exec(delete(Manager).where(Manager.league_id == league_id))
            ranking_by_id = {u.id: u for u in current_ranking.users} if current_ranking else {}
            for entry in r.overview.managers:
                dashboard = r.dashboards.get(entry.id)
                ranked = ranking_by_id.get(entry.id)
                session.add(
                    Manager(
                        league_id=league_id,
                        id=entry.id,
                        name=entry.name,
                        image=entry.image,
                        placement=_first(
                            dashboard and dashboard.placement, ranked and ranked.season_placement
                        ),
                        points=_first(dashboard and dashboard.total_points, ranked and ranked.season_points),
                        average_points=dashboard.average_points if dashboard else None,
                        team_value=_first(dashboard and dashboard.team_value, ranked and ranked.team_value),
                        matchday_wins=dashboard.matchday_wins if dashboard else None,
                    )
                )

            ### Ownership
            session.exec(delete(SquadEntry).where(SquadEntry.league_id == league_id))
            for squad in r.squads:
                for entry in squad.players:
                    session.add(
                        SquadEntry(
                            league_id=league_id,
                            player_id=entry.id,
                            manager_id=squad.id,
                            purchase_price=entry.purchase_price,
                            market_value_gain=entry.market_value_gain,
                        )
                    )

            ### Market
            session.exec(delete(MarketListing).where(MarketListing.league_id == league_id))
            for entry in r.market.players:
                session.add(
                    MarketListing(
                        league_id=league_id,
                        player_id=entry.id,
                        seller_id=entry.seller.id if entry.seller else None,
                        seller_name=entry.seller.name if entry.seller else None,
                        price=entry.price,
                        offer_count=entry.offer_count,
                        expires_at=now + timedelta(seconds=entry.expires_in)
                        if entry.expires_in is not None
                        else None,
                        listed_at=entry.listed_at,
                    )
                )

            ### What only the syncing user can see
            _write_personal(session, league_id, r.user_id, r.budget, r.market)

            ### Battles
            session.exec(delete(BattleEntry).where(BattleEntry.league_id == league_id))
            session.exec(delete(Battle).where(Battle.league_id == league_id))
            for order, (battle, users) in enumerate(r.battles):
                session.add(
                    Battle(
                        league_id=league_id,
                        type=battle.type,
                        name=battle.name,
                        description=battle.description,
                        sort_order=order,
                    )
                )
                for entry in users.entries:
                    if entry.user.id:
                        session.add(
                            BattleEntry(
                                league_id=league_id,
                                type=battle.type,
                                manager_id=entry.user.id,
                                placement=entry.placement,
                                value=entry.value,
                            )
                        )

            ### Matchday rankings
            for day, ranking in r.rankings.items():
                session.exec(
                    delete(MatchdayRanking).where(
                        MatchdayRanking.league_id == league_id, MatchdayRanking.day == day
                    )
                )
                for entry in ranking.users:
                    session.add(
                        MatchdayRanking(
                            league_id=league_id,
                            day=day,
                            manager_id=entry.id,
                            points=entry.matchday_points,
                            season_points=entry.season_points,
                            team_value=entry.team_value,
                            placement=entry.matchday_placement,
                            final=r.current_day is not None and day < r.current_day,
                        )
                    )

            ### Transfers
            new_transfers = 0
            for item in r.feed:
                data = item.data
                if item.type != TRANSFER_FEED_TYPE or item.date is None or "pi" not in data:
                    continue
                session.add(
                    Transfer(
                        id=item.id,
                        league_id=league_id,
                        date=item.date,
                        player_id=str(data["pi"]),
                        player_name=data.get("pn"),
                        team_id=str(data["tid"]) if data.get("tid") is not None else None,
                        buyer=data.get("byr") or None,
                        seller=data.get("slr") or None,
                        price=int(data.get("trp") or 0),
                    )
                )
                new_transfers += 1

            session.commit()

        return {
            "league": r.league.name,
            "players": len(seen),
            "player_details_fetched": len(r.details),
            "histories_fetched": len(r.histories),
            "rankings_fetched": len(r.rankings),
            "new_transfers": new_transfers,
            "failed_requests": len(r.failures),
        }


def _write_personal(
    session: Session, league_id: str, user_id: str, budget: int | None, market: kb.Market
) -> None:
    """Store a user's real budget and their own bids. Nobody else ever gets to see them."""
    membership = session.get(UserLeague, (user_id, league_id)) or UserLeague(
        user_id=user_id, league_id=league_id
    )
    if budget is not None:
        membership.budget = budget
        membership.budget_updated_at = utcnow()
    session.add(membership)

    session.exec(delete(MarketBid).where(MarketBid.league_id == league_id, MarketBid.user_id == user_id))
    for entry in market.players:
        bid = entry.own_bid(user_id)
        if bid is not None:
            session.add(MarketBid(league_id=league_id, user_id=user_id, player_id=entry.id, price=bid))


def _first(*values):
    for value in values:
        if value is not None and value is not False:
            return value
    return None


def _details_stale(state: PlayerState | None, status: int, now: datetime, max_age: timedelta) -> bool:
    if state is None or state.details_synced_at is None:
        return True
    if state.status != status:
        return True
    return now - state.details_synced_at > max_age


def _history_stale(state: PlayerState | None, market_values_updated: datetime | None, now: datetime) -> bool:
    if state is None or state.history_synced_at is None:
        return True
    if market_values_updated is not None and state.history_synced_at < market_values_updated:
        return True
    return now - state.history_synced_at > HISTORY_MAX_AGE


def mark_interrupted_runs(engine: Engine) -> None:
    """Runs still marked as running when the app starts were interrupted by a restart."""
    with Session(engine) as session:
        session.exec(
            update(SyncRun)
            .where(SyncRun.status == "running")
            .values(status="failed", error="Interrupted by a restart", finished_at=utcnow())
        )
        session.commit()
