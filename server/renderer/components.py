"""Drawing components for the KindlePad two-panel landscape dashboard."""

from __future__ import annotations

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


def draw_light_inline(
    draw: ImageDraw.ImageDraw,
    name: str,
    is_on: bool,
    device_id: str,
    x: int,
    y: int,
    cell_width: int,
) -> TouchZone:
    """Draw a single inline light toggle: 'Name ■ ON' or 'Name □ OFF'.

    Tap target covers the whole cell. Returns a TouchZone.
    """
    state_text = "ON" if is_on else "OFF"
    state_color = FG if is_on else GRAY_MID
    sq_size = 12
    sq_y = y + 6

    # Name
    draw.text((x + 4, y), name, fill=FG, font=font_small)
    name_bbox = draw.textbbox((0, 0), name, font=font_small)
    name_w = name_bbox[2] - name_bbox[0]
    cx = x + 4 + name_w + 8

    # Square indicator
    if is_on:
        draw.rectangle([cx, sq_y, cx + sq_size, sq_y + sq_size], fill=FG)
    else:
        draw.rectangle([cx, sq_y, cx + sq_size, sq_y + sq_size], fill=255, outline=FG, width=1)

    # ON/OFF text
    draw.text((cx + sq_size + 5, y), state_text, fill=state_color, font=font_small)

    return TouchZone(
        x=x,
        y=y,
        width=cell_width,
        height=ROW_HEIGHT,
        action="toggle_light",
        params={"device_id": device_id},
    )


def draw_light_group(
    draw: ImageDraw.ImageDraw,
    room_lights: list[dict],
    x: int,
    y: int,
    width: int,
) -> tuple[int, list[TouchZone]]:
    """Draw lights inline — two per row if multiple in a room, one per row otherwise.

    Returns (new_y, list of TouchZones).
    """
    zones = []
    i = 0
    while i < len(room_lights):
        if i + 1 < len(room_lights):
            # Two lights on one row
            cell_w = width // 2
            zone1 = draw_light_inline(
                draw, room_lights[i]["name"], room_lights[i]["is_on"],
                room_lights[i]["id"], x, y, cell_w,
            )
            zone2 = draw_light_inline(
                draw, room_lights[i + 1]["name"], room_lights[i + 1]["is_on"],
                room_lights[i + 1]["id"], x + cell_w, y, cell_w,
            )
            zones.extend([zone1, zone2])
            i += 2
        else:
            # Single light on its own row
            zone = draw_light_inline(
                draw, room_lights[i]["name"], room_lights[i]["is_on"],
                room_lights[i]["id"], x, y, width,
            )
            zones.append(zone)
            i += 1
        y += ROW_HEIGHT
    return y, zones


def draw_brightness_bar(
    draw: ImageDraw.ImageDraw,
    level: int,
    x: int,
    y: int,
    width: int,
) -> tuple[int, list[TouchZone]]:
    """Draw brightness control: label + 4 tap zones (off, low, med, high).

    Returns (new_y, list of TouchZones).
    """
    # Label
    draw.text((x, y), "Brightness", fill=GRAY_MID, font=font_small)
    bbox = draw.textbbox((0, 0), "Brightness", font=font_small)
    y += (bbox[3] - bbox[1]) + 8

    levels = [
        ("Off", 0),
        ("Low", 1),
        ("Med", 2),
        ("High", 3),
    ]
    btn_gap = 8
    btn_width = (width - btn_gap * (len(levels) - 1)) // len(levels)
    btn_height = 36
    zones = []

    for i, (label, lvl) in enumerate(levels):
        bx = x + i * (btn_width + btn_gap)
        is_active = lvl == level

        if is_active:
            draw.rectangle(
                [bx, y, bx + btn_width, y + btn_height],
                fill=FG,
            )
            text_color = 255  # white
        else:
            draw.rectangle(
                [bx, y, bx + btn_width, y + btn_height],
                fill=255,
                outline=FG,
                width=1,
            )
            text_color = FG

        lbl_bbox = draw.textbbox((0, 0), label, font=font_small)
        lw = lbl_bbox[2] - lbl_bbox[0]
        lh = lbl_bbox[3] - lbl_bbox[1]
        draw.text(
            (bx + (btn_width - lw) // 2, y + (btn_height - lh) // 2),
            label,
            fill=text_color,
            font=font_small,
        )

        zones.append(TouchZone(
            x=bx,
            y=y,
            width=btn_width,
            height=btn_height,
            action="set_brightness",
            params={"level": lvl},
        ))

    y += btn_height + SECTION_GAP
    return y, zones


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
