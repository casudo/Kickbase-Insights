"""REST API consumed by the frontend.

Every data endpoint needs a viewer: a logged in user (the `kbi_session` cookie), or with
KBI_AUTH__REQUIRE_LOGIN=false the account from the environment. A viewer only gets to see the leagues
their Kickbase account is in, chosen with the `league` query parameter.
"""

from __future__ import annotations

import asyncio
import secrets
from collections.abc import Callable, Coroutine, Iterator
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from sqlalchemy import Engine
from sqlmodel import Session, select

from api.insights import Insights
from api.live import LiveService
from api.schemas import (
    BattleOut,
    ChartOut,
    FixturesOut,
    LeagueOut,
    LineupsOut,
    LiveOut,
    LoginIn,
    ManagerOut,
    MarketPlayerOut,
    MatchdayChartsOut,
    MeOut,
    PlayerDetailOut,
    PlayerOut,
    StatusOut,
    SyncRunOut,
    SyncStatus,
    SyncTriggerOut,
    TeamOut,
    TransferOut,
    TurnoverOut,
    UserOut,
)
from auth.accounts import Accounts, LoginError, Viewer
from core.config import Settings
from db.models import Fixture, League, SyncRun, utcnow
from kickbase import KickbaseAuthError, KickbaseError
from sync.scheduler import Scheduler
from sync.service import SyncService

COOKIE = "kbi_session"
### Kick-off to final whistle including half time and stoppage time
MATCH_LENGTH = timedelta(minutes=115)


@dataclass
class AppState:
    settings: Settings
    engine: Engine
    accounts: Accounts
    sync: SyncService
    live: LiveService
    scheduler: Scheduler
    ### Computed responses, valid until the league is synced again
    cache: dict[tuple, Any] = field(default_factory=dict)
    tasks: set[asyncio.Task] = field(default_factory=set)

    @property
    def configured(self) -> bool:
        """Something can be synced: users log in themselves, or there is an account to show."""
        return self.settings.auth.require_login or self.accounts.service is not None

    def spawn(self, coro: Coroutine) -> None:
        task = asyncio.create_task(coro)
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)


def get_state(request: Request) -> AppState:
    return request.app.state.kbi


def get_session(state: Annotated[AppState, Depends(get_state)]) -> Iterator[Session]:
    with Session(state.engine) as session:
        yield session


StateDep = Annotated[AppState, Depends(get_state)]
SessionDep = Annotated[Session, Depends(get_session)]


def get_optional_viewer(request: Request, state: StateDep) -> Viewer | None:
    if not state.settings.auth.require_login:
        return state.accounts.public_viewer()
    cookie = request.cookies.get(COOKIE)
    return state.accounts.resolve(cookie) if cookie else None


OptionalViewerDep = Annotated[Viewer | None, Depends(get_optional_viewer)]


def get_viewer(state: StateDep, viewer: OptionalViewerDep) -> Viewer:
    if viewer is not None:
        return viewer
    if not state.settings.auth.require_login:
        raise HTTPException(503, "No data yet. The first sync has not finished.")
    raise HTTPException(401, "Nicht angemeldet.")


ViewerDep = Annotated[Viewer, Depends(get_viewer)]


def get_league_id(
    viewer: ViewerDep,
    league: Annotated[
        str | None, Query(description="League id, defaults to the viewer's preferred league")
    ] = None,
) -> str:
    league_id = league or (viewer.league_ids[0] if viewer.league_ids else None)
    if league_id is None or league_id not in viewer.league_ids:
        raise HTTPException(404, "Diese Liga gibt es nicht oder du bist kein Mitglied.")
    return league_id


LeagueIdDep = Annotated[str, Depends(get_league_id)]


def get_league(session: SessionDep, league_id: LeagueIdDep) -> League:
    found = session.get(League, league_id)
    if found is None or found.synced_at is None:
        raise HTTPException(503, "No data yet. The first sync has not finished.")
    return found


LeagueDep = Annotated[League, Depends(get_league)]

router = APIRouter(prefix="/api")


def cached(
    state: AppState, league: League, key: tuple, build: Callable[[], Any], viewer: Viewer | None = None
) -> Any:
    """Reuse a computed response until the next sync of the league changes `synced_at`.

    Responses with private data pass the viewer, so every user gets their own copy.
    """
    full_key = (*key, league.id, league.synced_at, viewer.user_id if viewer else None)
    if full_key not in state.cache:
        if len(state.cache) > 512:
            state.cache.clear()
        state.cache[full_key] = build()
    return state.cache[full_key]


def insights(state: AppState, session: Session, league: League, viewer: Viewer | None = None) -> Insights:
    return Insights(state.settings, session, league, viewer.user_id if viewer else None)


### ===============================================================================
### Accounts
### ===============================================================================

def _me(session: Session, viewer: Viewer, require_login: bool) -> MeOut:
    leagues = {
        league.id: league for league in session.exec(select(League).where(League.id.in_(viewer.league_ids)))
    }
    return MeOut(
        user=UserOut(id=viewer.user_id, name=viewer.name, image=viewer.image),
        leagues=[LeagueOut.model_validate(leagues[lid]) for lid in viewer.league_ids if lid in leagues],
        require_login=require_login,
    )


@router.post("/auth/login", response_model=MeOut)
async def login(body: LoginIn, request: Request, response: Response, state: StateDep) -> MeOut:
    if not state.settings.auth.require_login:
        raise HTTPException(400, "Anmelden ist auf diesem Server nicht nötig.")
    ip = request.client.host if request.client else "unknown"
    try:
        cookie, viewer = await state.accounts.login(body.email, body.password, ip)
    except LoginError as e:
        raise HTTPException(e.status_code, str(e)) from e

    response.set_cookie(
        COOKIE,
        cookie,
        max_age=state.settings.auth.session_days * 86_400,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
        path="/",
    )
    ### Bring the user's leagues up to date in the background, the frontend polls the status
    client = state.accounts.client_for_viewer(viewer)
    if client is not None:
        state.spawn(state.sync.sync_for_viewer(viewer, client))

    def me() -> MeOut:
        with Session(state.engine) as session:
            return _me(session, viewer, True)

    return await asyncio.to_thread(me)


@router.post("/auth/logout", status_code=204)
def logout(request: Request, state: StateDep) -> Response:
    cookie = request.cookies.get(COOKIE)
    if cookie:
        state.accounts.logout(cookie)
    response = Response(status_code=204)
    response.delete_cookie(COOKIE, path="/")
    return response


@router.get("/auth/me", response_model=MeOut)
def me(state: StateDep, session: SessionDep, viewer: ViewerDep) -> MeOut:
    return _me(session, viewer, state.settings.auth.require_login)


### ===============================================================================
### Status and sync
### ===============================================================================

@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/status", response_model=StatusOut)
def status(
    state: StateDep,
    session: SessionDep,
    viewer: OptionalViewerDep,
    league: Annotated[str | None, Query()] = None,
) -> StatusOut:
    settings = state.settings
    league_row: League | None = None
    if viewer is not None and viewer.league_ids:
        league_id = league if league in viewer.league_ids else viewer.league_ids[0]
        league_row = session.get(League, league_id)

    last_run = last_success = None
    if league_row is not None:
        last_run = session.exec(
            select(SyncRun).where(SyncRun.league_id == league_row.id).order_by(SyncRun.id.desc()).limit(1)
        ).first()
        last_success = session.exec(
            select(SyncRun.finished_at)
            .where(SyncRun.league_id == league_row.id, SyncRun.status == "success")
            .order_by(SyncRun.id.desc())
            .limit(1)
        ).first()

    warnings = []
    if not state.configured:
        warnings.append(
            "Keine Kickbase-Zugangsdaten konfiguriert (KBI_KICKBASE__EMAIL / KBI_KICKBASE__PASSWORD)."
        )
    if viewer is not None and not settings.kickbase.start_date and not settings.demo:
        warnings.append(
            "KBI_KICKBASE__START_DATE ist nicht gesetzt. Der Saisonstart wird geschätzt, "
            "Erlöse von Startspielern können ungenau sein."
        )
    if last_run and last_run.status == "failed":
        warnings.append(f"Der letzte Sync ist fehlgeschlagen: {last_run.error}")

    live_now = False
    if league_row and league_row.current_day:
        now = utcnow()
        kickoffs = session.exec(
            select(Fixture.kickoff).where(
                Fixture.competition_id == league_row.competition_id,
                Fixture.day == league_row.current_day,
                Fixture.kickoff.is_not(None),
            )
        ).all()
        live_now = any(kickoff <= now < kickoff + MATCH_LENGTH for kickoff in kickoffs)

    return StatusOut(
        version=settings.version,
        demo=settings.demo,
        configured=state.configured,
        require_login=settings.auth.require_login,
        authenticated=viewer is not None,
        league=LeagueOut.model_validate(league_row) if league_row else None,
        own_manager_id=viewer.user_id if viewer else None,
        start_date=settings.kickbase.start_date if viewer else None,
        start_money=settings.kickbase.start_money,
        sync=SyncStatus(
            running=state.sync.running(league_row.id) if league_row else False,
            next_run=state.scheduler.next_run if viewer else None,
            last_run=SyncRunOut.model_validate(last_run) if last_run else None,
            last_success_at=last_success,
        ),
        live_now=live_now,
        warnings=warnings,
    )


@router.get("/sync/runs", response_model=list[SyncRunOut])
def sync_runs(
    session: SessionDep, league_id: LeagueIdDep, limit: Annotated[int, Query(ge=1, le=200)] = 25
) -> list[SyncRun]:
    return list(
        session.exec(
            select(SyncRun).where(SyncRun.league_id == league_id).order_by(SyncRun.id.desc()).limit(limit)
        )
    )


@router.post("/sync", status_code=202, response_model=SyncTriggerOut)
async def trigger_sync(
    state: StateDep,
    viewer: ViewerDep,
    league_id: LeagueIdDep,
    authorization: Annotated[str | None, Header()] = None,
) -> SyncTriggerOut:
    token = state.settings.api.sync_token
    if not state.settings.auth.require_login and token is not None:
        ### Without logins everyone is a viewer, so the token is what protects the button
        expected = f"Bearer {token.get_secret_value()}"
        if not authorization or not secrets.compare_digest(authorization, expected):
            raise HTTPException(401, "A valid sync token is required.")

    client = state.accounts.client_for_viewer(viewer)
    if client is None:
        raise HTTPException(401, "Deine Sitzung ist abgelaufen. Bitte melde dich erneut an.")
    if state.sync.running(league_id):
        return SyncTriggerOut(started=False, reason="Es läuft bereits ein Sync.")

    cooldown = timedelta(seconds=state.settings.sync.manual_cooldown_seconds)
    last = state.sync.last_manual_trigger.get(league_id)
    if last and utcnow() - last < cooldown:
        wait = int((cooldown - (utcnow() - last)).total_seconds()) + 1
        return SyncTriggerOut(started=False, reason=f"Bitte warte noch {wait} Sekunden.")

    state.sync.last_manual_trigger[league_id] = utcnow()
    triggered_by = viewer.name if viewer.session_id else None
    state.spawn(state.sync.run(league_id, client, "manual", triggered_by))
    return SyncTriggerOut(started=True)


### ===============================================================================
### League data
### ===============================================================================

@router.get("/leagues", response_model=list[LeagueOut])
def leagues(state: StateDep, session: SessionDep, viewer: ViewerDep) -> list[LeagueOut]:
    return _me(session, viewer, state.settings.auth.require_login).leagues


@router.get("/teams", response_model=list[TeamOut])
def teams(state: StateDep, session: SessionDep, league: LeagueDep):
    return cached(state, league, ("teams",), lambda: insights(state, session, league).teams())


@router.get("/players", response_model=list[PlayerOut])
def players(state: StateDep, session: SessionDep, league: LeagueDep):
    return cached(state, league, ("players",), lambda: insights(state, session, league).players())


@router.get("/players/{player_id}", response_model=PlayerDetailOut)
def player(player_id: str, state: StateDep, session: SessionDep, league: LeagueDep):
    result = insights(state, session, league).player(player_id)
    if result is None:
        raise HTTPException(404, "Unknown player")
    return result


@router.get("/market", response_model=list[MarketPlayerOut])
def market(state: StateDep, session: SessionDep, league: LeagueDep, viewer: ViewerDep):
    return cached(
        state, league, ("market",), lambda: insights(state, session, league, viewer).market(), viewer
    )


@router.get("/managers", response_model=list[ManagerOut])
def managers(state: StateDep, session: SessionDep, league: LeagueDep, viewer: ViewerDep):
    return cached(
        state, league, ("managers",), lambda: insights(state, session, league, viewer).managers(), viewer
    )


@router.get("/battles", response_model=list[BattleOut])
def battles(state: StateDep, session: SessionDep, league: LeagueDep):
    return cached(state, league, ("battles",), lambda: insights(state, session, league).battles())


@router.get("/transfers", response_model=list[TransferOut])
def transfers(state: StateDep, session: SessionDep, league: LeagueDep):
    return cached(state, league, ("transfers",), lambda: insights(state, session, league).transfers())


@router.get("/turnovers", response_model=list[TurnoverOut])
def turnovers(state: StateDep, session: SessionDep, league: LeagueDep):
    return cached(state, league, ("turnovers",), lambda: insights(state, session, league).turnovers())


@router.get("/charts/revenue", response_model=ChartOut)
def revenue_chart(state: StateDep, session: SessionDep, league: LeagueDep):
    return cached(state, league, ("revenue",), lambda: insights(state, session, league).revenue_chart())


@router.get("/charts/matchdays", response_model=MatchdayChartsOut)
def matchday_charts(state: StateDep, session: SessionDep, league: LeagueDep):
    return cached(state, league, ("matchdays",), lambda: insights(state, session, league).matchday_charts())


@router.get("/fixtures", response_model=FixturesOut)
def fixtures(
    state: StateDep,
    session: SessionDep,
    league: LeagueDep,
    day: Annotated[int | None, Query(ge=1, le=60)] = None,
):
    return cached(state, league, ("fixtures", day), lambda: insights(state, session, league).fixtures(day))


@router.get("/lineups", response_model=LineupsOut)
async def lineups(state: StateDep, league: LeagueDep, viewer: ViewerDep) -> LineupsOut:
    client = state.accounts.client_for_viewer(viewer)
    if client is None:
        raise HTTPException(401, "Deine Sitzung ist abgelaufen. Bitte melde dich erneut an.")
    try:
        return await state.live.lineups(league, client)
    except KickbaseAuthError as e:
        await asyncio.to_thread(state.accounts.forget_client, client)
        raise HTTPException(401, "Deine Kickbase-Sitzung ist abgelaufen. Bitte melde dich erneut an.") from e
    except KickbaseError as e:
        raise HTTPException(502, f"Kickbase ist gerade nicht erreichbar: {e}") from e


@router.get("/live", response_model=LiveOut)
async def live(state: StateDep, league: LeagueDep, viewer: ViewerDep) -> LiveOut:
    client = state.accounts.client_for_viewer(viewer)
    if client is None:
        raise HTTPException(401, "Deine Sitzung ist abgelaufen. Bitte melde dich erneut an.")
    try:
        return await state.live.get(league, client, viewer.user_id)
    except KickbaseAuthError as e:
        await asyncio.to_thread(state.accounts.forget_client, client)
        raise HTTPException(401, "Deine Kickbase-Sitzung ist abgelaufen. Bitte melde dich erneut an.") from e
    except KickbaseError as e:
        raise HTTPException(502, f"Kickbase ist gerade nicht erreichbar: {e}") from e
