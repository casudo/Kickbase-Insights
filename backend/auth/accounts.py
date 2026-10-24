"""Logins and session handling.

Every visitor logs in with their own Kickbase account and only ever sees the leagues that account is
in. Which leagues get synced follows from that: every league with at least one logged in member,
plus the leagues of the optional account from the environment, which keeps syncing even when
nobody is logged in.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import Engine, delete
from sqlmodel import Session, select

from auth.security import TokenCipher, hash_session_token, new_session_token
from core.config import Settings
from db.models import League, User, UserLeague, UserSession, utcnow
from kickbase import KickbaseAuthError, KickbaseClient, KickbaseError, KickbaseHttp
from kickbase import models as kb
from sync.service import competition_id_of

log = logging.getLogger(__name__)

### last_seen_at is only written this often, so browsing does not turn every request into a write
TOUCH_INTERVAL = timedelta(minutes=5)


@dataclass(frozen=True)
class Viewer:
    """Who is looking. Decides which leagues are visible and whose private data is shown."""
    user_id: str
    name: str
    image: str | None
    ### The leagues this viewer may see, the preferred one first
    league_ids: tuple[str, ...]
    ### The login session behind it
    session_id: str


class LoginError(Exception):
    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code


class LoginRateLimiter:
    """Refuses further attempts after repeated failures, per e-mail address and per IP address.

    Without it the server would be an open relay for guessing Kickbase passwords.
    """
    WINDOW = timedelta(minutes=15)

    def __init__(self, max_per_email: int):
        self.max_per_email = max_per_email
        self._failures: dict[str, deque[datetime]] = defaultdict(deque)

    def _recent(self, key: str) -> deque[datetime]:
        entries = self._failures[key]
        cutoff = utcnow() - self.WINDOW
        while entries and entries[0] < cutoff:
            entries.popleft()
        return entries

    def blocked(self, email: str, ip: str) -> bool:
        return (
            len(self._recent(f"mail:{email}")) >= self.max_per_email
            or len(self._recent(f"ip:{ip}")) >= self.max_per_email * 4
        )

    def record_failure(self, email: str, ip: str) -> None:
        now = utcnow()
        self._recent(f"mail:{email}").append(now)
        self._recent(f"ip:{ip}").append(now)

    def clear(self, email: str) -> None:
        self._failures.pop(f"mail:{email}", None)


def select_league(leagues: list[kb.LeagueInfo], wanted: str | None) -> kb.LeagueInfo:
    if not leagues:
        raise KickbaseError("Your Kickbase account is not part of any league.")
    if wanted:
        for league in leagues:
            if wanted in (league.id, league.name) or league.name.casefold() == wanted.casefold():
                return league
        log.warning("League '%s' not found, using '%s' instead", wanted, leagues[0].name)
    return leagues[0]


class Accounts:
    def __init__(self, settings: Settings, engine: Engine, http: KickbaseHttp, cipher: TokenCipher):
        self.settings = settings
        self.engine = engine
        self.http = http
        self.cipher = cipher
        self.limiter = LoginRateLimiter(settings.auth.max_failed_logins)
        self.service: KickbaseClient | None = None
        self.service_user_id: str | None = None
        ### The leagues the account from the environment keeps synced. Its memberships stay complete:
        ### when it is also somebody's own account, they still see all their leagues.
        self.service_league_ids: set[str] = set()
        self._session_clients: dict[str, KickbaseClient] = {}

        kickbase = settings.kickbase
        if settings.demo:
            self.service = KickbaseClient("demo@example.com", "demo", http=http)
        elif kickbase.has_credentials:
            assert kickbase.password is not None
            self.service = KickbaseClient(kickbase.email, kickbase.password.get_secret_value(), http=http)

    ### ============================================================================================
    ### Login
    ### ============================================================================================

    async def login(self, email: str, password: str, ip: str) -> tuple[str, Viewer]:
        """Check the credentials with Kickbase and open a session. Returns the cookie value."""
        email = email.strip()
        key = email.casefold()
        if self.limiter.blocked(key, ip):
            raise LoginError(
                "Zu viele fehlgeschlagene Anmeldungen. Bitte versuche es in 15 Minuten erneut.", 429
            )

        try:
            login = await self.http.login(email, password)
        except KickbaseAuthError as e:
            self.limiter.record_failure(key, ip)
            raise LoginError("E-Mail-Adresse oder Passwort ist falsch.", 401) from e
        except KickbaseError as e:
            raise LoginError(
                "Kickbase ist gerade nicht erreichbar. Bitte versuche es später erneut.", 502
            ) from e
        self.limiter.clear(key)

        client = KickbaseClient(
            token=login.token, token_expiry=login.token_expiry, user=login.user, http=self.http
        )
        try:
            leagues = await client.leagues()
        except KickbaseError as e:
            raise LoginError(
                "Deine Ligen konnten nicht geladen werden. Bitte versuche es erneut.", 502
            ) from e

        allowed = [league for league in leagues if self.settings.auth.allows(league.id, league.name)]
        if not allowed:
            message = (
                "Dieser Server ist für keine deiner Ligen freigeschaltet."
                if leagues
                else "Dein Kickbase-Konto ist in keiner Liga."
            )
            raise LoginError(message, 403)

        cookie = new_session_token()
        viewer = await asyncio.to_thread(self._store_login, login, email, allowed, cookie)
        log.info("%s logged in (%d leagues)", login.user.name or login.user.id, len(allowed))
        return cookie, viewer

    def _store_login(
        self, login: kb.LoginResponse, email: str, leagues: list[kb.LeagueInfo], cookie: str
    ) -> Viewer:
        assert login.token_expiry is not None
        now = utcnow()
        with Session(self.engine) as session:
            self._upsert_user(session, login.user, email, now)
            self._replace_memberships(session, login.user.id, leagues)
            session_id = hash_session_token(cookie)
            session.add(
                UserSession(
                    id=session_id,
                    user_id=login.user.id,
                    token_encrypted=self.cipher.encrypt(login.token),
                    token_expires_at=login.token_expiry,
                    expires_at=min(now + timedelta(days=self.settings.auth.session_days), login.token_expiry),
                )
            )
            session.commit()
            viewer = self._viewer(session, login.user.id, session_id)
        assert viewer is not None
        return viewer

    def _upsert_user(self, session: Session, user: kb.LoginUser, email: str | None, now: datetime) -> None:
        row = session.get(User, user.id) or User(id=user.id, name=user.name)
        row.name = user.name or row.name
        row.image = user.image or row.image
        row.email = email or row.email
        row.last_login_at = now
        session.add(row)

    def _replace_memberships(self, session: Session, user_id: str, leagues: list[kb.LeagueInfo]) -> None:
        """Remember the user's leagues. Budgets of leagues they are still in are kept."""
        ids = {league.id for league in leagues}
        existing = {
            m.league_id: m for m in session.exec(select(UserLeague).where(UserLeague.user_id == user_id))
        }
        for league_id, membership in existing.items():
            if league_id not in ids:
                session.delete(membership)
        for info in leagues:
            if info.id not in existing:
                session.add(UserLeague(user_id=user_id, league_id=info.id))
            league = session.get(League, info.id) or League(id=info.id, name=info.name)
            league.name = info.name or league.name
            league.image = info.image or league.image
            league.competition_id = competition_id_of(info, self.settings.kickbase.competition_id)
            session.add(league)

    def logout(self, cookie: str) -> None:
        session_id = hash_session_token(cookie)
        self._session_clients.pop(session_id, None)
        with Session(self.engine) as session:
            session.exec(delete(UserSession).where(UserSession.id == session_id))
            session.commit()

    def resolve(self, cookie: str) -> Viewer | None:
        """The viewer behind a session cookie, None if the session is unknown or over."""
        session_id = hash_session_token(cookie)
        now = utcnow()
        with Session(self.engine) as session:
            row = session.get(UserSession, session_id)
            if row is None:
                return None
            if row.expires_at <= now or row.token_expires_at <= now:
                session.delete(row)
                session.commit()
                self._session_clients.pop(session_id, None)
                return None
            if now - row.last_seen_at > TOUCH_INTERVAL:
                row.last_seen_at = now
                session.add(row)
                session.commit()
            return self._viewer(session, row.user_id, session_id)

    def _viewer(self, session: Session, user_id: str, session_id: str) -> Viewer | None:
        user = session.get(User, user_id)
        if user is None:
            return None
        rows = session.exec(
            select(League.id, League.name)
            .join(UserLeague, UserLeague.league_id == League.id)
            .where(UserLeague.user_id == user_id)
        ).all()
        visible = [(lid, name) for lid, name in rows if self.settings.auth.allows(lid, name)]
        preferred = (self.settings.kickbase.league or "").casefold()
        visible.sort(
            key=lambda row: (preferred not in (row[0].casefold(), row[1].casefold()), row[1].casefold())
        )
        return Viewer(
            user_id=user.id,
            name=user.name,
            image=user.image,
            league_ids=tuple(lid for lid, _ in visible),
            session_id=session_id,
        )

    ### ============================================================================================
    ### The account from the environment
    ### ============================================================================================

    async def setup_service(self) -> None:
        """Log in the account from the environment and remember the leagues it syncs."""
        if self.service is None:
            return
        user = await self.service.ensure_login()
        leagues = [
            league
            for league in await self.service.leagues()
            if self.settings.auth.allows(league.id, league.name)
        ]
        synced = leagues
        if self.settings.kickbase.league and leagues:
            synced = [select_league(leagues, self.settings.kickbase.league)]
        if not synced:
            log.warning("The account from KBI_KICKBASE__EMAIL is in none of the allowed leagues")
        ### All memberships are stored, KBI_KICKBASE__LEAGUE only narrows down what this account syncs
        await asyncio.to_thread(self._store_service, user, leagues)
        self.service_user_id = user.id
        self.service_league_ids = {league.id for league in synced}

    def _store_service(self, user: kb.LoginUser, leagues: list[kb.LeagueInfo]) -> None:
        with Session(self.engine) as session:
            self._upsert_user(session, user, None, utcnow())
            self._replace_memberships(session, user.id, leagues)
            session.commit()

    ### ============================================================================================
    ### Clients
    ### ============================================================================================

    def client_for_session(self, session_id: str) -> KickbaseClient | None:
        cached = self._session_clients.get(session_id)
        if cached is not None:
            return cached
        with Session(self.engine) as session:
            row = session.get(UserSession, session_id)
            user = session.get(User, row.user_id) if row else None
            if row is None or user is None:
                return None
            token = self.cipher.decrypt(row.token_encrypted)
            if token is None:
                ### Encrypted with another secret, the session is useless now
                session.delete(row)
                session.commit()
                return None
            client = KickbaseClient(
                token=token,
                token_expiry=row.token_expires_at,
                user=kb.LoginUser(id=user.id, name=user.name, uim=user.image),
                http=self.http,
                session_id=session_id,
            )
        self._session_clients[session_id] = client
        return client

    def client_for_viewer(self, viewer: Viewer) -> KickbaseClient | None:
        return self.client_for_session(viewer.session_id)

    def _service_leagues(self, session: Session) -> set[str]:
        if self.service_user_id is None:
            return set()
        members = set(
            session.exec(select(UserLeague.league_id).where(UserLeague.user_id == self.service_user_id))
        )
        return members & self.service_league_ids

    def _member_sessions(self, session: Session, league_id: str) -> list[UserSession]:
        """Valid sessions of the league's members, most recently active first, one per user."""
        now = utcnow()
        rows = session.exec(
            select(UserSession)
            .join(UserLeague, UserLeague.user_id == UserSession.user_id)
            .where(
                UserLeague.league_id == league_id,
                UserSession.expires_at > now,
                UserSession.token_expires_at > now,
            )
            .order_by(UserSession.last_seen_at.desc())
        ).all()
        seen: set[str] = set()
        result = []
        for row in rows:
            if row.user_id not in seen:
                seen.add(row.user_id)
                result.append(row)
        return result

    def client_for_league(self, league_id: str) -> KickbaseClient | None:
        """Prefer the account from the environment, it never expires. Otherwise any active member."""
        with Session(self.engine) as session:
            if league_id in self._service_leagues(session):
                return self.service
            sessions = self._member_sessions(session, league_id)
        for row in sessions:
            client = self.client_for_session(row.id)
            if client is not None:
                return client
        return None

    def member_clients(self, league_id: str, exclude_user: str | None = None) -> list[KickbaseClient]:
        """One client per logged in member, to refresh what only they can see."""
        with Session(self.engine) as session:
            sessions = self._member_sessions(session, league_id)
        clients = []
        for row in sessions:
            if row.user_id in (exclude_user, self.service_user_id):
                continue
            client = self.client_for_session(row.id)
            if client is not None:
                clients.append(client)
        return clients

    def sync_targets(self) -> list[tuple[str, KickbaseClient]]:
        """Every league somebody can currently sync, with the client to sync it with."""
        now = utcnow()
        with Session(self.engine) as session:
            league_ids = self._service_leagues(session)
            league_ids |= set(
                session.exec(
                    select(UserLeague.league_id)
                    .join(UserSession, UserSession.user_id == UserLeague.user_id)
                    .where(UserSession.expires_at > now, UserSession.token_expires_at > now)
                    .distinct()
                )
            )
            names = dict(
                session.exec(select(League.id, League.name).where(League.id.in_(list(league_ids)))).all()
            )
        targets = []
        for league_id in sorted(league_ids):
            if not self.settings.auth.allows(league_id, names.get(league_id, "")):
                continue
            client = self.client_for_league(league_id)
            if client is not None:
                targets.append((league_id, client))
        return targets

    def forget_client(self, client: KickbaseClient) -> None:
        """Kickbase rejected a session token: end that session, the user has to log in again."""
        if client.session_id is None:
            return
        self._session_clients.pop(client.session_id, None)
        with Session(self.engine) as session:
            session.exec(delete(UserSession).where(UserSession.id == client.session_id))
            session.commit()

    def prune_sessions(self) -> int:
        now = utcnow()
        with Session(self.engine) as session:
            expired = session.exec(
                select(UserSession.id).where(
                    (UserSession.expires_at <= now) | (UserSession.token_expires_at <= now)
                )
            ).all()
            if expired:
                session.exec(delete(UserSession).where(UserSession.id.in_(expired)))
                session.commit()
        for session_id in expired:
            self._session_clients.pop(session_id, None)
        return len(expired)
