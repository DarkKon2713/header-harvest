import logging
import requests
from json import JSONDecodeError
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

DEFAULT_SERVER = "http://localhost:9191/v1"


class HeaderHarvest:
    """Python client for the HeaderHarvest API."""

    HEADER: Dict[str, Any] = {"Content-Type": "application/json"}

    def __init__(self, server: str = DEFAULT_SERVER, name: str = ""):
        self.SERVER = server
        self.session = requests.Session()
        self.session.headers.update(self.HEADER)
        self.name = name

    # ------------------------------------------------------------------ #
    #  Sessions                                                            #
    # ------------------------------------------------------------------ #

    def create_session(self, proxy: Optional[str] = None) -> str:
        session_id = self.name + str(uuid4())
        data: Dict[str, Any] = {
            "cmd": "sessions.create",
            "session": session_id,
        }
        if proxy:
            data["proxy"] = proxy

        self._post(data)
        logger.info("Session created: %s", session_id)
        return session_id

    def list_sessions(self) -> List[str]:
        response = self._post({"cmd": "sessions.list"})
        return response.get("sessions", [])

    def session_destroyer(self, session_id: Optional[str] = None) -> None:
        if not session_id:
            return
        if self.name and self.name not in session_id:
            logger.warning("session_destroyer: %s does not belong to this client", session_id)
            return
        self._post({"cmd": "sessions.destroy", "session": session_id})
        logger.info("Session destroyed: %s", session_id)

    # ------------------------------------------------------------------ #
    #  Requests                                                            #
    # ------------------------------------------------------------------ #

    def get(
        self,
        url: str,
        session_id: str,
        cookies: Optional[List[Dict[str, str]]] = None,
        max_timeout: int = 60000,
        screenshot: bool = False,
        only_cookies: bool = False,
        wait_seconds: int = 0,
        js_code: Optional[str] = None,
        capture_headers: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "cmd": "request.get",
            "url": url,
            "session": session_id,
            "maxTimeout": max_timeout,
            "returnScreenshot": screenshot,
            "returnOnlyCookies": only_cookies,
            "waitInSeconds": wait_seconds,
        }
        if js_code:
            data["javaScript"] = js_code
        if cookies:
            data["cookies"] = cookies
        if capture_headers:
            data["captureHeaders"] = capture_headers

        logger.debug("GET %s (session=%s)", url, session_id)
        return self._post(data)

    def post(
        self,
        url: str,
        session_id: str,
        post_data: str = "",
        headers: Optional[Dict[str, str]] = None,
        max_timeout: int = 60000,
        screenshot: bool = False,
        only_cookies: bool = False,
        wait_seconds: int = 0,
        js_code: Optional[str] = None,
        capture_headers: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "cmd": "request.post",
            "url": url,
            "session": session_id,
            "postData": post_data,
            "maxTimeout": max_timeout,
            "returnScreenshot": screenshot,
            "returnOnlyCookies": only_cookies,
            "waitInSeconds": wait_seconds,
        }
        if js_code:
            data["javaScript"] = js_code
        if headers:
            data["headers"] = headers
        if capture_headers:
            data["captureHeaders"] = capture_headers

        logger.debug("POST %s (session=%s)", url, session_id)
        return self._post(data)

    # ------------------------------------------------------------------ #
    #  Internal                                                            #
    # ------------------------------------------------------------------ #

    def _post(self, data: Dict[str, Any], timeout: int = 120) -> Dict[str, Any]:
        try:
            r = self.session.post(self.SERVER, json=data, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except JSONDecodeError as e:
            logger.error("Response is not valid JSON: %s", e)
            raise
        except requests.HTTPError as e:
            body = e.response.text if e.response else ""
            logger.error("HTTP %s — %s", e.response.status_code if e.response else "?", body or "(empty body)")
            raise
        except requests.Timeout:
            logger.warning("Request timeout: cmd=%s", data.get("cmd"))
            raise
        except requests.RequestException as e:
            logger.error("Network error: %s", e)
            raise
