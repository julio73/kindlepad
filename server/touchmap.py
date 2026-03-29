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
        # Set by engine when image is rotated for display.
        # Tuple of (landscape_width, landscape_height) or None.
        self._rotation: tuple[int, int] | None = None

    def add(self, zone: TouchZone):
        self.zones.append(zone)

    def resolve(self, x: int, y: int) -> TouchZone | None:
        """Find zone containing (x,y). Last match wins (highest z-order).

        If the image was rotated 90° clockwise for display, incoming
        coordinates are in the rotated (portrait) space and need mapping
        back to the original landscape layout.
        """
        if self._rotation is not None:
            # Image was rotated -90° (clockwise). The rotated image is
            # (height x width). A tap at (rx, ry) in rotated space maps
            # to landscape (lx, ly) = (ry, height - rx) where height is
            # the landscape height (short side, 758).
            _lw, lh = self._rotation
            lx, ly = y, lh - x
            x, y = lx, ly

        result = None
        for zone in self.zones:
            if (zone.x <= x <= zone.x + zone.width
                    and zone.y <= y <= zone.y + zone.height):
                result = zone
        return result
