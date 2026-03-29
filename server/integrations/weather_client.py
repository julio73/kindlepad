"""Weather integration using the free Open-Meteo API."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

import httpx


@dataclass
class WeatherData:
    temperature: float      # current temp in °C
    high: float             # today's high
    low: float              # today's low
    rain_chance: int        # precipitation probability %
    condition_code: int     # WMO weather code
    condition_text: str     # human readable condition


# WMO weather code -> human readable condition text
_WMO_CODE_MAP: dict[int, str] = {
    0: "Clear",
    1: "Partly Cloudy",
    2: "Cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Foggy",
    51: "Drizzle",
    53: "Drizzle",
    55: "Drizzle",
    56: "Drizzle",
    57: "Drizzle",
    61: "Rain",
    63: "Rain",
    65: "Rain",
    66: "Rain",
    67: "Rain",
    71: "Snow",
    73: "Snow",
    75: "Snow",
    77: "Snow",
    80: "Showers",
    81: "Showers",
    82: "Showers",
    85: "Snow Showers",
    86: "Snow Showers",
    95: "Thunderstorm",
    96: "Thunderstorm",
    99: "Thunderstorm",
}


def _code_to_text(code: int) -> str:
    """Map a WMO weather code to a human-readable condition string."""
    if code in _WMO_CODE_MAP:
        return _WMO_CODE_MAP[code]
    # Fallback ranges
    if 1 <= code <= 3:
        return "Cloudy"
    if 45 <= code <= 48:
        return "Foggy"
    if 51 <= code <= 57:
        return "Drizzle"
    if 61 <= code <= 67:
        return "Rain"
    if 71 <= code <= 77:
        return "Snow"
    if 80 <= code <= 82:
        return "Showers"
    if 85 <= code <= 86:
        return "Snow Showers"
    if 95 <= code <= 99:
        return "Thunderstorm"
    return "Unknown"


class WeatherClient:
    """Fetches current weather data from the Open-Meteo API (no key required)."""

    _CACHE_TTL = 600  # 10 minutes in seconds

    def __init__(self, latitude: float, longitude: float) -> None:
        self.latitude = latitude
        self.longitude = longitude
        self._cached: Optional[WeatherData] = None
        self._cached_at: float = 0.0

    def get_weather(self) -> Optional[WeatherData]:
        """Return current weather data, cached for 10 minutes.

        Returns None if the API call fails and no cached data is available.
        """
        now = time.monotonic()
        if self._cached is not None and (now - self._cached_at) < self._CACHE_TTL:
            return self._cached

        try:
            data = self._fetch()
            self._cached = data
            self._cached_at = now
            return data
        except Exception:
            # Return stale cache if available, otherwise None
            return self._cached

    def _fetch(self) -> WeatherData:
        """Make the actual HTTP request to Open-Meteo."""
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={self.latitude}"
            f"&longitude={self.longitude}"
            "&current=temperature_2m,weather_code"
            "&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max"
            "&timezone=Europe/London"
            "&forecast_days=1"
        )
        response = httpx.get(url, timeout=10.0)
        response.raise_for_status()
        payload = response.json()

        current = payload["current"]
        daily = payload["daily"]

        code = int(current["weather_code"])
        return WeatherData(
            temperature=float(current["temperature_2m"]),
            high=float(daily["temperature_2m_max"][0]),
            low=float(daily["temperature_2m_min"][0]),
            rain_chance=int(daily["precipitation_probability_max"][0]),
            condition_code=code,
            condition_text=_code_to_text(code),
        )
