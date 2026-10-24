"""Async client for the Kickbase CDN."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Iterable

import httpx

from core.version import __version__

log = logging.getLogger(__name__)

CDN_URL = "https://kickbase.b-cdn.net"

### Players without a pool picture are asked about again after this long, they may have got one
MISSING_RECHECK_SECONDS = 3 * 24 * 3600
### A slow CDN must not hold up the sync, whatever is not answered by then is asked next time
LOOKUP_TIMEOUT_SECONDS = 60


def pool_path(player_id: str) -> str:
    return f"pool/playersbig/{player_id}.png"


class PicturePool:
    def __init__(
        self,
        *,
        concurrency: int = 8,
        timeout: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self._semaphore = asyncio.Semaphore(concurrency)
        ### Its own client: the CDN never gets to see a Kickbase token
        self._client = httpx.AsyncClient(
            base_url=CDN_URL,
            timeout=timeout,
            transport=transport,
            headers={"User-Agent": f"KickbaseInsights/{__version__}"},
        )
        self._missing: dict[str, float] = {}

    async def aclose(self) -> None:
        await self._client.aclose()

    async def find(self, player_ids: Iterable[str]) -> dict[str, str]:
        """The pool picture of every given player that has one, as a path for the CDN."""
        now = time.monotonic()

        def due(pid: str) -> bool:
            missing_since = self._missing.get(pid)
            return missing_since is None or now - missing_since >= MISSING_RECHECK_SECONDS

        ### Kickbase's ids are numbers, anything else has no business in a URL
        ids = [pid for pid in dict.fromkeys(player_ids) if pid.isdigit() and due(pid)]
        if not ids:
            return {}
        tasks = {asyncio.create_task(self._exists(pid)): pid for pid in ids}
        done, pending = await asyncio.wait(tasks, timeout=LOOKUP_TIMEOUT_SECONDS)
        for task in pending:
            task.cancel()
        if pending:
            log.info("The picture pool did not answer for %d players in time", len(pending))

        found: dict[str, str] = {}
        for task in done:
            pid = tasks[task]
            exists = task.result()
            if exists:
                found[pid] = pool_path(pid)
                self._missing.pop(pid, None)
            elif exists is False:
                self._missing[pid] = time.monotonic()
        return found

    async def _exists(self, player_id: str) -> bool | None:
        """Whether the pool has a picture of the player, `None` when the CDN could not be asked."""
        async with self._semaphore:
            try:
                response = await self._client.head(f"/{pool_path(player_id)}")
            except httpx.HTTPError as e:
                log.debug("Picture pool lookup of %s failed: %s", player_id, e)
                return None
        if response.status_code == 200:
            return response.headers.get("content-type", "").startswith("image/")
        if response.status_code in (403, 404):
            return False
        return None
