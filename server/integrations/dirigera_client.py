"""Wrapper around the dirigera library for IKEA smart home control."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional

import dirigera

logger = logging.getLogger(__name__)


@dataclass
class LightState:
    id: str
    name: str
    is_on: bool
    brightness: int  # 0-100
    reachable: bool


class DirigeraClient:
    """Client for controlling IKEA lights via a local Dirigera hub."""

    def __init__(self, hub_ip: str, token: str, device_ids: list[str], name_map: Optional[dict[str, str]] = None):
        self.hub = dirigera.Hub(token=token, ip_address=hub_ip)
        self.device_ids = device_ids
        self._name_map = name_map or {}
        self._cache: list[LightState] = []
        self._cache_time: float = 0.0

    def _invalidate_cache(self):
        self._cache_time = 0.0

    def get_lights(self) -> list[LightState]:
        """Fetch light states from hub, cached for 5 seconds."""
        now = time.monotonic()
        if self._cache and (now - self._cache_time) < 5.0:
            return self._cache

        try:
            raw_lights = self.hub.get_lights()
        except Exception:
            logger.warning("Failed to reach Dirigera hub", exc_info=True)
            return self._cache if self._cache else []

        id_set = set(self.device_ids)
        results: list[LightState] = []
        for light in raw_lights:
            if light.id not in id_set:
                continue
            results.append(
                LightState(
                    id=light.id,
                    name=self._name_map.get(light.id, light.attributes.custom_name),
                    is_on=light.attributes.is_on,
                    brightness=light.attributes.light_level or 0,
                    reachable=light.is_reachable,
                )
            )

        self._cache = results
        self._cache_time = now
        return results

    def _find_raw_light(self, device_id: str):
        """Find a raw dirigera Light object by ID."""
        lights = self.hub.get_lights()
        for light in lights:
            if light.id == device_id:
                return light
        raise ValueError(f"Light {device_id!r} not found on hub")

    def toggle(self, device_id: str) -> bool:
        """Toggle a light's on/off state. Returns the new is_on state."""
        light = self._find_raw_light(device_id)
        new_state = not light.attributes.is_on
        light.set_light(lamp_on=new_state)
        self._invalidate_cache()
        return new_state

    def set_on(self, device_id: str, on: bool):
        """Set a light explicitly on or off."""
        light = self._find_raw_light(device_id)
        light.set_light(lamp_on=on)
        self._invalidate_cache()

    def all_off(self):
        """Turn off all configured lights."""
        try:
            raw_lights = self.hub.get_lights()
        except Exception:
            logger.warning("Failed to reach Dirigera hub for all_off", exc_info=True)
            return

        id_set = set(self.device_ids)
        for light in raw_lights:
            if light.id in id_set:
                try:
                    light.set_light(lamp_on=False)
                except Exception:
                    logger.warning(
                        "Failed to turn off light %s", light.id, exc_info=True
                    )
        self._invalidate_cache()
