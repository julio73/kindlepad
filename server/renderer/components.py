"""Drawing components for the KindlePad two-panel landscape dashboard."""

from __future__ import annotations

import math

from PIL import ImageDraw

from server.touchmap import TouchZone

from .theme import (
    FG,
    GRAY_LIGHT,
    GRAY_MID,
    PADDING,
    ROW_HEIGHT,
    SECTION_GAP,
    font_body,
    font_heading,
    font_label,
    font_small,
)


def draw_header(
    draw: ImageDraw.ImageDraw,
    title: str,
    time_str: str,
    date_str: str,
    width: int,
    y: int,
) -> int:
    """Draw title left-aligned, date+time right-aligned, then a separator line.

    Returns the y position below the separator.
    """
    draw.text((PADDING, y), title, fill=FG, font=font_heading)

    # Right side: "Sat 29 Mar  04:35"
    right_text = f"{date_str}  {time_str}"
    rt_bbox = draw.textbbox((0, 0), right_text, font=font_heading)
    rt_width = rt_bbox[2] - rt_bbox[0]
    draw.text(
        (width - PADDING - rt_width, y),
        right_text,
        fill=FG,
        font=font_heading,
    )

    # Advance past text
    title_bbox = draw.textbbox((0, 0), title, font=font_heading)
    text_height = title_bbox[3] - title_bbox[1]
    y += text_height + 12

    # Full-width separator
    draw.line([(PADDING, y), (width - PADDING, y)], fill=FG, width=2)
    y += SECTION_GAP

    return y


def draw_section_header(
    draw: ImageDraw.ImageDraw,
    label: str,
    x: int,
    y: int,
) -> int:
    """Draw a section label (e.g. 'NEXT TRAINS ...', 'LIGHTS').

    Returns the y position below the label.
    """
    draw.text((x, y), label, fill=FG, font=font_body)
    bbox = draw.textbbox((0, 0), label, font=font_body)
    text_height = bbox[3] - bbox[1]
    y += text_height + 6

    # Thin underline
    draw.line([(x, y), (x + 200, y)], fill=GRAY_LIGHT, width=1)
    y += SECTION_GAP

    return y


def draw_departure_row(
    draw: ImageDraw.ImageDraw,
    minutes: int,
    destination: str,
    direction: str,
    x: int,
    y: int,
    width: int,
) -> int:
    """Draw a departure row: '2 min   Northtown       Eastbound'.

    Minutes left-aligned in bold (heading font), 'min' suffix in small gray,
    destination in body font, direction right-aligned in gray.

    Returns the y position below the row.
    """
    # Minutes number (bold via heading font)
    if minutes == 0:
        min_num = "Due"
        draw.text((x, y), min_num, fill=FG, font=font_heading)
        num_bbox = draw.textbbox((0, 0), min_num, font=font_heading)
        num_width = num_bbox[2] - num_bbox[0]
    else:
        min_num = str(minutes)
        draw.text((x, y), min_num, fill=FG, font=font_heading)
        num_bbox = draw.textbbox((0, 0), min_num, font=font_heading)
        num_width = num_bbox[2] - num_bbox[0]

        # "min" suffix in small gray text
        min_suffix = " min"
        # Vertically align the small text with the baseline
        suffix_y = y + 4  # slight offset to align baselines
        draw.text(
            (x + num_width, suffix_y),
            min_suffix,
            fill=GRAY_MID,
            font=font_small,
        )

    # Destination in body font, offset from left
    dest_x = x + 90
    draw.text((dest_x, y), destination, fill=FG, font=font_body)

    # Direction right-aligned within the panel width
    dir_bbox = draw.textbbox((0, 0), direction, font=font_small)
    dir_width = dir_bbox[2] - dir_bbox[0]
    draw.text(
        (x + width - dir_width, y + 2),
        direction,
        fill=GRAY_MID,
        font=font_small,
    )

    y += ROW_HEIGHT
    return y


def draw_tfl_row(
    draw: ImageDraw.ImageDraw,
    line_name: str,
    status_text: str,
    severity: int,
    x: int,
    y: int,
    width: int,
) -> int:
    """Draw a TfL line status row: line name left, status right.

    severity 10 = good service (GRAY_MID), anything else = black (FG).
    Returns the y position below the row.
    """
    color = GRAY_MID if severity == 10 else FG

    draw.text((x, y), line_name, fill=FG, font=font_body)

    status_bbox = draw.textbbox((0, 0), status_text, font=font_body)
    status_width = status_bbox[2] - status_bbox[0]
    draw.text(
        (x + width - status_width, y),
        status_text,
        fill=color,
        font=font_body,
    )

    y += ROW_HEIGHT
    return y


def draw_room_header(
    draw: ImageDraw.ImageDraw,
    room_name: str,
    x: int,
    y: int,
) -> int:
    """Draw a small room group label, slightly indented.

    Returns the y position below the label.
    """
    indent = 4
    draw.text((x + indent, y), room_name, fill=GRAY_MID, font=font_label)
    bbox = draw.textbbox((0, 0), room_name, font=font_label)
    text_height = bbox[3] - bbox[1]
    y += text_height + 6
    return y


def draw_light_button(
    draw: ImageDraw.ImageDraw,
    name: str,
    is_on: bool,
    device_id: str,
    x: int,
    y: int,
    width: int,
) -> tuple[int, TouchZone]:
    """Draw a single button for a light: filled=ON, outlined=OFF. Tap to toggle.

    Shows: [  Lamp 1  ON  ] (filled) or [  Lamp 2  OFF  ] (outlined)
    Returns (new_y, TouchZone).
    """
    btn_height = 42
    label = f"{name}  {'ON' if is_on else 'OFF'}"

    if is_on:
        draw.rectangle([x, y, x + width, y + btn_height], fill=FG)
        text_color = 255
    else:
        draw.rectangle([x, y, x + width, y + btn_height], fill=255, outline=FG, width=1)
        text_color = FG

    lbl_bbox = draw.textbbox((0, 0), label, font=font_small)
    lw = lbl_bbox[2] - lbl_bbox[0]
    lh = lbl_bbox[3] - lbl_bbox[1]
    draw.text(
        (x + (width - lw) // 2, y + (btn_height - lh) // 2),
        label,
        fill=text_color,
        font=font_small,
    )

    zone = TouchZone(
        x=x,
        y=y,
        width=width,
        height=btn_height,
        action="toggle_light",
        params={"device_id": device_id},
    )

    y += btn_height + 8
    return y, zone


def draw_light_group(
    draw: ImageDraw.ImageDraw,
    room_lights: list[dict],
    x: int,
    y: int,
    width: int,
) -> tuple[int, list[TouchZone]]:
    """Draw lights as single toggle buttons — always half-width, two per row.

    Returns (new_y, list of TouchZones).
    """
    zones = []
    btn_gap = 8
    btn_w = (width - btn_gap) // 2
    i = 0
    while i < len(room_lights):
        if i + 1 < len(room_lights):
            # Two buttons side by side
            y1, zone1 = draw_light_button(
                draw, room_lights[i]["name"], room_lights[i]["is_on"],
                room_lights[i]["id"], x, y, btn_w,
            )
            y2, zone2 = draw_light_button(
                draw, room_lights[i + 1]["name"], room_lights[i + 1]["is_on"],
                room_lights[i + 1]["id"], x + btn_w + btn_gap, y, btn_w,
            )
            zones.extend([zone1, zone2])
            y = max(y1, y2)
            i += 2
        else:
            # Single button — same half-width size
            y, zone = draw_light_button(
                draw, room_lights[i]["name"], room_lights[i]["is_on"],
                room_lights[i]["id"], x, y, btn_w,
            )
            zones.append(zone)
            i += 1
    return y, zones


def draw_weather(
    draw: ImageDraw.ImageDraw,
    weather: dict,
    x: int,
    y: int,
    width: int,
) -> int:
    """Draw weather info: icon + temperature + high/low/rain details.

    The icon is ~40x40 pixels drawn with Pillow shapes based on condition_code.
    Returns the y position below the weather section.
    """
    code = weather.get("condition_code", 0)
    temp = weather.get("temperature", 0)
    high = weather.get("high", 0)
    low = weather.get("low", 0)
    rain = weather.get("rain_chance", 0)

    icon_size = 40
    icon_x = x
    icon_y = y

    _draw_weather_icon(draw, code, icon_x, icon_y, icon_size)

    # Temperature next to icon
    temp_text = f"{temp:.0f}\u00b0C"
    text_x = icon_x + icon_size + 12
    draw.text((text_x, icon_y), temp_text, fill=FG, font=font_heading)

    # Condition text below temperature
    condition = weather.get("condition_text", "")
    cond_bbox = draw.textbbox((0, 0), condition, font=font_small)
    cond_h = cond_bbox[3] - cond_bbox[1]
    heading_bbox = draw.textbbox((0, 0), temp_text, font=font_heading)
    heading_h = heading_bbox[3] - heading_bbox[1]
    draw.text((text_x, icon_y + heading_h + 4), condition, fill=GRAY_MID, font=font_small)

    # High/Low and Rain line below the icon area
    detail_y = icon_y + icon_size + 10
    detail_text = f"H:{high:.0f}\u00b0  L:{low:.0f}\u00b0   Rain: {rain}%"
    draw.text((x, detail_y), detail_text, fill=FG, font=font_small)

    detail_bbox = draw.textbbox((0, 0), detail_text, font=font_small)
    detail_h = detail_bbox[3] - detail_bbox[1]
    y = detail_y + detail_h + SECTION_GAP
    return y


def _draw_weather_icon(
    draw: ImageDraw.ImageDraw,
    code: int,
    x: int,
    y: int,
    size: int,
) -> None:
    """Draw a weather icon using Pillow shapes based on WMO condition code."""
    if code == 0:
        # Clear: circle (sun)
        margin = 4
        draw.ellipse(
            [x + margin, y + margin, x + size - margin, y + size - margin],
            outline=FG,
            width=2,
        )
        # Sun rays: short lines radiating from center
        cx = x + size // 2
        cy = y + size // 2
        r_inner = size // 2 - margin
        r_outer = size // 2 - 1
        for angle_deg in range(0, 360, 45):
            angle = math.radians(angle_deg)
            x1 = cx + int(r_inner * math.cos(angle))
            y1 = cy + int(r_inner * math.sin(angle))
            x2 = cx + int(r_outer * math.cos(angle))
            y2 = cy + int(r_outer * math.sin(angle))
            draw.line([(x1, y1), (x2, y2)], fill=FG, width=1)

    elif 1 <= code <= 3:
        # Cloudy: cloud shape using overlapping ellipses
        _draw_cloud(draw, x, y, size)

    elif 45 <= code <= 48:
        # Fog: horizontal parallel lines
        line_y = y + 8
        for i in range(4):
            lx1 = x + 4
            lx2 = x + size - 4
            draw.line([(lx1, line_y), (lx2, line_y)], fill=FG, width=2)
            line_y += 8

    elif (51 <= code <= 67) or (80 <= code <= 82):
        # Rain: cloud + vertical drop lines
        _draw_cloud(draw, x, y - 4, size)
        for dx in [10, 20, 30]:
            rx = x + dx
            ry_top = y + size - 12
            ry_bot = y + size - 4
            draw.line([(rx, ry_top), (rx, ry_bot)], fill=FG, width=2)

    elif (71 <= code <= 77) or (85 <= code <= 86):
        # Snow: cloud + dots
        _draw_cloud(draw, x, y - 4, size)
        for dx, dy in [(10, -8), (22, -4), (34, -8), (16, 0), (28, 0)]:
            sx = x + dx
            sy = y + size + dy - 8
            draw.ellipse([sx - 2, sy - 2, sx + 2, sy + 2], fill=FG)

    elif 95 <= code <= 99:
        # Thunderstorm: cloud + zigzag bolt
        _draw_cloud(draw, x, y - 4, size)
        bolt_x = x + size // 2
        bolt_y = y + size - 14
        draw.line(
            [(bolt_x, bolt_y), (bolt_x - 5, bolt_y + 6),
             (bolt_x + 3, bolt_y + 6), (bolt_x - 2, bolt_y + 14)],
            fill=FG,
            width=2,
        )

    else:
        # Unknown: question mark
        draw.text((x + 8, y + 4), "?", fill=FG, font=font_heading)


def _draw_cloud(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    size: int,
) -> None:
    """Draw a cloud shape using overlapping ellipses."""
    # Base ellipse (wide, lower)
    draw.ellipse(
        [x + 2, y + size // 3, x + size - 2, y + size * 2 // 3 + 4],
        outline=FG,
        width=2,
    )
    # Top bump (smaller, higher)
    draw.ellipse(
        [x + size // 4, y + 4, x + size * 3 // 4, y + size // 2 + 2],
        outline=FG,
        width=2,
    )


def draw_vertical_divider(
    draw: ImageDraw.ImageDraw,
    x: int,
    y_start: int,
    y_end: int,
) -> None:
    """Draw a thin vertical line separating the two panels."""
    draw.line([(x, y_start), (x, y_end)], fill=GRAY_LIGHT, width=1)


def draw_footer(
    draw: ImageDraw.ImageDraw,
    timestamp: str,
    x: int,
    y: int,
    width: int,
) -> int:
    """Draw 'Last updated: {timestamp}' in SMALL font, GRAY_MID, left-aligned."""
    text = f"Last updated: {timestamp}"
    draw.text((x, y), text, fill=GRAY_MID, font=font_small)
    bbox = draw.textbbox((0, 0), text, font=font_small)
    text_height = bbox[3] - bbox[1]
    y += text_height + PADDING
    return y
