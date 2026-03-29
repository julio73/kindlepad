"""Drawing components for the KindlePad two-panel landscape dashboard.

Editorial utilitarian style: high contrast, typographically-driven.
Every mark is deliberate.
"""

from __future__ import annotations

import math

from PIL import ImageDraw

from server.touchmap import TouchZone

from .theme import (
    FG,
    GRAY_DARK,
    GRAY_LIGHT,
    GRAY_MID,
    PADDING,
    ROW_HEIGHT,
    SECTION_GAP,
    font_body,
    font_display,
    font_display_xl,
    font_section,
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
    """Draw title left-aligned, date+time right-aligned, thick separator below.

    Returns the y position below the separator.
    """
    # Title in display font, uppercase
    title_upper = title.upper()
    draw.text((PADDING, y), title_upper, fill=FG, font=font_display)

    # Right side: date + time in body font
    right_text = f"{date_str}  {time_str}"
    rt_bbox = draw.textbbox((0, 0), right_text, font=font_body)
    rt_width = rt_bbox[2] - rt_bbox[0]
    # Vertically center the smaller body text with the display text
    title_bbox = draw.textbbox((0, 0), title_upper, font=font_display)
    title_h = title_bbox[3] - title_bbox[1]
    rt_h = rt_bbox[3] - rt_bbox[1]
    rt_y = y + (title_h - rt_h) // 2
    draw.text(
        (width - PADDING - rt_width, rt_y),
        right_text,
        fill=FG,
        font=font_body,
    )

    # Advance past text
    y += title_h + 14

    # Thick full-width separator (width=3 for e-ink presence)
    draw.line([(PADDING, y), (width - PADDING, y)], fill=FG, width=3)
    y += SECTION_GAP + 4  # breathing room below separator

    return y


def draw_section_header(
    draw: ImageDraw.ImageDraw,
    label: str,
    x: int,
    y: int,
) -> int:
    """Draw a section label in DIN Alternate Bold, uppercase.

    If label contains " . " (middle dot), render the part after it in
    font_small at GRAY_MID on the same line.

    Returns the y position below the label.
    """
    if " \u00b7 " in label:
        main_part, sub_part = label.split(" \u00b7 ", 1)
    else:
        main_part = label
        sub_part = None

    main_upper = main_part.upper()
    draw.text((x, y), main_upper, fill=FG, font=font_section)
    main_bbox = draw.textbbox((0, 0), main_upper, font=font_section)
    main_w = main_bbox[2] - main_bbox[0]
    main_h = main_bbox[3] - main_bbox[1]

    if sub_part:
        # Position subtitle after main text, baseline-aligned
        sub_bbox = draw.textbbox((0, 0), sub_part, font=font_small)
        sub_h = sub_bbox[3] - sub_bbox[1]
        sub_y = y + (main_h - sub_h)  # align bottoms
        draw.text(
            (x + main_w + 10, sub_y),
            sub_part,
            fill=GRAY_MID,
            font=font_small,
        )

    y += main_h + 6

    # Thin 1px rule below
    rule_end = x + main_w + 20
    if sub_part:
        sub_w = draw.textbbox((0, 0), sub_part, font=font_small)[2]
        rule_end = x + main_w + 10 + sub_w + 10
    draw.line([(x, y), (rule_end, y)], fill=GRAY_LIGHT, width=1)
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
    """Draw a departure row with hero-sized minutes number.

    Minutes in font_display_xl (commanding), "min" suffix in font_small gray,
    destination in font_body after the minutes block.
    Direction is omitted (implied by destination).

    Returns the y position below the row.
    """
    # Minutes number (hero element) or "Due"
    if minutes == 0:
        min_text = "DUE"
        draw.text((x, y), min_text, fill=FG, font=font_display_xl)
        num_bbox = draw.textbbox((0, 0), min_text, font=font_display_xl)
        num_w = num_bbox[2] - num_bbox[0]
        num_h = num_bbox[3] - num_bbox[1]
    else:
        min_text = str(minutes)
        draw.text((x, y), min_text, fill=FG, font=font_display_xl)
        num_bbox = draw.textbbox((0, 0), min_text, font=font_display_xl)
        num_w = num_bbox[2] - num_bbox[0]
        num_h = num_bbox[3] - num_bbox[1]

        # "min" suffix in small gray, baseline-aligned to the number
        suffix = "min"
        suffix_bbox = draw.textbbox((0, 0), suffix, font=font_small)
        suffix_h = suffix_bbox[3] - suffix_bbox[1]
        suffix_y = y + (num_h - suffix_h)  # align baselines
        draw.text(
            (x + num_w + 4, suffix_y),
            suffix,
            fill=GRAY_MID,
            font=font_small,
        )

    # Destination in body font, offset from the minutes block
    dest_x = x + 100
    dest_bbox = draw.textbbox((0, 0), destination, font=font_body)
    dest_h = dest_bbox[3] - dest_bbox[1]
    dest_y = y + (num_h - dest_h) // 2  # vertically center with number
    draw.text((dest_x, dest_y), destination, fill=FG, font=font_body)

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

    Good service (severity 10) renders status in GRAY_MID.
    Disruptions render in FG (black) for emphasis.
    Returns the y position below the row.
    """
    status_color = GRAY_MID if severity == 10 else FG

    draw.text((x, y), line_name, fill=FG, font=font_body)

    status_bbox = draw.textbbox((0, 0), status_text, font=font_body)
    status_w = status_bbox[2] - status_bbox[0]
    draw.text(
        (x + width - status_w, y),
        status_text,
        fill=status_color,
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
    """Draw a room group label in small font, black, uppercase feel.

    Returns the y position below the label.
    """
    label = room_name.upper()
    y += 10  # breathing room above
    draw.text((x, y), label, fill=FG, font=font_small)
    bbox = draw.textbbox((0, 0), label, font=font_small)
    text_h = bbox[3] - bbox[1]
    y += text_h + 10
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
    """Draw a single toggle button for a light.

    ON = filled black with white text. OFF = white with black 2px outline.
    Returns (new_y, TouchZone).
    """
    btn_height = 42
    label = f"{name}  {'ON' if is_on else 'OFF'}"

    if is_on:
        draw.rectangle([x, y, x + width, y + btn_height], fill=FG)
        text_color = 255
    else:
        draw.rectangle(
            [x, y, x + width, y + btn_height],
            fill=255,
            outline=FG,
            width=2,  # thicker border for e-ink visibility
        )
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
    """Draw lights as single toggle buttons -- always half-width, two per row.

    Returns (new_y, list of TouchZones).
    """
    zones: list[TouchZone] = []
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
            # Single button -- same half-width size
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
    """Draw weather in 3-column layout: icon | temps | condition.

    Returns the y position below the weather section.
    """
    code = weather.get("condition_code", 0)
    temp = weather.get("temperature", 0)
    high = weather.get("high", 0)
    low = weather.get("low", 0)
    rain = weather.get("rain_chance", 0)
    condition = weather.get("condition_text", "")

    # Column 1: Icon (~50px)
    icon_size = 50
    _draw_weather_icon(draw, code, x, y, icon_size)

    # Column 2: Temps (after icon)
    temp_x = x + icon_size + 12
    temp_text = f"{temp:.0f}\u00b0C"
    draw.text((temp_x, y), temp_text, fill=FG, font=font_display)
    temp_bbox = draw.textbbox((0, 0), temp_text, font=font_display)
    temp_h = temp_bbox[3] - temp_bbox[1]
    temp_w = temp_bbox[2] - temp_bbox[0]

    hl_text = f"H:{high:.0f}\u00b0 L:{low:.0f}\u00b0"
    draw.text((temp_x, y + temp_h + 4), hl_text, fill=GRAY_MID, font=font_small)

    # Column 3: Condition + rain (takes remaining width)
    cond_x = temp_x + temp_w + 20
    draw.text((cond_x, y + 4), condition, fill=FG, font=font_body)
    cond_bbox = draw.textbbox((0, 0), condition, font=font_body)
    cond_h = cond_bbox[3] - cond_bbox[1]

    rain_text = f"Rain: {rain}%"
    draw.text((cond_x, y + 4 + cond_h + 4), rain_text, fill=GRAY_MID, font=font_small)

    y += max(icon_size, temp_h + 24) + SECTION_GAP
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
        # Clear: circle (sun) with rays
        margin = 4
        draw.ellipse(
            [x + margin, y + margin, x + size - margin, y + size - margin],
            outline=FG,
            width=2,
        )
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
        # Cloudy
        _draw_cloud(draw, x, y, size)

    elif 45 <= code <= 48:
        # Fog: horizontal parallel lines
        line_y = y + 8
        for _i in range(4):
            draw.line([(x + 4, line_y), (x + size - 4, line_y)], fill=FG, width=2)
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
        draw.text((x + 8, y + 4), "?", fill=FG, font=font_display)


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
    """Draw a vertical divider separating the two panels.

    Uses GRAY_DARK and width=2 for stronger e-ink presence.
    """
    draw.line([(x, y_start), (x, y_end)], fill=GRAY_DARK, width=2)


def draw_footer(
    draw: ImageDraw.ImageDraw,
    timestamp: str,
    x: int,
    y: int,
    width: int,
) -> int:
    """Draw a subtle timestamp in tiny text, bottom-left."""
    text = timestamp
    draw.text((x, y), text, fill=GRAY_MID, font=font_small)
    bbox = draw.textbbox((0, 0), text, font=font_small)
    text_h = bbox[3] - bbox[1]
    y += text_h + PADDING
    return y
