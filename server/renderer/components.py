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


def draw_power_button(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
) -> TouchZone:
    """Draw a small power icon (arc with gap + vertical line).

    Returns a TouchZone for the sleep action.
    """
    r = 9
    cx = x + r
    cy = y + r

    # Circle arc with gap at top
    draw.arc([cx - r, cy - r, cx + r, cy + r], start=40, end=320, fill=GRAY_MID, width=2)
    # Vertical line through the gap
    draw.line([(cx, cy - r), (cx, cy - 3)], fill=GRAY_MID, width=2)

    # Generous touch zone for finger taps
    pad = 12
    return TouchZone(
        x=x - pad,
        y=y - pad,
        width=r * 2 + pad * 2,
        height=r * 2 + pad * 2,
        action="screen_off",
    )


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
        action="light_off" if is_on else "light_on",
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

    # Separator above weather
    draw.line([(x, y), (x + width, y)], fill=GRAY_LIGHT, width=1)
    y += 14

    # Column 1: Icon (56px, bold filled shapes)
    icon_size = 56
    _draw_weather_icon(draw, code, x, y, icon_size)

    # Column 2: Temps
    temp_x = x + icon_size + 28
    temp_text = f"{temp:.0f}\u00b0C"
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
    hl_text = f"H:{high:.0f}\u00b0  L:{low:.0f}\u00b0"
    draw.text((temp_x, row2_y), hl_text, fill=GRAY_MID, font=font_small)

    y += max(icon_size, temp_h + 30) + SECTION_GAP
    return y


def _draw_weather_icon(
    draw: ImageDraw.ImageDraw,
    code: int,
    x: int,
    y: int,
    size: int,
) -> None:
    """Draw weather icons using thick outlines (3px stroke) for e-ink clarity."""
    W = 3  # stroke width
    cx = x + size // 2
    cy = y + size // 2

    if code == 0:
        # Clear: sun circle + rays
        r = size // 4
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=FG, width=W)
        ray_inner = r + 5
        ray_outer = size // 2 - 2
        for angle_deg in range(0, 360, 45):
            angle = math.radians(angle_deg)
            x1 = cx + int(ray_inner * math.cos(angle))
            y1 = cy + int(ray_inner * math.sin(angle))
            x2 = cx + int(ray_outer * math.cos(angle))
            y2 = cy + int(ray_outer * math.sin(angle))
            draw.line([(x1, y1), (x2, y2)], fill=FG, width=W)

    elif code == 1:
        # Mostly clear: small sun top-right + cloud outline
        sr = size // 7
        sx = x + size * 3 // 4
        sy = y + size // 5
        draw.ellipse([sx - sr, sy - sr, sx + sr, sy + sr], outline=FG, width=W)
        for angle_deg in range(0, 360, 60):
            angle = math.radians(angle_deg)
            draw.line([
                (sx + int((sr + 3) * math.cos(angle)), sy + int((sr + 3) * math.sin(angle))),
                (sx + int((sr + 7) * math.cos(angle)), sy + int((sr + 7) * math.sin(angle))),
            ], fill=FG, width=2)
        _draw_cloud(draw, x, y + size // 3, int(size * 0.7))

    elif 2 <= code <= 3:
        # Cloudy / Overcast
        _draw_cloud(draw, x, y + size // 6, size)

    elif 45 <= code <= 48:
        # Fog: wavy horizontal lines
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
            draw.line(points, fill=FG, width=W)
            bar_y += 12

    elif 51 <= code <= 57:
        # Drizzle: cloud + short thin drops
        _draw_cloud(draw, x + 2, y + 2, size - 4)
        drop_y = y + size * 2 // 3 + 6
        for dx in [size // 4, size // 2, size * 3 // 4]:
            draw.line([(x + dx, drop_y), (x + dx, drop_y + 8)], fill=FG, width=2)

    elif (61 <= code <= 67) or (80 <= code <= 82):
        # Rain: cloud + thick angled drops
        _draw_cloud(draw, x + 2, y + 2, size - 4)
        drop_y = y + size * 2 // 3 + 6
        for dx in [size // 5, size * 2 // 5, size * 3 // 5, size * 4 // 5]:
            draw.line([(x + dx, drop_y), (x + dx - 3, drop_y + 12)], fill=FG, width=W)

    elif (71 <= code <= 77) or (85 <= code <= 86):
        # Snow: cloud + circle dots (outlined)
        _draw_cloud(draw, x + 2, y + 2, size - 4)
        dot_y = y + size * 2 // 3 + 8
        for dx, dy in [(size // 4, 0), (size // 2, 5), (size * 3 // 4, 0),
                        (size * 3 // 8, 12), (size * 5 // 8, 12)]:
            draw.ellipse([x + dx - 3, dot_y + dy - 3, x + dx + 3, dot_y + dy + 3],
                         outline=FG, width=2)

    elif 95 <= code <= 99:
        # Thunderstorm: cloud + bolt outline
        _draw_cloud(draw, x + 2, y + 2, size - 4)
        bx = cx
        by = y + size * 2 // 3 + 2
        bolt = [
            (bx, by), (bx - 7, by + 10), (bx - 1, by + 10),
            (bx - 5, by + 22), (bx + 7, by + 8), (bx + 1, by + 8),
            (bx + 5, by),
        ]
        draw.line(bolt + [bolt[0]], fill=FG, width=W)

    else:
        draw.text((x + size // 4, y + size // 4), "?", fill=FG, font=font_display)


def _draw_cloud(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    size: int,
) -> None:
    """Draw a cloud with flat bottom, two top bumps, smooth curves."""
    W = 3
    # Key positions
    base_y = y + size * 3 // 4       # flat bottom line
    left_x = x + size // 8           # left edge
    right_x = x + size * 7 // 8      # right edge

    # Flat bottom
    draw.line([(left_x, base_y), (right_x, base_y)], fill=FG, width=W)

    # Left side curve (3/4 circle, open on the right)
    left_r = size // 5
    draw.arc([left_x - left_r, base_y - left_r * 2, left_x + left_r, base_y],
             start=90, end=360, fill=FG, width=W)

    # Left/small top bump
    bump1_cx = x + size * 3 // 10
    bump1_r = size // 4
    draw.arc([bump1_cx - bump1_r, base_y - bump1_r * 3, bump1_cx + bump1_r, base_y - bump1_r],
             start=155, end=335, fill=FG, width=W)

    # Main/large top bump (the dominant cloud curve)
    bump2_cx = x + size * 3 // 5
    bump2_r = size // 3
    bump2_top = y + size // 10
    draw.arc([bump2_cx - bump2_r, bump2_top, bump2_cx + bump2_r, bump2_top + bump2_r * 2],
             start=180, end=360, fill=FG, width=W)

    # Right side curve (3/4 circle, open on the left)
    right_r = size // 5
    draw.arc([right_x - right_r, base_y - right_r * 2, right_x + right_r, base_y],
             start=180, end=90, fill=FG, width=W)


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
    battery_pct: int | None = None,
    is_charging: bool = False,
) -> int:
    """Draw timestamp left-aligned, battery right-aligned.

    When charging, a small lightning bolt is drawn to the left of the
    battery percentage.
    """
    draw.text((x, y), timestamp, fill=GRAY_MID, font=font_small)

    if battery_pct is not None:
        batt_text = f"{battery_pct}%"
        batt_bbox = draw.textbbox((0, 0), batt_text, font=font_small)
        batt_w = batt_bbox[2] - batt_bbox[0]
        batt_h = batt_bbox[3] - batt_bbox[1]
        batt_x = x + width - batt_w

        if is_charging:
            # Small lightning bolt to the left of the percentage
            bolt_w = 10
            bx = batt_x - bolt_w - 4
            by = y + 1
            h = batt_h
            bolt = [
                (bx + 5, by),
                (bx + 1, by + h // 2 + 1),
                (bx + 5, by + h // 2 - 1),
                (bx + 3, by + h),
                (bx + 9, by + h // 2 - 1),
                (bx + 5, by + h // 2 + 1),
            ]
            draw.polygon(bolt, fill=GRAY_MID)

        draw.text((batt_x, y), batt_text, fill=GRAY_MID, font=font_small)

    bbox = draw.textbbox((0, 0), timestamp, font=font_small)
    text_h = bbox[3] - bbox[1]
    y += text_h + PADDING
    return y
