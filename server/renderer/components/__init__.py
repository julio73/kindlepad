"""Drawing components for the KindlePad two-panel landscape dashboard.

Editorial utilitarian style: high contrast, typographically-driven.
Every mark is deliberate.

Components are grouped by domain into submodules; this package re-exports the
public drawing helpers consumed by the render engine.
"""

from __future__ import annotations

from .layout import (
    draw_footer,
    draw_header,
    draw_no_data_row,
    draw_room_header,
    draw_section_header,
    draw_vertical_divider,
)
from .lights import (
    draw_brightness_control,
    draw_light_button,
    draw_light_group,
    draw_power_button,
)
from .music import draw_music_section
from .transit import draw_departure_row, draw_tfl_row
from .weather import draw_weather

__all__ = [
    "draw_brightness_control",
    "draw_departure_row",
    "draw_footer",
    "draw_header",
    "draw_light_button",
    "draw_light_group",
    "draw_music_section",
    "draw_no_data_row",
    "draw_power_button",
    "draw_room_header",
    "draw_section_header",
    "draw_tfl_row",
    "draw_vertical_divider",
    "draw_weather",
]
