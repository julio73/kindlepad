"""Weather section: 3-column layout with condition-driven icons."""

from __future__ import annotations

import math

from PIL import ImageDraw

from ..theme import FG, GRAY_LIGHT, GRAY_MID, font_display, font_small

# Stroke width for the e-ink weather glyphs.
_STROKE = 3


def draw_weather(
    draw: ImageDraw.ImageDraw,
    weather: dict | None,
    x: int,
    y: int,
    width: int,
    stale: bool = False,
    stale_since: str | None = None,
) -> int:
    """Draw weather in 3-column layout: icon | temps | condition.

    When ``stale`` is set, an "offline" marker (with the time of the last
    successful fetch, when known) is drawn so a cached/failed reading isn't
    mistaken for live data. ``weather`` may be None when the source is down
    with nothing cached — the section still renders as a placeholder.

    Returns the y position below the weather section.
    """
    # Separator above weather
    draw.line([(x, y), (x + width, y)], fill=GRAY_LIGHT, width=1)
    if stale:
        marker = f"offline since {stale_since}" if stale_since else "offline"
        m_bbox = draw.textbbox((0, 0), marker, font=font_small)
        draw.text(
            (x + width - (m_bbox[2] - m_bbox[0]), y + 2),
            marker,
            fill=GRAY_MID,
            font=font_small,
        )
    y += 14

    if weather is None:
        draw.text((x, y), "no data", fill=GRAY_MID, font=font_small)
        nd_bbox = draw.textbbox((0, 0), "no data", font=font_small)
        return y + (nd_bbox[3] - nd_bbox[1]) + 8

    code = weather.get("condition_code", 0)
    temp = weather.get("temperature", 0)
    high = weather.get("high", 0)
    low = weather.get("low", 0)
    rain = weather.get("rain_chance", 0)
    condition = weather.get("condition_text", "")

    # Column 1: Icon (56px, bold filled shapes)
    icon_size = 56
    _draw_weather_icon(draw, code, x, y, icon_size)

    # Column 2: Temps
    temp_x = x + icon_size + 28
    temp_text = f"{temp:.0f}°C"
    draw.text((temp_x, y), temp_text, fill=FG, font=font_display)
    temp_bbox = draw.textbbox((0, 0), temp_text, font=font_display)
    temp_h = temp_bbox[3] - temp_bbox[1]
    temp_w = temp_bbox[2] - temp_bbox[0]

    # Column 3: Condition (same size as temp) + rain
    cond_x = temp_x + temp_w + 36
    draw.text((cond_x, y), condition, fill=FG, font=font_display)
    cond_bbox = draw.textbbox((0, 0), condition, font=font_display)
    cond_h = cond_bbox[3] - cond_bbox[1]

    rain_text = f"Rain: {rain}%"
    rain_color = FG if rain >= 50 else GRAY_MID
    row2_y = y + cond_h + 6
    draw.text((cond_x, row2_y), rain_text, fill=rain_color, font=font_small)

    # Align H/L on same row as rain
    hl_text = f"H:{high:.0f}°  L:{low:.0f}°"
    draw.text((temp_x, row2_y), hl_text, fill=GRAY_MID, font=font_small)

    y += max(icon_size, temp_h + 30)
    return y


def _weather_key(code: int) -> str:
    """Map an Open-Meteo weather code to an icon-handler key."""
    if code == 0:
        return "clear"
    if code == 1:
        return "mostly_clear"
    if 2 <= code <= 3:
        return "cloudy"
    if 45 <= code <= 48:
        return "fog"
    if 51 <= code <= 57:
        return "drizzle"
    if (61 <= code <= 67) or (80 <= code <= 82):
        return "rain"
    if (71 <= code <= 77) or (85 <= code <= 86):
        return "snow"
    if 95 <= code <= 99:
        return "thunder"
    return "unknown"


def _icon_clear(draw: ImageDraw.ImageDraw, x: int, y: int, size: int) -> None:
    """Clear: sun circle + rays."""
    cx, cy = x + size // 2, y + size // 2
    r = size // 4
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=FG, width=_STROKE)
    ray_inner = r + 5
    ray_outer = size // 2 - 2
    for angle_deg in range(0, 360, 45):
        angle = math.radians(angle_deg)
        x1 = cx + int(ray_inner * math.cos(angle))
        y1 = cy + int(ray_inner * math.sin(angle))
        x2 = cx + int(ray_outer * math.cos(angle))
        y2 = cy + int(ray_outer * math.sin(angle))
        draw.line([(x1, y1), (x2, y2)], fill=FG, width=_STROKE)


def _icon_mostly_clear(draw: ImageDraw.ImageDraw, x: int, y: int, size: int) -> None:
    """Mostly clear: small sun top-right + cloud outline."""
    sr = size // 7
    sx = x + size * 3 // 4
    sy = y + size // 5
    draw.ellipse([sx - sr, sy - sr, sx + sr, sy + sr], outline=FG, width=_STROKE)
    for angle_deg in range(0, 360, 60):
        angle = math.radians(angle_deg)
        draw.line(
            [
                (
                    sx + int((sr + 3) * math.cos(angle)),
                    sy + int((sr + 3) * math.sin(angle)),
                ),
                (
                    sx + int((sr + 7) * math.cos(angle)),
                    sy + int((sr + 7) * math.sin(angle)),
                ),
            ],
            fill=FG,
            width=2,
        )
    _draw_cloud(draw, x, y + size // 3, int(size * 0.7))


def _icon_cloudy(draw: ImageDraw.ImageDraw, x: int, y: int, size: int) -> None:
    """Cloudy / Overcast."""
    _draw_cloud(draw, x, y + size // 6, size)


def _icon_fog(draw: ImageDraw.ImageDraw, x: int, y: int, size: int) -> None:
    """Fog: wavy horizontal lines."""
    bar_y = y + size // 4
    for i in range(4):
        # Alternate wave direction per line
        wave_amp = 3
        points = []
        left = x + 4
        right = x + size - 4
        steps = 12
        for s in range(steps + 1):
            px = left + (right - left) * s // steps
            offset = wave_amp * math.sin(s * math.pi / 3)
            if i % 2 == 1:
                offset = -offset
            points.append((px, bar_y + offset))
        draw.line(points, fill=FG, width=_STROKE)
        bar_y += 12


def _icon_drizzle(draw: ImageDraw.ImageDraw, x: int, y: int, size: int) -> None:
    """Drizzle: cloud + short thin drops."""
    _draw_cloud(draw, x + 2, y + 2, size - 4)
    drop_y = y + size * 2 // 3 + 6
    for dx in [size // 4, size // 2, size * 3 // 4]:
        draw.line([(x + dx, drop_y), (x + dx, drop_y + 8)], fill=FG, width=2)


def _icon_rain(draw: ImageDraw.ImageDraw, x: int, y: int, size: int) -> None:
    """Rain: cloud + thick angled drops."""
    _draw_cloud(draw, x + 2, y + 2, size - 4)
    drop_y = y + size * 2 // 3 + 6
    for dx in [size // 5, size * 2 // 5, size * 3 // 5, size * 4 // 5]:
        draw.line([(x + dx, drop_y), (x + dx - 3, drop_y + 12)], fill=FG, width=_STROKE)


def _icon_snow(draw: ImageDraw.ImageDraw, x: int, y: int, size: int) -> None:
    """Snow: cloud + circle dots (outlined)."""
    _draw_cloud(draw, x + 2, y + 2, size - 4)
    dot_y = y + size * 2 // 3 + 8
    for dx, dy in [
        (size // 4, 0),
        (size // 2, 5),
        (size * 3 // 4, 0),
        (size * 3 // 8, 12),
        (size * 5 // 8, 12),
    ]:
        draw.ellipse(
            [x + dx - 3, dot_y + dy - 3, x + dx + 3, dot_y + dy + 3],
            outline=FG,
            width=2,
        )


def _icon_thunder(draw: ImageDraw.ImageDraw, x: int, y: int, size: int) -> None:
    """Thunderstorm: cloud + bolt outline."""
    _draw_cloud(draw, x + 2, y + 2, size - 4)
    bx = x + size // 2
    by = y + size * 2 // 3 + 2
    bolt = [
        (bx, by),
        (bx - 7, by + 10),
        (bx - 1, by + 10),
        (bx - 5, by + 22),
        (bx + 7, by + 8),
        (bx + 1, by + 8),
        (bx + 5, by),
    ]
    draw.line(bolt + [bolt[0]], fill=FG, width=_STROKE)


def _icon_unknown(draw: ImageDraw.ImageDraw, x: int, y: int, size: int) -> None:
    """Fallback glyph for unrecognized codes."""
    draw.text((x + size // 4, y + size // 4), "?", fill=FG, font=font_display)


_WEATHER_ICONS = {
    "clear": _icon_clear,
    "mostly_clear": _icon_mostly_clear,
    "cloudy": _icon_cloudy,
    "fog": _icon_fog,
    "drizzle": _icon_drizzle,
    "rain": _icon_rain,
    "snow": _icon_snow,
    "thunder": _icon_thunder,
    "unknown": _icon_unknown,
}


def _draw_weather_icon(
    draw: ImageDraw.ImageDraw,
    code: int,
    x: int,
    y: int,
    size: int,
) -> None:
    """Draw weather icons using thick outlines (3px stroke) for e-ink clarity."""
    _WEATHER_ICONS[_weather_key(code)](draw, x, y, size)


def _draw_cloud(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    size: int,
) -> None:
    """Draw a cloud with flat bottom, two top bumps, smooth curves."""
    # Key positions
    base_y = y + size * 3 // 4  # flat bottom line
    left_x = x + size // 8  # left edge
    right_x = x + size * 7 // 8  # right edge

    # Flat bottom
    draw.line([(left_x, base_y), (right_x, base_y)], fill=FG, width=_STROKE)

    # Left side curve (3/4 circle, open on the right)
    left_r = size // 5
    draw.arc(
        [left_x - left_r, base_y - left_r * 2, left_x + left_r, base_y],
        start=90,
        end=360,
        fill=FG,
        width=_STROKE,
    )

    # Left/small top bump
    bump1_cx = x + size * 3 // 10
    bump1_r = size // 4
    draw.arc(
        [
            bump1_cx - bump1_r,
            base_y - bump1_r * 3,
            bump1_cx + bump1_r,
            base_y - bump1_r,
        ],
        start=155,
        end=335,
        fill=FG,
        width=_STROKE,
    )

    # Main/large top bump (the dominant cloud curve)
    bump2_cx = x + size * 3 // 5
    bump2_r = size // 3
    bump2_top = y + size // 10
    draw.arc(
        [bump2_cx - bump2_r, bump2_top, bump2_cx + bump2_r, bump2_top + bump2_r * 2],
        start=180,
        end=360,
        fill=FG,
        width=_STROKE,
    )

    # Right side curve (3/4 circle, open on the left)
    right_r = size // 5
    draw.arc(
        [right_x - right_r, base_y - right_r * 2, right_x + right_r, base_y],
        start=180,
        end=90,
        fill=FG,
        width=_STROKE,
    )
