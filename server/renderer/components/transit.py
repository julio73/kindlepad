"""Transit components: train departure rows and TfL line status rows."""

from __future__ import annotations

from PIL import ImageDraw

from ..theme import (
    FG,
    GRAY_MID,
    ROW_HEIGHT,
    font_body,
    font_display_xl,
    font_small,
)


def draw_departure_row(
    draw: ImageDraw.ImageDraw,
    departure: dict,
    x: int,
    y: int,
    width: int,
) -> int:
    """Draw a departure row with hero-sized minutes number.

    ``departure`` keys: minutes, destination, direction. Minutes render in
    font_display_xl (commanding), "min" suffix in font_small gray, destination
    in font_body after the minutes block. Direction is omitted (implied by
    destination).

    Returns the y position below the row.
    """
    minutes = departure["minutes"]
    destination = departure["destination"]

    # Minutes number (hero element) or "Due"
    min_text = "DUE" if minutes == 0 else str(minutes)
    draw.text((x, y), min_text, fill=FG, font=font_display_xl)
    num_bbox = draw.textbbox((0, 0), min_text, font=font_display_xl)
    num_w = num_bbox[2] - num_bbox[0]
    num_h = num_bbox[3] - num_bbox[1]

    if minutes != 0:
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
    status: dict,
    x: int,
    y: int,
    width: int,
) -> int:
    """Draw a TfL line status row: line name left, status right.

    ``status`` keys: name, status_text, severity. Good service (severity 10)
    renders status in GRAY_MID; disruptions render in FG (black) for emphasis.
    Returns the y position below the row.
    """
    line_name = status["name"]
    status_text = status["status_text"]
    severity = status["severity"]

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
