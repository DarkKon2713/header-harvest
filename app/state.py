import asyncio
from typing import Optional

from playwright.async_api import Browser, BrowserContext, Playwright

sessions: dict[str, BrowserContext] = {}
session_meta: dict[str, dict] = {}

browser: Optional[Browser] = None
playwright: Optional[Playwright] = None
semaphore: Optional[asyncio.Semaphore] = None
start_time: Optional[float] = None
