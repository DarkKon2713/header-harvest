import base64
import logging
import os
import time
import traceback
from contextlib import asynccontextmanager
from typing import Optional
from urllib.parse import urlparse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from playwright.async_api import async_playwright, Browser, BrowserContext, Playwright
import uvicorn

PORT = int(os.environ.get("PORT", 9191))
HEADLESS = os.environ.get("HEADLESS", "false").lower() != "false"
MAX_TIMEOUT = int(os.environ.get("MAX_TIMEOUT", 60000))
PROXY_URL = os.environ.get("PROXY_URL", "")

sessions: dict[str, BrowserContext] = {}
_browser: Optional[Browser] = None
_playwright: Optional[Playwright] = None

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
LAUNCH_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-blink-features=AutomationControlled",
]


def parse_proxy(proxy_url) -> Optional[dict]:
    """Convert proxy URL to Playwright proxy dict.

    Supports: http://host:port  and  http://user:pass@host:port
    (including Bright Data: http://brd-customer-...:pass@zproxy.lum-superproxy.io:22225)
    Also accepts a dict already in Playwright format (passthrough).
    """
    if not proxy_url:
        return None
    if isinstance(proxy_url, dict):
        return proxy_url if proxy_url.get("server") else None
    if not isinstance(proxy_url, str):
        raise ValueError(f"proxy must be a string URL or dict, got {type(proxy_url).__name__}")
    parsed = urlparse(proxy_url)
    if parsed.username or parsed.password:
        # Proxy autenticado: separa credenciais da URL do servidor
        server = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"
        proxy: dict = {"server": server}
        if parsed.username:
            proxy["username"] = parsed.username
        if parsed.password:
            proxy["password"] = parsed.password
        return proxy
    # Proxy simples: passa a URL diretamente, sem reconstruir
    return {"server": proxy_url.rstrip("/")}


def _mask_proxy(proxy_url) -> str:
    if not proxy_url:
        return "none"
    if isinstance(proxy_url, dict):
        server = proxy_url.get("server", "")
        return f"***@{server}" if proxy_url.get("username") else server
    parsed = urlparse(proxy_url)
    if parsed.password:
        return f"{parsed.scheme}://***@{parsed.hostname}:{parsed.port}"
    return proxy_url.rstrip("/")


async def get_browser() -> Browser:
    global _browser, _playwright
    if _browser is None or not _browser.is_connected():
        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(headless=HEADLESS, args=LAUNCH_ARGS)
    return _browser


async def get_or_create_session(
    session_id: str,
    proxy_url: Optional[str] = None,
) -> BrowserContext:
    ctx = sessions.get(session_id)
    if ctx is not None:
        return ctx
    browser = await get_browser()
    kwargs: dict = {
        "user_agent": USER_AGENT,
        "extra_http_headers": {"Accept-Language": "en-US,en;q=0.9"},
    }
    # Proxy priority: argument > global env var
    proxy = parse_proxy(proxy_url or PROXY_URL)
    if proxy:
        kwargs["proxy"] = proxy
    context = await browser.new_context(**kwargs)
    sessions[session_id] = context
    logger.info("session.create | session=%s proxy=%s", session_id, _mask_proxy(proxy_url or PROXY_URL))
    return context


async def do_request(
    url: str,
    method: str = "GET",
    post_data: Optional[str] = None,
    headers: Optional[dict] = None,
    cookies: Optional[list] = None,
    timeout: Optional[int] = None,
    session: Optional[str] = None,
    screenshot: bool = False,
    only_cookies: bool = False,
    wait_seconds: int = 0,
    js_code: Optional[str] = None,
    capture_headers: Optional[list] = None,
) -> dict:
    t0 = time.monotonic()
    logger.info("%s %s | session=%s capture=%s", method.upper(), url, session, capture_headers or [])
    effective_timeout = timeout or MAX_TIMEOUT
    own_context = False

    if session:
        context = await get_or_create_session(session)
    else:
        browser = await get_browser()
        kwargs: dict = {
            "user_agent": USER_AGENT,
            "extra_http_headers": {"Accept-Language": "en-US,en;q=0.9"},
        }
        proxy = parse_proxy(PROXY_URL)
        if proxy:
            kwargs["proxy"] = proxy
        context = await browser.new_context(**kwargs)
        own_context = True

    if cookies:
        await context.add_cookies(cookies)

    page = await context.new_page()
    await page.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    captured_status: Optional[int] = None
    captured_headers: dict = {}
    captured_auth: dict = {}  # authorization e outros tokens capturados dos sub-requests
    base_url = url.split("?")[0]

    async def on_response(response):
        nonlocal captured_status, captured_headers
        try:
            resp_headers = await response.all_headers()
            if response.url == url or response.url.startswith(base_url):
                if captured_status is None or response.url == url:
                    captured_status = response.status
                    captured_headers = resp_headers
            if capture_headers:
                for key in (k.lower() for k in capture_headers):
                    value = resp_headers.get(key)
                    if value:
                        captured_auth[key] = value
        except Exception as e:
            logger.warning("on_response error: %s", e)

    def on_request(request):
        try:
            req_headers = request.headers
            fixed = ("authorization", "x-api-key", "x-auth-token", "x-access-token")
            keys = set(fixed) | {k.lower() for k in (capture_headers or [])}
            for key in keys:
                value = req_headers.get(key)
                if value:
                    captured_auth[key] = value
        except Exception as e:
            logger.warning("on_request error: %s", e)

    page.on("response", on_response)
    page.on("request", on_request)

    try:
        if method.upper() == "POST":
            async def handle_route(route):
                await route.continue_(
                    method="POST",
                    post_data=post_data or "",
                    headers={**route.request.headers, **(headers or {})},
                )
            await page.route(url, handle_route)
        elif headers:
            await page.set_extra_http_headers(headers)

        await page.goto(url, timeout=effective_timeout, wait_until="load")

        if wait_seconds > 0:
            await page.wait_for_timeout(wait_seconds * 1000)

        js_result = None
        if js_code:
            try:
                js_result = await page.evaluate(js_code)
            except Exception as e:
                logger.warning("javaScript eval error: %s", e)

        final_url = page.url
        final_cookies = await context.cookies()
        user_agent = await page.evaluate("() => navigator.userAgent")

        if only_cookies:
            return {
                "status": "ok",
                "message": "",
                "startTimestamp": int(time.time() * 1000),
                "solution": {
                    "url": final_url,
                    "status": captured_status or 200,
                    "headers": {},
                    "response": "",
                    "cookies": final_cookies,
                    "userAgent": user_agent,
                    "title": "",
                    "screenshot": None,
                    "javaScriptResult": js_result,
                },
            }

        html = await page.content()
        final_title = await page.title()

        screenshot_b64: Optional[str] = None
        if screenshot:
            png = await page.screenshot(full_page=True)
            screenshot_b64 = base64.b64encode(png).decode()

        merged_headers = {**captured_headers, **captured_auth}
        elapsed = time.monotonic() - t0
        logger.info(
            "%s %s | status=%s tokens=%s screenshot=%s %.1fs",
            method.upper(), url, captured_status, list(captured_auth.keys()), screenshot, elapsed,
        )

        return {
            "status": "ok",
            "message": "",
            "startTimestamp": int(time.time() * 1000),
            "solution": {
                "url": final_url,
                "status": captured_status or 200,
                "headers": merged_headers,
                "response": html,
                "cookies": final_cookies,
                "userAgent": user_agent,
                "title": final_title,
                "screenshot": screenshot_b64,
                "javaScriptResult": js_result,
            },
        }
    finally:
        await page.close()
        if own_context:
            await context.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_browser()
    proxy_info = f"PROXY={PROXY_URL}" if PROXY_URL else "PROXY=none"
    logger.info("Browser ready | port=%d headless=%s %s", PORT, HEADLESS, proxy_info)
    yield
    if sessions:
        logger.info("Shutdown: closing %d active session(s)", len(sessions))
    for sid, ctx in list(sessions.items()):
        try:
            await ctx.close()
            logger.info("session.destroy | session=%s reason=shutdown", sid)
        except Exception as e:
            logger.warning("session.destroy failed | session=%s error=%s", sid, e)
    if _browser:
        try:
            await _browser.close()
        except Exception:
            pass
    if _playwright:
        try:
            await _playwright.stop()
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


@app.get("/")
async def status():
    return {
        "msg": "HeaderHarvest is running",
        "version": "1.0.0",
        "proxy": PROXY_URL or None,
    }


@app.post("/v1")
async def handle_v1(request: Request):
    body = await request.json()
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
            )

        if cmd == "sessions.create":
            session_id = body.get("session") or f"session_{int(time.time() * 1000)}"
            # proxy field here overrides the global PROXY_URL for this session
            await get_or_create_session(session_id, proxy_url=body.get("proxy"))
            return {"status": "ok", "session": session_id}

        if cmd == "sessions.list":
            return {"status": "ok", "sessions": list(sessions.keys())}

        if cmd == "sessions.destroy":
            session_id = body.get("session")
            if not session_id:
                return JSONResponse(status_code=400, content={"status": "error", "message": "Missing session"})
            if session_id in sessions:
                ctx = sessions.pop(session_id)
                await ctx.close()
                logger.info("session.destroy | session=%s", session_id)
                return {"status": "ok"}
            return JSONResponse(status_code=404, content={"status": "error", "message": "Session not found"})

        return JSONResponse(status_code=400, content={"status": "error", "message": f"Unknown cmd: {cmd}"})

    except Exception as e:
        logger.error("cmd=%s: %s\n%s", cmd, e, traceback.format_exc())
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


if __name__ == "__main__":
    logger.info("HeaderHarvest starting | port=%d headless=%s timeout=%dms", PORT, HEADLESS, MAX_TIMEOUT)
    if PROXY_URL:
        logger.info("Global proxy: %s", PROXY_URL)
    uvicorn.run(app, host="0.0.0.0", port=PORT)
