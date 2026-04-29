import os
import time

from fastapi import APIRouter

import app.state as state
from app.config import MAX_CONCURRENT, PROXY_URL
from app.utils import format_uptime, mask_proxy

router = APIRouter()


@router.get("/")
async def status():
    return {
        "msg": "HeaderHarvest is running",
        "version": "1.0.0",
        "proxy": PROXY_URL or None,
    }


@router.get("/health")
async def health():
    _browser = state.browser
    session_details = [
        {
            "id": sid,
            "pages": len(ctx.pages),
            **state.session_meta.get(sid, {}),
        }
        for sid, ctx in state.sessions.items()
    ]
    uptime = format_uptime(time.monotonic() - state.start_time) if state.start_time else "n/a"
    active_slots = MAX_CONCURRENT - state.semaphore._value if state.semaphore else 0
    return {
        "status": "ok",
        "pid": os.getpid(),
        "uptime": uptime,
        "browser": {
            "state": "connected" if _browser and _browser.is_connected() else "disconnected",
            "version": _browser.version if _browser and _browser.is_connected() else None,
        },
        "proxy": mask_proxy(PROXY_URL) if PROXY_URL else None,
        "concurrency": {
            "max": MAX_CONCURRENT,
            "active": active_slots,
            "free": MAX_CONCURRENT - active_slots,
        },
        "sessions": {
            "count": len(state.sessions),
            "items": session_details,
        },
    }
