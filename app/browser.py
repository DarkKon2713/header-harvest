import base64
import logging
import time
from typing import Optional

from playwright.async_api import async_playwright, BrowserContext
from playwright_stealth import stealth_async

import app.state as state
from app.config import HEADLESS, LAUNCH_ARGS, MAX_TIMEOUT, PROXY_URL, USER_AGENT, VALID_WAIT_UNTIL
from app.utils import mask_proxy, parse_proxy

logger = logging.getLogger(__name__)


async def get_browser():
    if state.browser is None or not state.browser.is_connected():
        state.playwright = await async_playwright().start()
        state.browser = await state.playwright.chromium.launch(headless=HEADLESS, args=LAUNCH_ARGS)
    return state.browser


async def get_or_create_session(
    session_id: str,
    proxy_url: Optional[str] = None,
) -> BrowserContext:
    ctx = state.sessions.get(session_id)
    if ctx is not None:
        return ctx
    _browser = await get_browser()
    kwargs: dict = {
        "user_agent": USER_AGENT,
        "extra_http_headers": {"Accept-Language": "en-US,en;q=0.9"},
        "ignore_https_errors": True,
    }
    proxy = parse_proxy(proxy_url or PROXY_URL)
    if proxy:
        kwargs["proxy"] = proxy
    context = await _browser.new_context(**kwargs)
    state.sessions[session_id] = context
    state.session_meta[session_id] = {
        "proxy": mask_proxy(proxy_url or PROXY_URL),
        "createdAt": int(time.time() * 1000),
        "lastUsedAt": None,
        "lastUrl": None,
        "requestCount": 0,
    }
    logger.info("session.create | session=%s proxy=%s", session_id, mask_proxy(proxy_url or PROXY_URL))
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
    wait_until: str = "load",
    proxy_url: Optional[str] = None,
    block_resources: Optional[list] = None,
) -> dict:
    start_ts = int(time.time() * 1000)
    t0 = time.monotonic()
    logger.info("%s %s | session=%s capture=%s", method.upper(), url, session, capture_headers or [])
    effective_timeout = timeout or MAX_TIMEOUT
    own_context = False

    if wait_until not in VALID_WAIT_UNTIL:
        raise ValueError(f"waitUntil must be one of {sorted(VALID_WAIT_UNTIL)}, got {wait_until!r}")

    async with state.semaphore:
        if session:
            context = await get_or_create_session(session)
        else:
            _browser = await get_browser()
            kwargs: dict = {
                "user_agent": USER_AGENT,
                "extra_http_headers": {"Accept-Language": "en-US,en;q=0.9"},
                "ignore_https_errors": True,
            }
            proxy = parse_proxy(proxy_url or PROXY_URL)
            if proxy:
                kwargs["proxy"] = proxy
            context = await _browser.new_context(**kwargs)
            own_context = True

        if cookies:
            await context.add_cookies(cookies)

        page = await context.new_page()
        await stealth_async(page)

        captured_status: Optional[int] = None
        captured_headers: dict = {}
        captured_auth: dict = {}
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
            if block_resources:
                blocked = {r.lower() for r in block_resources}

                async def handle_block(route):
                    if route.request.resource_type in blocked:
                        await route.abort()
                    else:
                        await route.continue_()

                await page.route("**/*", handle_block)

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

            await page.goto(url, timeout=effective_timeout, wait_until=wait_until)

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
                    "startTimestamp": start_ts,
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
                "startTimestamp": start_ts,
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
            elif session and session in state.session_meta:
                meta = state.session_meta[session]
                meta["lastUsedAt"] = int(time.time() * 1000)
                meta["lastUrl"] = url
                meta["requestCount"] = meta.get("requestCount", 0) + 1
