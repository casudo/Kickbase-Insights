"""Async client for the Kickbase API v4."""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import UTC, datetime, timedelta
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel

from core.version import __version__
from kickbase import models

log = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

BASE_URL = "https://api.kickbase.com"

### ==========================================================================================================
### ERROR Definitions
### ==========================================================================================================


class KickbaseError(Exception):
    """A request against the Kickbase API failed."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class KickbaseAuthError(KickbaseError):
    """The login was rejected or a session token is no longer accepted."""


### ==========================================================================================================
### HTTP Client
### ==========================================================================================================


class KickbaseHttp:
    """Connection pool, concurrency limit and retry policy shared by EVERY client of the app.

    Stops multiple clients from overwhelming the Kickbase API with concurrent requests.
    """
    def __init__(
        self,
        *,
        concurrency: int = 12,
        timeout: float = 20.0,
        retries: int = 3,
        transport: httpx.AsyncBaseTransport | None = None,
        base_url: str = BASE_URL,
    ):
        self.retries = retries
        self.semaphore = asyncio.Semaphore(concurrency)
        self.client = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            transport=transport,
            headers={
                "Accept": "application/json",
                "Accept-Language": "de-DE,de;q=0.9", # German texts for injury notes and battle names
                "User-Agent": f"KickbaseInsights/{__version__}",
            },
        )

    async def aclose(self) -> None:
        await self.client.aclose()

    async def login(self, email: str, password: str) -> models.LoginResponse:
        """Log in with Kickbase credentials."""
        try:
            async with self.semaphore:
                response = await self.client.post(
                    "/v4/user/login",
                    json={"em": email, "pass": password, "loy": False, "rep": {}, "ext": True},
                )
        except httpx.TransportError as e:
            raise KickbaseError(f"Login failed, Kickbase is unreachable: {e}") from e

        ### Response handling
        if response.status_code in (400, 401, 403):
            raise KickbaseAuthError(
                "Login rejected. Please check your Kickbase credentials.", response.status_code
            )
        if response.status_code >= 400:
            raise KickbaseError(f"Login failed with HTTP {response.status_code}", response.status_code)

        login = models.LoginResponse.model_validate(response.json())
        if not login.token:
            raise KickbaseAuthError("Login response did not contain a token.")
        ### Without an expiry, assume a conservative lifetime
        if login.token_expiry is None:
            login.token_expiry = datetime.now(UTC) + timedelta(hours=12)
        return login


class KickbaseClient:
    """KickbaseClient exists per account. It either logs in with a password or uses the token of a user session."""
    def __init__(
        self,
        email: str | None = None,
        password: str | None = None,
        *,
        token: str | None = None,
        token_expiry: datetime | None = None,
        user: models.LoginUser | None = None,
        http: KickbaseHttp | None = None,
        session_id: str | None = None,
        **http_options: Any,
    ):
        self._owns_http = http is None
        self._http = http or KickbaseHttp(**http_options)
        self._email = email
        self._password = password
        self._login_lock = asyncio.Lock()
        self._token = token
        self._token_expiry = token_expiry
        self.user = user
        ### The user session this client belongs to, None for a password client
        self.session_id = session_id
        self.request_count = 0

    @property
    def can_relogin(self) -> bool:
        return bool(self._email and self._password)

    @property
    def token(self) -> str | None:
        return self._token

    @property
    def token_expiry(self) -> datetime | None:
        return self._token_expiry

    async def aclose(self) -> None:
        if self._owns_http:
            await self._http.aclose()

    async def __aenter__(self) -> KickbaseClient:
        return self

    async def __aexit__(self, *exc) -> None:
        await self.aclose()

    ### ======================================================================================================
    ### Authentication and login management
    ### ======================================================================================================

    async def login(self) -> models.LoginResponse:
        if not self.can_relogin:
            raise KickbaseAuthError("This client has no credentials to log in with.", 401)
        login = await self._http.login(self._email or "", self._password or "")
        self.request_count += 1
        self._token = login.token
        self._token_expiry = login.token_expiry
        self.user = login.user
        log.info("Logged in to Kickbase as %s", login.user.name or login.user.id)
        return login

    async def _ensure_token(self) -> None:
        async with self._login_lock:
            now = datetime.now(UTC)
            if self._token and self._token_expiry and self._token_expiry - now > timedelta(minutes=5):
                return
            if not self.can_relogin:
                ### A session token cannot be renewed, so it is used until the very end
                if self._token and (self._token_expiry is None or self._token_expiry > now):
                    return
                raise KickbaseAuthError("The Kickbase session has expired.", 401)
            await self.login()

    async def ensure_login(self) -> models.LoginUser:
        await self._ensure_token()
        if self.user is None:
            raise KickbaseAuthError("No user is known for this client.", 401)
        return self.user

    def _auth_headers(self) -> dict[str, str]:
        ### Kickbase v4 accepts the bearer token, older clients sent it as cookie. Both are sent.
        return {"Authorization": f"Bearer {self._token}", "Cookie": f"kkstrauth={self._token};"}

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json: Any = None,
        headers: dict | None = None,
    ) -> Any:
        await self._ensure_token()
        relogged = False
        last_error: Exception | None = None
        retries = self._http.retries

        for attempt in range(retries + 1):
            delay = 0.5 * 2**attempt + random.uniform(0, 0.25)
            try:
                async with self._http.semaphore:
                    response = await self._http.client.request(
                        method,
                        path,
                        params=params,
                        json=json,
                        headers={**self._auth_headers(), **(headers or {})},
                    )
            except httpx.TransportError as e:
                last_error = KickbaseError(f"{method} {path} failed: {e}")
            else:
                self.request_count += 1
                if response.status_code == 401:
                    if not self.can_relogin:
                        raise KickbaseAuthError("Kickbase no longer accepts this session.", 401)
                    if not relogged:
                        ### The token was revoked early. Log in once more and retry right away.
                        relogged = True
                        self._token = None
                        await self._ensure_token()
                        continue
                if response.status_code == 429 or response.status_code >= 500:
                    last_error = KickbaseError(
                        f"{method} {path} returned HTTP {response.status_code}", response.status_code
                    )
                    retry_after = response.headers.get("Retry-After")
                    if retry_after and retry_after.isdigit():
                        delay = max(delay, min(float(retry_after), 30.0))
                elif response.status_code >= 400:
                    raise KickbaseError(
                        f"{method} {path} returned HTTP {response.status_code}", response.status_code
                    )
                else:
                    return response.json() if response.content else {}

            if attempt < retries:
                await asyncio.sleep(delay)

        assert last_error is not None
        raise last_error

    async def _get(self, model: type[T], path: str, params: dict | None = None) -> T:
        return model.model_validate(await self.request("GET", path, params=params))

    ### ======================================================================================================
    ### Leagues
    ### ======================================================================================================

    async def leagues(self) -> list[models.LeagueInfo]:
        data = await self.request("GET", "/v4/leagues/selection")
        return [models.LeagueInfo.model_validate(item) for item in data.get("it", [])]

    async def league_overview(self, league_id: str) -> models.LeagueOverview:
        return await self._get(
            models.LeagueOverview,
            f"/v4/leagues/{league_id}/overview",
            {"includeManagersAndBattles": "true"},
        )

    async def own_budget(self, league_id: str) -> models.Budget:
        return await self._get(models.Budget, f"/v4/leagues/{league_id}/me/budget")

    async def manager_dashboard(self, league_id: str, manager_id: str) -> models.ManagerDashboard:
        return await self._get(models.ManagerDashboard, f"/v4/leagues/{league_id}/managers/{manager_id}/dashboard")

    async def manager_squad(self, league_id: str, manager_id: str) -> models.ManagerSquad:
        return await self._get(models.ManagerSquad, f"/v4/leagues/{league_id}/managers/{manager_id}/squad")

    async def battle(self, league_id: str, battle_type: int) -> models.BattleUsers:
        return await self._get(models.BattleUsers, f"/v4/leagues/{league_id}/battles/{battle_type}/users")

    async def ranking(self, league_id: str, day: int | None = None) -> models.Ranking:
        params = {"dayNumber": day} if day is not None else None
        return await self._get(models.Ranking, f"/v4/leagues/{league_id}/ranking", params)

    async def market(self, league_id: str) -> models.Market:
        return await self._get(models.Market, f"/v4/leagues/{league_id}/market")

    async def feed_page(self, league_id: str, start: int, size: int = 50) -> list[models.FeedItem]:
        page = await self._get(
            models.FeedPage, f"/v4/leagues/{league_id}/activitiesFeed", {"start": start, "max": size}
        )
        return page.items

    async def feed_until(self, league_id: str, known_ids: set[str], max_pages: int = 500) -> list[models.FeedItem]:
        """Page through the activity feed (newest first) until an already stored item shows up."""
        items: list[models.FeedItem] = []
        start = 0
        for _ in range(max_pages):
            page = await self.feed_page(league_id, start)
            if not page:
                break
            items.extend(item for item in page if item.id not in known_ids)
            if any(item.id in known_ids for item in page):
                break
            ### Advance by what actually arrived, in case Kickbase caps the page size
            start += len(page)
        return items

    async def collect_bonus(self) -> dict:
        return await self.request("GET", "/v4/bonus/collect")

    ### ======================================================================================================
    ### Competitions
    ### ======================================================================================================

    async def competition_table(self, competition_id: int) -> models.CompetitionTable:
        return await self._get(models.CompetitionTable, f"/v4/competitions/{competition_id}/table")

    async def matchdays(self, competition_id: int) -> models.Matchdays:
        return await self._get(models.Matchdays, f"/v4/competitions/{competition_id}/matchdays")

    async def team_profile(self, competition_id: int, team_id: str) -> models.TeamProfile:
        return await self._get(
            models.TeamProfile, f"/v4/competitions/{competition_id}/teams/{team_id}/teamprofile"
        )

    async def player(self, competition_id: int, player_id: str) -> models.PlayerDetails:
        return await self._get(models.PlayerDetails, f"/v4/competitions/{competition_id}/players/{player_id}")

    async def market_value_history(
        self, competition_id: int, player_id: str, days: int = 365
    ) -> models.MarketValueHistory:
        return await self._get(
            models.MarketValueHistory, f"/v4/competitions/{competition_id}/players/{player_id}/marketValue/{days}"
        )

    async def player_center(
        self, competition_id: int, player_id: str, *, day: int | None = None, league_id: str | None = None
    ) -> models.PlayerCenter:
        params: dict[str, Any] = {}
        if day is not None:
            params["dayNumber"] = day
        if league_id is not None:
            params["leagueId"] = league_id
        return await self._get(
            models.PlayerCenter, f"/v4/competitions/{competition_id}/playercenter/{player_id}", params or None
        )

    async def event_types(self, language: str | None = None) -> models.EventTypes:
        headers = {"Accept-Language": language} if language else None
        return models.EventTypes.model_validate(await self.request("GET", "/v4/live/eventtypes", headers=headers))
