import base64
import json
import logging
import os
from datetime import datetime
from client import HeaderHarvest

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

BASE   = "http://localhost:9191/v1"
TARGET = "https://www.lg.com/br/monitores/monitores-ultrawide/?ec_model_status_code=ACTIVE"
PROXY  = ""

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")


def _slug(url: str) -> str:
    return url.split("//")[-1].split("/")[0].replace(".", "_")


def save_screenshot(b64: str, url: str) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(OUTPUT_DIR, f"{_slug(url)}_{ts}.png")
    with open(path, "wb") as f:
        f.write(base64.b64decode(b64))
    return path


def save_html(html: str, url: str) -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(OUTPUT_DIR, f"{_slug(url)}_{ts}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path


def print_section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_headers(headers: dict) -> None:
    if not headers:
        print("  (none)")
        return
    width = max(len(k) for k in headers)
    for k, v in sorted(headers.items()):
        print(f"  {k:<{width}}  {v}")


def print_cookies(cookies: list) -> None:
    if not cookies:
        print("  (none)")
        return
    for cookie in cookies:
        name   = cookie.get("name", "")
        value  = cookie.get("value", "")
        domain = cookie.get("domain", "-")
        print(f"  {name}={value} | domain={domain}")


def demo_basic_get(client: HeaderHarvest, session_id: str) -> None:
    """Basic GET — captures full response headers including intercepted auth tokens."""
    print_section("1. Basic GET + full header capture")
    res = client.get(TARGET, session_id)
    sol = res.get("solution", {})
    print(f"  URL    : {sol.get('url', '-')}")
    print(f"  Status : {sol.get('status', '-')}")
    print(f"  Title  : {sol.get('title', '-')}")

    headers = sol.get("headers", {})
    print(f"\n  --- Headers ({len(headers)}) ---")
    print_headers(headers)

    cookies = sol.get("cookies", [])
    print(f"\n  --- Cookies ({len(cookies)}) ---")
    print_cookies(cookies)


def demo_wait_and_js(client: HeaderHarvest, session_id: str) -> None:
    """waitInSeconds waits after page load for JS-rendered content, then captures.
    Combine with javaScript injection to extract structured data from the rendered page."""
    print_section("2. waitInSeconds (JS render) + JavaScript injection")
    js = "() => [...document.querySelectorAll('h2, h3')].slice(0, 5).map(e => e.innerText.trim())"
    res = client.get(TARGET, session_id, wait_seconds=3, js_code=js)
    sol = res.get("solution", {})
    js_result = sol.get("javaScriptResult")
    print(f"  JS result: {json.dumps(js_result, ensure_ascii=False, indent=4)}")


def demo_only_cookies(client: HeaderHarvest, session_id: str) -> None:
    """returnOnlyCookies — faster, skips body and headers."""
    print_section("3. returnOnlyCookies (fast)")
    res = client.get(TARGET, session_id, only_cookies=True)
    sol = res.get("solution", {})
    cookies = sol.get("cookies", [])
    print(f"  {len(cookies)} cookie(s) returned, no body fetched")
    print_cookies(cookies)


def demo_screenshot_and_html(client: HeaderHarvest, session_id: str) -> None:
    """GET with full-page screenshot + save HTML."""
    print_section("4. Screenshot + save HTML")
    res = client.get(TARGET, session_id, screenshot=True)
    sol = res.get("solution", {})

    html = sol.get("response", "")
    if html:
        path = save_html(html, sol.get("url", "page"))
        print(f"  HTML saved  : {path}")

    screenshot = sol.get("screenshot")
    if screenshot:
        path = save_screenshot(screenshot, sol.get("url", "page"))
        print(f"  Screenshot  : {path}")


def demo_js_title(client: HeaderHarvest, session_id: str) -> None:
    """JavaScript injection — return document.title."""
    print_section("5. JavaScript injection — document.title")
    res = client.get(TARGET, session_id, js_code="() => document.title")
    sol = res.get("solution", {})
    print(f"  JS result: {sol.get('javaScriptResult')}")


if __name__ == "__main__":
    client = HeaderHarvest(server=BASE)
    session_id = client.create_session(proxy=PROXY or None)

    try:
        demo_basic_get(client, session_id)
        demo_wait_and_js(client, session_id)
        demo_only_cookies(client, session_id)
        demo_screenshot_and_html(client, session_id)
        demo_js_title(client, session_id)

    except Exception as e:
        print(f"\nERROR: {e}")
    finally:
        client.session_destroyer(session_id)
