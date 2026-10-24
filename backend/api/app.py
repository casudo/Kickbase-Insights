"""FastAPI application: the REST API plus the built frontend, on one port."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

from api.live import LiveService
from api.routes import AppState, router
from auth.accounts import Accounts
from auth.security import TokenCipher
from core.config import Settings, get_settings
from core.version import __version__
from db import create_db_engine, init_db
from kickbase import KickbaseHttp, PicturePool
from sync.scheduler import Scheduler
from sync.service import SyncService, mark_interrupted_runs

log = logging.getLogger("kbi")


def configure_logging(debug: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    ### One line per request is far too chatty for a sync with hundreds of them
    for noisy in ("httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def database_url(settings: Settings) -> str:
    ### Demo data must never end up in a real database
    if settings.demo and not settings.database.url:
        return f"sqlite:///{(settings.data_dir / 'demo.db').as_posix()}"
    return settings.database_url


class ETagMiddleware(BaseHTTPMiddleware):
    """Weak ETags for API responses, so unchanged data costs a 304 instead of the full payload."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.method != "GET" or not request.url.path.startswith("/api/") or response.status_code != 200:
            return response
        body = b"".join([chunk async for chunk in response.body_iterator])
        etag = f'W/"{hashlib.blake2b(body, digest_size=12).hexdigest()}"'
        if etag in request.headers.get("if-none-match", ""):
            return Response(status_code=304, headers={"ETag": etag, "Cache-Control": "no-cache"})
        headers = {k: v for k, v in response.headers.items() if k.lower() != "content-length"}
        headers.update({"ETag": etag, "Cache-Control": "no-cache"})
        return Response(body, status_code=200, headers=headers)


def create_app(
    settings: Settings | None = None,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
    start_scheduler: bool = True,
) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        configure_logging(settings.debug)
        log.info(
            "Kickbase Insights %s starting%s", settings.version, " in demo mode" if settings.demo else ""
        )

        engine = create_db_engine(database_url(settings))
        await asyncio.to_thread(init_db, engine)
        await asyncio.to_thread(mark_interrupted_runs, engine)

        kickbase_transport = transport
        if settings.demo and kickbase_transport is None:
            from kickbase.demo import DemoWorld

            kickbase_transport = DemoWorld().transport()

        ### One connection pool and concurrency limit for every account
        http = KickbaseHttp(concurrency=settings.sync.concurrency, transport=kickbase_transport)
        cipher = TokenCipher.from_settings(
            settings.auth.secret_key.get_secret_value() if settings.auth.secret_key else None,
            settings.data_dir,
        )
        accounts = Accounts(settings, engine, http, cipher)
        ### Portraits for players the API only shows with a placeholder. Never for the made up demo
        ### players, and not in tests that bring their own Kickbase.
        pictures = PicturePool() if not settings.demo and transport is None else None
        sync = SyncService(settings, engine, accounts, pictures)
        scheduler = Scheduler(sync)
        state = AppState(
            settings=settings,
            engine=engine,
            accounts=accounts,
            sync=sync,
            live=LiveService(settings, engine),
            scheduler=scheduler,
        )
        app.state.kbi = state

        if start_scheduler:
            scheduler.start()

        try:
            yield
        finally:
            await sync.shutdown()
            await scheduler.stop()
            for task in list(state.tasks):
                task.cancel()
            await asyncio.gather(*state.tasks, return_exceptions=True)
            await http.aclose()
            if pictures:
                await pictures.aclose()
            engine.dispose()

    app = FastAPI(
        title="Kickbase Insights",
        version=__version__,
        lifespan=lifespan,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )
    app.add_middleware(ETagMiddleware)
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    if settings.api.cors_origins:
        app.add_middleware(
            CORSMiddleware, allow_origins=settings.api.cors_origins, allow_methods=["*"], allow_headers=["*"]
        )

    app.include_router(router)
    mount_frontend(app, settings.frontend_dir)
    return app


def mount_frontend(app: FastAPI, frontend_dir: Path) -> None:
    """Serve the built single page app. Unknown paths get index.html so client side routes work."""
    index = frontend_dir / "index.html"

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        ### Sync on purpose: FastAPI runs it in the threadpool, the file checks below block
        if path.startswith("api/") or path == "api":
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        if not index.exists():
            hint = "The frontend is not built. Run `npm run build` in frontend/ or use `npm run dev`."
            return JSONResponse(
                {"detail": hint},
                status_code=404,
            )
        candidate = (frontend_dir / path).resolve()
        if path and candidate.is_file() and candidate.is_relative_to(frontend_dir.resolve()):
            ### Vite fingerprints everything in assets/, so those files never change
            immutable = path.startswith("assets/")
            headers = {"Cache-Control": "public, max-age=31536000, immutable" if immutable else "no-cache"}
            return FileResponse(candidate, headers=headers)
        return FileResponse(index, headers={"Cache-Control": "no-cache"})
