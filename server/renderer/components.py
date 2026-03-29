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


def draw_light_row(
    draw: ImageDraw.ImageDraw,
    name: str,
    is_on: bool,
    device_id: str,
    x: int,
    y: int,
    width: int,
) -> tuple[int, TouchZone]:
    """Draw a light row: filled/empty circle + name + ON/OFF status.

    The full row is a tap target for toggling.
    Returns (new_y, TouchZone).
    """
    circle_char = "\u25cf" if is_on else "\u25cb"  # filled or empty circle
    state_text = "ON" if is_on else "OFF"
    state_color = FG if is_on else GRAY_MID

    # Try drawing the circle character; fall back to a rectangle if the font
    # cannot render it (bbox would be zero-width).
    circle_bbox = draw.textbbox((0, 0), circle_char, font=font_body)
    circle_width = circle_bbox[2] - circle_bbox[0]

    if circle_width > 0:
        draw.text((x, y), circle_char, fill=state_color, font=font_body)
        text_x = x + circle_width + 8
    else:
        # Fallback: draw a small filled/empty rectangle
        rect_size = 10
        ry = y + 4
        if is_on:
            draw.rectangle([x, ry, x + rect_size, ry + rect_size], fill=FG)
        else:
            draw.rectangle(
                [x, ry, x + rect_size, ry + rect_size],
                fill=255,
                outline=FG,
                width=1,
            )
        text_x = x + rect_size + 8

    # Light name
    draw.text((text_x, y), name, fill=FG, font=font_body)

    # State label right-aligned
    st_bbox = draw.textbbox((0, 0), state_text, font=font_body)
    st_width = st_bbox[2] - st_bbox[0]
    draw.text(
        (x + width - st_width, y),
        state_text,
        fill=state_color,
        font=font_body,
    )

    zone = TouchZone(
        x=x,
        y=y,
        width=width,
        height=ROW_HEIGHT,
        action="toggle_light",
        params={"device_id": device_id},
    )

    y += ROW_HEIGHT
    return y, zone


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
