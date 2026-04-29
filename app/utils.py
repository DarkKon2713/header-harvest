from typing import Optional
from urllib.parse import urlparse


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
        server = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"
        proxy: dict = {"server": server}
        if parsed.username:
            proxy["username"] = parsed.username
        if parsed.password:
            proxy["password"] = parsed.password
        return proxy
    return {"server": proxy_url.rstrip("/")}


def mask_proxy(proxy_url) -> str:
    if not proxy_url:
        return "none"
    if isinstance(proxy_url, dict):
        server = proxy_url.get("server", "")
        return f"***@{server}" if proxy_url.get("username") else server
    parsed = urlparse(proxy_url)
    if parsed.password:
        return f"{parsed.scheme}://***@{parsed.hostname}:{parsed.port}"
    return proxy_url.rstrip("/")


def format_uptime(seconds: float) -> str:
    s = int(seconds)
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    parts = []
    if d:
        parts.append(f"{d}d")
    if h:
        parts.append(f"{h}h")
    if m:
        parts.append(f"{m}m")
    parts.append(f"{s}s")
    return " ".join(parts)
