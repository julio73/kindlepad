"""Render engine: composites the full two-panel landscape dashboard image."""

from __future__ import annotations

from collections import OrderedDict
from io import BytesIO

from PIL import Image, ImageDraw

from server.config import ScreenConfig
from server.touchmap import TouchMap

from .components import (
    draw_brightness_bar,
    draw_departure_row,
    draw_footer,
    draw_header,
    draw_light_row,
    draw_room_header,
    draw_section_header,
    draw_tfl_row,
    draw_vertical_divider,
)
from .theme import BG, DIVIDER_X, PADDING, PANEL_GAP, SECTION_GAP


class RenderEngine:
    """Renders the KindlePad dashboard as a 1024x758 grayscale PNG."""

    def __init__(self, screen: ScreenConfig):
        self.width = screen.width
        self.height = screen.height

    def render_dashboard(
        self,
        lights: list[dict],
        tfl_statuses: list[dict],
        departures: list[dict],
        current_time: str,
        current_date: str,
        brightness_level: int = 2,
    ) -> tuple[bytes, TouchMap]:
        """Render the full two-panel dashboard and return (png_bytes, touchmap).

        Parameters
        ----------
        lights:
            List of dicts with keys: id, name, is_on, room.
        tfl_statuses:
            List of dicts with keys: name, status_text, severity.
        departures:
            List of dicts with keys: minutes, destination, direction.
        current_time:
            Formatted time string, e.g. "04:35".
        current_date:
            Formatted date string, e.g. "Sat 29 Mar".
        """
        img = Image.new("L", (self.width, self.height), BG)
        draw = ImageDraw.Draw(img)
        touchmap = TouchMap()

        y = PADDING

        # --- Header (full width) ---
        y = draw_header(
            draw, "KindlePad", current_time, current_date, self.width, y
        )
        header_bottom = y

        # --- Panel geometry ---
        left_x = PADDING
        left_width = DIVIDER_X - PANEL_GAP - PADDING
        right_x = DIVIDER_X + PANEL_GAP
        right_width = self.width - PADDING - right_x

        # ============================================================
        # LEFT PANEL: Transit
        # ============================================================
        ly = header_bottom

        # Departures section
        if departures:
            ly = draw_section_header(
                draw, "NEXT TRAINS \u00b7 Your Station", left_x, ly
            )
            for dep in departures[:5]:
                ly = draw_departure_row(
                    draw,
                    minutes=dep["minutes"],
                    destination=dep["destination"],
                    direction=dep["direction"],
                    x=left_x,
                    y=ly,
                    width=left_width,
                )
            ly += SECTION_GAP

        # TfL line status section
        if tfl_statuses:
            ly = draw_section_header(draw, "LINE STATUS", left_x, ly)
            for status in tfl_statuses:
                ly = draw_tfl_row(
                    draw,
                    line_name=status["name"],
                    status_text=status["status_text"],
                    severity=status["severity"],
                    x=left_x,
                    y=ly,
                    width=left_width,
                )

        # Footer at the bottom of the left panel
        footer_y = max(ly + SECTION_GAP, self.height - 50)
        draw_footer(draw, current_time, left_x, footer_y, left_width)

        # ============================================================
        # RIGHT PANEL: Lights
        # ============================================================
        ry = header_bottom

        if lights:
            ry = draw_section_header(draw, "LIGHTS", right_x, ry)

            # Group lights by room, preserving insertion order
            rooms: OrderedDict[str, list[dict]] = OrderedDict()
            for light in lights:
                room = light.get("room", "Other")
                rooms.setdefault(room, []).append(light)

            for room_name, room_lights in rooms.items():
                ry = draw_room_header(draw, room_name, right_x, ry)
                for light in room_lights:
                    ry, zone = draw_light_row(
                        draw,
                        name=light["name"],
                        is_on=light["is_on"],
                        device_id=light["id"],
                        x=right_x,
                        y=ry,
                        width=right_width,
                    )
                    touchmap.add(zone)
                ry += SECTION_GAP // 2

        # Brightness control at bottom of right panel
        bright_y = max(ry + SECTION_GAP, self.height - 80)
        bright_y, bright_zones = draw_brightness_bar(
            draw, brightness_level, right_x, bright_y, right_width
        )
        for zone in bright_zones:
            touchmap.add(zone)

        # ============================================================
        # Vertical divider
        # ============================================================
        draw_vertical_divider(draw, DIVIDER_X, header_bottom, self.height - PADDING)

        # Rotate 90° clockwise for portrait framebuffer display.
        # The Kindle screen is physically 758x1024 portrait, so we render
        # landscape (1024x758) then rotate to fit.
        img_rotated = img.rotate(-90, expand=True)

        # Encode to PNG
        buf = BytesIO()
        img_rotated.save(buf, format="PNG")
        png_bytes = buf.getvalue()

        # Touch coordinates from the Kindle will be in the rotated (portrait)
        # coordinate space. We need to map them back to our landscape layout.
        # Rotated image is 758x1024. A tap at (rx, ry) in rotated space
        # maps to (ry, 758 - rx) in our landscape layout.
        touchmap._rotation = (self.width, self.height)

        return png_bytes, touchmap
