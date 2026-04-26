"""Render engine: composites the full two-panel landscape dashboard image."""

from __future__ import annotations

from collections import OrderedDict
from io import BytesIO
from typing import Optional

from PIL import Image, ImageDraw

from server.config import ScreenConfig
from server.touchmap import TouchMap

from .components import (
    draw_departure_row,
    draw_footer,
    draw_header,
    draw_light_group,
    draw_power_button,
    draw_room_header,
    draw_section_header,
    draw_tfl_row,
    draw_vertical_divider,
    draw_weather,
)
from .theme import BG, DIVIDER_X, PADDING, PANEL_GAP, SECTION_GAP, font_display


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
        weather: Optional[dict] = None,
        battery_pct: Optional[int] = None,
        is_charging: bool = False,
        station_name: Optional[str] = None,
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
        weather:
            Optional dict with keys: temperature, high, low, rain_chance,
            condition_code, condition_text.
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

        # Power/sleep button in header area, right of title
        title_bbox = draw.textbbox((0, 0), "KINDLEPAD", font=font_display)
        title_w = title_bbox[2] - title_bbox[0]
        power_zone = draw_power_button(draw, PADDING + title_w + 16, PADDING + 10)
        touchmap.add(power_zone)

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
            header_label = "NEXT TRAINS"
            if station_name:
                header_label += f" \u00b7 {station_name}"
            ly = draw_section_header(draw, header_label, left_x, ly)
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

        # Subtle time-only footer at the bottom of the left panel
        footer_y = max(ly + SECTION_GAP, self.height - 44)
        draw_footer(draw, current_time, left_x, footer_y, left_width, battery_pct=battery_pct, is_charging=is_charging)

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
                ry, zones = draw_light_group(
                    draw, room_lights, right_x, ry, right_width,
                )
                for zone in zones:
                    touchmap.add(zone)
                ry += SECTION_GAP // 2

        # Weather at bottom of right panel
        if weather is not None:
            weather_y = max(ry + SECTION_GAP, self.height - 110)
            draw_weather(draw, weather, right_x, weather_y, right_width)

        # ============================================================
        # Vertical divider
        # ============================================================
        draw_vertical_divider(draw, DIVIDER_X, header_bottom, self.height - PADDING)

        # Rotate 90 degrees clockwise for portrait framebuffer display.
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
