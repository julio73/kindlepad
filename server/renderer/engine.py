"""Render engine: composites the full two-panel landscape dashboard image."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from io import BytesIO
from typing import Optional

from PIL import Image, ImageDraw

from server.config import ScreenConfig
from server.touchmap import TouchMap

from .components import (
    draw_brightness_control,
    draw_departure_row,
    draw_footer,
    draw_header,
    draw_light_group,
    draw_music_section,
    draw_no_data_row,
    draw_power_button,
    draw_room_header,
    draw_section_header,
    draw_tfl_row,
    draw_vertical_divider,
    draw_weather,
)
from .theme import (
    BETWEEN_SECTIONS,
    BG,
    DIVIDER_X,
    PADDING,
    PANEL_GAP,
    SECTION_GAP,
    font_display,
)


@dataclass
class DashboardData:
    """All inputs for a single dashboard render, bundled to keep the panel
    helpers below the parameter limit.

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

    lights: list[dict] = field(default_factory=list)
    tfl_statuses: list[dict] = field(default_factory=list)
    departures: list[dict] = field(default_factory=list)
    current_time: str = ""
    current_date: str = ""
    weather: Optional[dict] = None
    battery_pct: Optional[int] = None
    is_charging: bool = False
    station_name: Optional[str] = None
    sonos: Optional[dict] = None
    brightness_level: int = 2
    lights_stale: bool = False
    tfl_stale: bool = False
    weather_stale: bool = False
    sonos_stale: bool = False
    # "HH:MM" of the last successful fetch per source (None = never succeeded);
    # only rendered when the matching *_stale flag is set.
    lights_since: Optional[str] = None
    tfl_since: Optional[str] = None
    weather_since: Optional[str] = None
    sonos_since: Optional[str] = None


def offline_marker(since: Optional[str]) -> str:
    """Marker text for a stale panel: age when known, bare 'offline' otherwise."""
    return f"offline since {since}" if since else "offline"


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
        sonos: Optional[dict] = None,
        brightness_level: int = 2,
        lights_stale: bool = False,
        tfl_stale: bool = False,
        weather_stale: bool = False,
        sonos_stale: bool = False,
        lights_since: Optional[str] = None,
        tfl_since: Optional[str] = None,
        weather_since: Optional[str] = None,
        sonos_since: Optional[str] = None,
    ) -> tuple[bytes, TouchMap]:
        """Render the full two-panel dashboard and return (png_bytes, touchmap)."""
        data = DashboardData(
            lights=lights,
            tfl_statuses=tfl_statuses,
            departures=departures,
            current_time=current_time,
            current_date=current_date,
            weather=weather,
            battery_pct=battery_pct,
            is_charging=is_charging,
            station_name=station_name,
            sonos=sonos,
            brightness_level=brightness_level,
            lights_stale=lights_stale,
            tfl_stale=tfl_stale,
            weather_stale=weather_stale,
            sonos_stale=sonos_stale,
            lights_since=lights_since,
            tfl_since=tfl_since,
            weather_since=weather_since,
            sonos_since=sonos_since,
        )

        img = Image.new("L", (self.width, self.height), BG)
        draw = ImageDraw.Draw(img)
        touchmap = TouchMap()

        header_bottom = self._draw_chrome(draw, touchmap, data)

        left_x = PADDING
        left_width = DIVIDER_X - PANEL_GAP - PADDING
        right_x = DIVIDER_X + PANEL_GAP
        right_width = self.width - PADDING - right_x

        self._draw_left_panel(draw, data, left_x, left_width, header_bottom)
        self._draw_right_panel(
            draw, touchmap, data, right_x, right_width, header_bottom
        )

        draw_vertical_divider(draw, DIVIDER_X, header_bottom, self.height - PADDING)

        # Rotate 90 degrees clockwise for portrait framebuffer display.
        # The Kindle screen is physically 758x1024 portrait, so we render
        # landscape (1024x758) then rotate to fit.
        img_rotated = img.rotate(-90, expand=True)

        buf = BytesIO()
        img_rotated.save(buf, format="PNG")
        png_bytes = buf.getvalue()

        # Touch coordinates from the Kindle arrive in the rotated (portrait)
        # coordinate space; the touchmap maps them back to the landscape layout.
        touchmap._rotation = (self.width, self.height)

        return png_bytes, touchmap

    def _draw_chrome(
        self,
        draw: ImageDraw.ImageDraw,
        touchmap: TouchMap,
        data: DashboardData,
    ) -> int:
        """Draw the header, power button, and brightness stepper.

        Returns the y position below the header separator.
        """
        header_bottom = draw_header(
            draw, "KindlePad", data.current_time, data.current_date, self.width, PADDING
        )

        # Power/sleep button in header area, right of title
        title_bbox = draw.textbbox((0, 0), "KINDLEPAD", font=font_display)
        title_w = title_bbox[2] - title_bbox[0]
        power_x = PADDING + title_w + 16
        touchmap.add(draw_power_button(draw, power_x, PADDING + 10))

        # Brightness stepper to the right of the power button
        for zone in draw_brightness_control(
            draw, power_x + 58, PADDING + 6, data.brightness_level
        ):
            touchmap.add(zone)

        return header_bottom

    def _draw_left_panel(
        self,
        draw: ImageDraw.ImageDraw,
        data: DashboardData,
        x: int,
        width: int,
        top: int,
    ) -> None:
        """Draw departures, line status, and the footer in the left panel."""
        ly = top

        # A stale-but-configured section still renders (header + marker +
        # placeholder) so a dead source never silently vanishes from the layout.
        if data.departures or (data.tfl_stale and data.station_name):
            header_label = "NEXT TRAINS"
            if data.tfl_stale:
                header_label += f" · {offline_marker(data.tfl_since)}"
            elif data.station_name:
                header_label += f" · {data.station_name}"
            ly = draw_section_header(draw, header_label, x, ly)
            if data.departures:
                for dep in data.departures[:5]:
                    ly = draw_departure_row(draw, dep, x, ly, width)
            else:
                ly = draw_no_data_row(draw, x, ly)
            ly += BETWEEN_SECTIONS

        if data.tfl_statuses or data.tfl_stale:
            label = "LINE STATUS"
            if data.tfl_stale:
                label += f" · {offline_marker(data.tfl_since)}"
            ly = draw_section_header(draw, label, x, ly)
            if data.tfl_statuses:
                for status in data.tfl_statuses:
                    ly = draw_tfl_row(draw, status, x, ly, width)
            else:
                ly = draw_no_data_row(draw, x, ly)

        # Subtle time-only footer at the bottom of the left panel
        footer_y = max(ly + SECTION_GAP, self.height - 44)
        draw_footer(
            draw,
            data.current_time,
            x,
            footer_y,
            width,
            battery_pct=data.battery_pct,
            is_charging=data.is_charging,
        )

    def _draw_right_panel(
        self,
        draw: ImageDraw.ImageDraw,
        touchmap: TouchMap,
        data: DashboardData,
        x: int,
        width: int,
        top: int,
    ) -> None:
        """Draw music, lights, and weather in the right panel."""
        ry = top

        # Music at the top (above lights)
        if data.sonos is not None:
            ry, music_zones = draw_music_section(
                draw,
                data.sonos,
                x,
                ry,
                width,
                stale=data.sonos_stale,
                stale_since=data.sonos_since,
            )
            for zone in music_zones:
                touchmap.add(zone)
            ry += BETWEEN_SECTIONS

        if data.lights or data.lights_stale:
            label = "LIGHTS"
            if data.lights_stale:
                label += f" · {offline_marker(data.lights_since)}"
            ry = draw_section_header(draw, label, x, ry)

            if not data.lights:
                ry = draw_no_data_row(draw, x, ry)

            # Group lights by room, preserving insertion order
            rooms: OrderedDict[str, list[dict]] = OrderedDict()
            for light in data.lights:
                rooms.setdefault(light.get("room", "Other"), []).append(light)

            room_items = list(rooms.items())
            for i, (room_name, room_lights) in enumerate(room_items):
                ry = draw_room_header(draw, room_name, x, ry)
                ry, zones = draw_light_group(draw, room_lights, x, ry, width)
                for zone in zones:
                    touchmap.add(zone)
                if i < len(room_items) - 1:
                    ry += SECTION_GAP // 2  # within-section: between rooms

        # Weather pinned to the bottom of the right panel.
        # NOTE: the right panel doesn't paginate — with enough rooms/lights the
        # light list can collide with this block and content past the bottom edge
        # is clipped. Fine for the current device's light count; revisit if the
        # config grows large.
        if data.weather is not None or data.weather_stale:
            weather_y = max(ry + BETWEEN_SECTIONS, self.height - 110)
            draw_weather(
                draw,
                data.weather,
                x,
                weather_y,
                width,
                stale=data.weather_stale,
                stale_since=data.weather_since,
            )
