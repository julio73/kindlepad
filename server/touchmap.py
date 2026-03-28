"""Touch zone mapping for Kindle e-ink touch input."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TouchZone:
    x: int
    y: int
    width: int
    height: int
    action: str
    params: dict = field(default_factory=dict)


class TouchMap:
    def __init__(self):
        self.zones: list[TouchZone] = []

    def add(self, zone: TouchZone):
        self.zones.append(zone)

    def resolve(self, x: int, y: int) -> TouchZone | None:
        """Find zone containing (x,y). Last match wins (highest z-order)."""
        result = None
        for zone in self.zones:
            if (zone.x <= x <= zone.x + zone.width
                    and zone.y <= y <= zone.y + zone.height):
                result = zone
        return result
