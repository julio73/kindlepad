"""HTTP client for Transport for London (TfL) line status API."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

TFL_BASE_URL = "https://api.tfl.gov.uk/Line"


@dataclass
class LineStatus:
    id: str
    name: str
    severity: int  # 10 = Good Service
    status_text: str  # "Good Service", "Minor Delays", etc.
    disruption_reason: Optional[str]  # reason text if disrupted


def _parse_statuses(data: list[dict]) -> list[LineStatus]:
    """Parse TfL JSON response into LineStatus objects."""
    results: list[LineStatus] = []
    for item in data:
        line_statuses = item.get("lineStatuses", [])
        if line_statuses:
            status = line_statuses[0]
            severity = status.get("statusSeverity", 0)
            status_text = status.get("statusSeverityDescription", "Unknown")
            reason = status.get("reason")
        else:
            severity = 0
            status_text = "Unknown"
            reason = None

        results.append(
            LineStatus(
                id=item["id"],
                name=item["name"],
                severity=severity,
                status_text=status_text,
                disruption_reason=reason,
            )
        )
    return results


class TflClient:
    """Client for fetching TfL tube line statuses."""

    def __init__(self, lines: list[dict], refresh_interval: int = 120):
        self.lines = lines
        self.refresh_interval = refresh_interval
        self._cache: list[LineStatus] = []
        self._cache_time: float = 0.0

    def _build_url(self) -> str:
        ids = ",".join(line["id"] for line in self.lines)
        return f"{TFL_BASE_URL}/{ids}/Status"

    def _is_cache_valid(self) -> bool:
        return bool(self._cache) and (
            time.monotonic() - self._cache_time < self.refresh_interval
        )

    async def get_statuses(self) -> list[LineStatus]:
        """Fetch line statuses asynchronously via httpx. Cached per refresh_interval."""
        if self._is_cache_valid():
            return self._cache

        url = self._build_url()
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=10.0)
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            logger.warning("TfL async request failed", exc_info=True)
            return self._cache if self._cache else []

        self._cache = _parse_statuses(data)
        self._cache_time = time.monotonic()
        return self._cache

    def get_statuses_sync(self) -> list[LineStatus]:
        """Fetch line statuses synchronously via httpx. Cached per refresh_interval."""
        if self._is_cache_valid():
            return self._cache

        url = self._build_url()
        try:
            with httpx.Client() as client:
                resp = client.get(url, timeout=10.0)
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            logger.warning("TfL sync request failed", exc_info=True)
            return self._cache if self._cache else []

        self._cache = _parse_statuses(data)
        self._cache_time = time.monotonic()
        return self._cache
