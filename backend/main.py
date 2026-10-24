"""CLI entrypoint.

python main.py start        start the web server (API, frontend and scheduler)
python main.py sync         run a single sync and exit
python main.py healthcheck  exit 0 if the local server answers, used by Docker
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from core.version import __version__


def _start() -> None:
    import uvicorn

    from api.app import create_app
    from core.config import get_settings

    settings = get_settings()
    uvicorn.run(
        create_app(settings),
        host=settings.api.host,
        port=settings.api.port,
        proxy_headers=True,
        forwarded_allow_ips=settings.api.forwarded_allow_ips,
    )


def _sync() -> int:
    """Sync every league of the account from the environment once, then exit."""
    from api.app import configure_logging, database_url
    from auth.accounts import Accounts
    from auth.security import TokenCipher
    from core.config import get_settings
    from db import create_db_engine, init_db
    from kickbase import KickbaseHttp, PicturePool
    from sync.service import SyncService

    settings = get_settings()
    configure_logging(settings.debug)
    if not settings.demo and not settings.kickbase.has_credentials:
        print(
            "No Kickbase credentials configured (KBI_KICKBASE__EMAIL / KBI_KICKBASE__PASSWORD).",
            file=sys.stderr,
        )
        return 2

    async def run() -> int:
        engine = create_db_engine(database_url(settings))
        init_db(engine)
        transport = None
        if settings.demo:
            from kickbase.demo import DemoWorld

            transport = DemoWorld().transport()
        http = KickbaseHttp(concurrency=settings.sync.concurrency, transport=transport)
        pictures = None if settings.demo else PicturePool()
        secret = settings.auth.secret_key.get_secret_value() if settings.auth.secret_key else None
        accounts = Accounts(settings, engine, http, TokenCipher.from_settings(secret, settings.data_dir))
        try:
            await accounts.setup_service()
            runs = await SyncService(settings, engine, accounts, pictures).run_all("manual")
        finally:
            await http.aclose()
            if pictures:
                await pictures.aclose()
            engine.dispose()
        return 0 if runs and all(run.status == "success" for run in runs) else 1

    return asyncio.run(run())


def _healthcheck() -> int:
    """Check the health of the web server"""
    import urllib.request

    from core.config import get_settings

    port = get_settings().api.port
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=4) as response:
            return 0 if response.status == 200 else 1
    except OSError:
        return 1

### ======================================================================================================

def main() -> None:
    parser = argparse.ArgumentParser(prog="main.py", description=f"Kickbase Insights {__version__}")
    parser.add_argument("command", nargs="?", default="start", choices=["start", "sync", "healthcheck"])

    args = parser.parse_args()

    if args.command == "sync":
        sys.exit(_sync())
    if args.command == "healthcheck":
        sys.exit(_healthcheck())
    ### Default: start the web server
    _start()


if __name__ == "__main__":
    main()
