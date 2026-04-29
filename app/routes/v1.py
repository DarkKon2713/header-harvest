import logging
import time
import traceback

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

import app.state as state
from app.browser import do_request, get_or_create_session

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/v1")
async def handle_v1(request: Request):
    body: dict = await request.json()
    cmd = body.get("cmd")

    if not cmd:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Missing cmd"})

    try:
        if cmd == "request.get":
            url = body.get("url")
            if not url:
                return JSONResponse(status_code=400, content={"status": "error", "message": "Missing url"})
            return await do_request(
                url=url,
                method="GET",
                headers=body.get("headers"),
                cookies=body.get("cookies"),
                timeout=body.get("maxTimeout"),
                session=body.get("session"),
                screenshot=bool(body.get("returnScreenshot", False)),
                only_cookies=bool(body.get("returnOnlyCookies", False)),
                wait_seconds=int(body.get("waitInSeconds", 0)),
                js_code=body.get("javaScript"),
                capture_headers=body.get("captureHeaders"),
                wait_until=body.get("waitUntil", "load"),
                proxy_url=body.get("proxy"),
                block_resources=body.get("blockResources"),
            )

        if cmd == "request.post":
            url = body.get("url")
            if not url:
                return JSONResponse(status_code=400, content={"status": "error", "message": "Missing url"})
            return await do_request(
                url=url,
                method="POST",
                post_data=body.get("postData"),
                headers=body.get("headers"),
                cookies=body.get("cookies"),
                timeout=body.get("maxTimeout"),
                session=body.get("session"),
                screenshot=bool(body.get("returnScreenshot", False)),
                only_cookies=bool(body.get("returnOnlyCookies", False)),
                wait_seconds=int(body.get("waitInSeconds", 0)),
                js_code=body.get("javaScript"),
                capture_headers=body.get("captureHeaders"),
                wait_until=body.get("waitUntil", "load"),
                proxy_url=body.get("proxy"),
                block_resources=body.get("blockResources"),
            )

        if cmd == "sessions.create":
            session_id = body.get("session") or f"session_{int(time.time() * 1000)}"
            await get_or_create_session(session_id, proxy_url=body.get("proxy"))
            return {"status": "ok", "session": session_id}

        if cmd == "sessions.list":
            return {"status": "ok", "sessions": list(state.sessions.keys())}

        if cmd == "sessions.destroy":
            session_id = body.get("session")
            if not session_id:
                return JSONResponse(status_code=400, content={"status": "error", "message": "Missing session"})
            if session_id in state.sessions:
                ctx = state.sessions.pop(session_id)
                state.session_meta.pop(session_id, None)
                await ctx.close()
                logger.info("session.destroy | session=%s", session_id)
                return {"status": "ok"}
            return JSONResponse(status_code=404, content={"status": "error", "message": "Session not found"})

        if cmd == "sessions.get_cookies":
            session_id = body.get("session")
            if not session_id:
                return JSONResponse(status_code=400, content={"status": "error", "message": "Missing session"})
            if session_id not in state.sessions:
                return JSONResponse(status_code=404, content={"status": "error", "message": "Session not found"})
            cookies = await state.sessions[session_id].cookies()
            return {"status": "ok", "cookies": cookies}

        return JSONResponse(status_code=400, content={"status": "error", "message": f"Unknown cmd: {cmd}"})

    except Exception as e:
        logger.error("cmd=%s: %s\n%s", cmd, e, traceback.format_exc())
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
