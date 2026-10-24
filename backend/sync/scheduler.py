"""Runs the sync on a cron schedule."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import datetime, timedelta

from croniter import croniter

from db.models import utcnow
from sync.service import SyncService

log = logging.getLogger(__name__)


class Scheduler:
    def __init__(self, service: SyncService):
        self.service = service
        self.next_run: datetime | None = None
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._loop(), name="sync-scheduler")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    def compute_next_run(self, now: datetime | None = None) -> datetime:
        settings = self.service.settings.sync
        local_now = (now or utcnow()).astimezone(settings.tz)
        return croniter(settings.schedule, local_now).get_next(datetime)

    async def _loop(self) -> None:
        settings = self.service.settings.sync
        try:
            await self.service.accounts.setup_service()
        except Exception:
            log.exception("Could not log in the account from KBI_KICKBASE__EMAIL")

        ### Leagues whose data is missing or older than the threshold are synced right away
        await self.service.run_all(
            "startup", stale_after=timedelta(minutes=settings.startup_if_older_than_minutes)
        )

        while True:
            self.next_run = self.compute_next_run()
            log.info("Next sync at %s", self.next_run.isoformat(timespec="minutes"))
            ### Sleep in slices, so a suspended host or clock change cannot oversleep a run by hours
            while (remaining := (self.next_run - utcnow()).total_seconds()) > 0:  # noqa: ASYNC110
                await asyncio.sleep(min(remaining, 300))
            try:
                await asyncio.to_thread(self.service.accounts.prune_sessions)
                await self.service.run_all("schedule")
            except Exception:  # pragma: no cover - run() already logs and records failures
                log.exception("Scheduled sync crashed")
