"""Render engine: composites the full dashboard image."""

from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageDraw

from server.config import ScreenConfig
from server.touchmap import TouchMap

from .components import (
    draw_footer,
    draw_header,
    draw_light_toggle,
    draw_section_header,
    draw_tfl_row,
)
from .theme import BG, PADDING, SECTION_GAP


class RenderEngine:
    """Renders the KindlePad dashboard as a grayscale PNG."""

    def __init__(self, screen: ScreenConfig):
        self.width = screen.width
        self.height = screen.height

    def render_dashboard(
        self,
        lights: list[dict],
        tfl_statuses: list[dict],
        current_time: str,
    ) -> tuple[bytes, TouchMap]:
        """Render the full dashboard and return (png_bytes, touchmap)."""
        img = Image.new("L", (self.width, self.height), BG)
        draw = ImageDraw.Draw(img)
        touchmap = TouchMap()

        y = PADDING

        # Header
        y = draw_header(draw, "KindlePad", current_time, y)

        # TfL section
        if tfl_statuses:
            y += SECTION_GAP
            y = draw_section_header(draw, "TfL Status", y)
            for status in tfl_statuses:
                y = draw_tfl_row(
                    draw,
                    line_name=status["name"],
                    status_text=status["status_text"],
                    severity=status["severity"],
                    y=y,
                )

        # Lights section
        if lights:
            y += SECTION_GAP
            y = draw_section_header(draw, "Lights", y)
            for light in lights:
                y, zones = draw_light_toggle(
                    draw,
                    name=light["name"],
                    is_on=light["is_on"],
                    device_id=light["id"],
                    y=y,
                )
                for zone in zones:
                    touchmap.add(zone)

        # Footer
        footer_y = max(y + SECTION_GAP, self.height - 80)
        draw_footer(draw, current_time, footer_y)

        # Encode to PNG
        buf = BytesIO()
        img.save(buf, format="PNG")
        png_bytes = buf.getvalue()

        return png_bytes, touchmap
