"""Discord webhook notifications. Optional, nothing happens without a webhook URL."""

from __future__ import annotations

import logging

import httpx

log = logging.getLogger(__name__)

GREEN = 0x64FA00
RED = 0xFF0000


### TODO: SMTP

async def discord(webhook_url: str | None, title: str, message: str, color: int = GREEN) -> None:
    if not webhook_url:
        return
    payload = {
        "username": "Kickbase Insights",
        "embeds": [{"title": title, "description": message[:4000], "color": color}],
    }
    try:
        async with httpx.AsyncClient(timeout=10) as http:
            response = await http.post(webhook_url, json=payload)
            response.raise_for_status()
    except httpx.HTTPError as e:
        ### A broken webhook must never take a sync down with it
        log.warning("Discord notification failed: %s", e)
