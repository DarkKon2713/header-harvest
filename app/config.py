import os

PORT = int(os.environ.get("PORT", 9191))
HEADLESS = os.environ.get("HEADLESS", "false").lower() != "false"
MAX_TIMEOUT = int(os.environ.get("MAX_TIMEOUT", 60000))
MAX_CONCURRENT = int(os.environ.get("MAX_CONCURRENT", 100))
PROXY_URL = os.environ.get("PROXY_URL", "")

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
VALID_WAIT_UNTIL = {"load", "domcontentloaded", "networkidle", "commit"}
