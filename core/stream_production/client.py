"""HTTP client for the Stream Production Status API (read-only GET /status)."""
import logging
from typing import Optional

import requests

import settings.config as config
from core.stream_production.models import StatusSnapshot

logger = logging.getLogger(__name__)


class StreamProductionClient:
    def __init__(self, base_url=None, api_key=None, verify_ssl=None, timeout=None):
        raw_base = base_url if base_url is not None else getattr(config, "STREAM_PRODUCTION_API_URL", "")
        base = (raw_base or "").rstrip("/")
        # Forgive a full ".../status" URL being pasted as the base.
        if base.lower().endswith("/status"):
            base = base[: -len("/status")]
        self.base_url = base
        self.api_key = (
            api_key if api_key is not None else getattr(config, "STREAM_PRODUCTION_API_KEY", "")
        )
        self.verify_ssl = (
            verify_ssl
            if verify_ssl is not None
            else getattr(config, "STREAM_PRODUCTION_VERIFY_SSL", True)
        )
        self.timeout = timeout or getattr(config, "STREAM_PRODUCTION_API_TIMEOUT_SECONDS", 5)

    def _headers(self):
        h = {"Accept": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def fetch_status(self, since: Optional[int] = None) -> Optional[StatusSnapshot]:
        """GET /status (optionally ?since=<seq>). Returns None on any failure.

        Failures are intentionally quiet (debug-level): a stale/offline producer
        is an expected state, not an error worth spamming the log.
        """
        if not self.base_url:
            return None
        url = f"{self.base_url}/status"
        params = {}
        if since:
            params["since"] = since
        try:
            r = requests.get(
                url,
                params=params,
                headers=self._headers(),
                timeout=self.timeout,
                verify=self.verify_ssl,
            )
            if r.status_code != 200:
                logger.debug(f"stream production /status HTTP {r.status_code}")
                return None
            return StatusSnapshot.from_json(r.json())
        except Exception as e:
            logger.debug(f"stream production /status error: {e}")
            return None

    def fetch_path_text(self, rel_path: str) -> Optional[str]:
        """GET an arbitrary path under the base URL, returning raw text (e.g. a CSV)."""
        if not self.base_url or not rel_path:
            return None
        url = f"{self.base_url}/{rel_path.lstrip('/')}"
        try:
            r = requests.get(
                url, headers=self._headers(), timeout=self.timeout, verify=self.verify_ssl
            )
            if r.status_code != 200:
                return None
            return r.text
        except Exception as e:
            logger.debug(f"stream production fetch_path_text error ({rel_path}): {e}")
            return None

    def fetch_path_json(self, rel_path: str) -> Optional[dict]:
        """GET an arbitrary JSON path under the base URL."""
        if not self.base_url or not rel_path:
            return None
        url = f"{self.base_url}/{rel_path.lstrip('/')}"
        try:
            r = requests.get(
                url, headers=self._headers(), timeout=self.timeout, verify=self.verify_ssl
            )
            if r.status_code != 200:
                return None
            return r.json()
        except Exception as e:
            logger.debug(f"stream production fetch_path_json error ({rel_path}): {e}")
            return None
