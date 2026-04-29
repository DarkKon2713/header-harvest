import asyncio
import logging
import time
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

import app.state as state
from app.browser import get_browser
from app.config import HEADLESS, MAX_CONCURRENT, PORT, PROXY_URL
from app.routes.health import router as health_router
from app.routes.v1 import router as v1_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    state.semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    state.start_time = time.monotonic()
    await get_browser()
    proxy_info = f"PROXY={PROXY_URL}" if PROXY_URL else "PROXY=none"
    logger.info(
        "Browser ready | port=%d headless=%s %s max_concurrent=%d",
        PORT, HEADLESS, proxy_info, MAX_CONCURRENT,
    )
    yield
    if state.sessions:
        logger.info("Shutdown: closing %d active session(s)", len(state.sessions))
    for sid, ctx in list(state.sessions.items()):
        try:
            await ctx.close()
            logger.info("session.destroy | session=%s reason=shutdown", sid)
        except Exception as e:
            logger.warning("session.destroy failed | session=%s error=%s", sid, e)
        state.session_meta.pop(sid, None)
    if state.browser:
        try:
            await state.browser.close()
        except Exception:
            pass
    if state.playwright:
        try:
            await state.playwright.stop()
        except Exception:
            pass


app = FastAPI(lifespan=lifespan)


@app.exception_handler(Exception)
async def global_exception_handler(_request: Request, exc: Exception):  # noqa: ARG001
    logger.error("Unhandled exception: %s\n%s", exc, traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": str(exc)},
    )


app.include_router(health_router)
app.include_router(v1_router)
