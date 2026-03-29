"""Drawing components for the KindlePad dashboard."""

from __future__ import annotations

from PIL import ImageDraw

from server.touchmap import TouchZone

from .theme import (
    BG,
    FG,
    GRAY_MID,
    PADDING,
    ROW_HEIGHT,
    SECTION_GAP,
    font_body,
    font_heading,
    font_small,
)

# Screen width will be set by the engine before rendering.
SCREEN_WIDTH = 758


def draw_header(draw: ImageDraw.ImageDraw, title: str, time_str: str, y: int) -> int:
    """Draw title left-aligned, time right-aligned, then a separator line."""
    # Title on the left
    draw.text((PADDING, y), title, fill=FG, font=font_heading)

    # Time on the right
    time_bbox = draw.textbbox((0, 0), time_str, font=font_heading)
    time_width = time_bbox[2] - time_bbox[0]
    draw.text((SCREEN_WIDTH - PADDING - time_width, y), time_str, fill=FG, font=font_heading)

    # Advance past the text
    title_bbox = draw.textbbox((0, 0), title, font=font_heading)
    text_height = title_bbox[3] - title_bbox[1]
    y += text_height + 16

    # Separator line
    draw.line([(PADDING, y), (SCREEN_WIDTH - PADDING, y)], fill=FG, width=2)
    y += SECTION_GAP

    return y


def draw_section_header(draw: ImageDraw.ImageDraw, label: str, y: int) -> int:
    """Draw a section label in BODY font."""
    draw.text((PADDING, y), label, fill=FG, font=font_body)
    bbox = draw.textbbox((0, 0), label, font=font_body)
    text_height = bbox[3] - bbox[1]
    y += text_height + 12
    return y


def draw_tfl_row(
    draw: ImageDraw.ImageDraw,
    line_name: str,
    status_text: str,
    severity: int,
    y: int,
) -> int:
    """Draw a TfL line status row: line name left, status right."""
    color = GRAY_MID if severity == 10 else FG

    draw.text((PADDING + 10, y), line_name, fill=FG, font=font_body)

    status_bbox = draw.textbbox((0, 0), status_text, font=font_body)
    status_width = status_bbox[2] - status_bbox[0]
    draw.text(
        (SCREEN_WIDTH - PADDING - status_width, y),
        status_text,
        fill=color,
        font=font_body,
    )

    y += ROW_HEIGHT
    return y


def draw_light_toggle(
    draw: ImageDraw.ImageDraw,
    name: str,
    is_on: bool,
    device_id: str,
    y: int,
) -> tuple[int, list[TouchZone]]:
    """Draw a light toggle with ON/OFF buttons side by side."""
    BUTTON_WIDTH = 330
    BUTTON_HEIGHT = 90
    GAP = 12

    # Device name
    draw.text((PADDING, y), name, fill=FG, font=font_body)
    name_bbox = draw.textbbox((0, 0), name, font=font_body)
    name_height = name_bbox[3] - name_bbox[1]
    y += name_height + 10

    # Button positions
    on_x = PADDING
    off_x = PADDING + BUTTON_WIDTH + GAP
    btn_y = y

    # ON button
    if is_on:
        # Active: filled black with white text
        draw.rectangle(
            [on_x, btn_y, on_x + BUTTON_WIDTH, btn_y + BUTTON_HEIGHT],
            fill=FG,
        )
        on_text_color = BG
    else:
        # Inactive: white with black border
        draw.rectangle(
            [on_x, btn_y, on_x + BUTTON_WIDTH, btn_y + BUTTON_HEIGHT],
            fill=BG,
            outline=FG,
            width=2,
        )
        on_text_color = FG

    on_label = "ON"
    on_bbox = draw.textbbox((0, 0), on_label, font=font_body)
    on_tw = on_bbox[2] - on_bbox[0]
    on_th = on_bbox[3] - on_bbox[1]
    draw.text(
        (on_x + (BUTTON_WIDTH - on_tw) // 2, btn_y + (BUTTON_HEIGHT - on_th) // 2),
        on_label,
        fill=on_text_color,
        font=font_body,
    )

    # OFF button
    if not is_on:
        # Active: filled black with white text
        draw.rectangle(
            [off_x, btn_y, off_x + BUTTON_WIDTH, btn_y + BUTTON_HEIGHT],
            fill=FG,
        )
        off_text_color = BG
    else:
        # Inactive: white with black border
        draw.rectangle(
            [off_x, btn_y, off_x + BUTTON_WIDTH, btn_y + BUTTON_HEIGHT],
            fill=BG,
            outline=FG,
            width=2,
        )
        off_text_color = FG

    off_label = "OFF"
    off_bbox = draw.textbbox((0, 0), off_label, font=font_body)
    off_tw = off_bbox[2] - off_bbox[0]
    off_th = off_bbox[3] - off_bbox[1]
    draw.text(
        (off_x + (BUTTON_WIDTH - off_tw) // 2, btn_y + (BUTTON_HEIGHT - off_th) // 2),
        off_label,
        fill=off_text_color,
        font=font_body,
    )

    # Touch zones
    zones = [
        TouchZone(
            x=on_x,
            y=btn_y,
            width=BUTTON_WIDTH,
            height=BUTTON_HEIGHT,
            action="light_on",
            params={"device_id": device_id},
        ),
        TouchZone(
            x=off_x,
            y=btn_y,
            width=BUTTON_WIDTH,
            height=BUTTON_HEIGHT,
            action="light_off",
            params={"device_id": device_id},
        ),
    ]

    y = btn_y + BUTTON_HEIGHT + SECTION_GAP
    return y, zones


def draw_footer(draw: ImageDraw.ImageDraw, timestamp: str, y: int) -> int:
    """Draw 'Last updated: {timestamp}' at the bottom in SMALL font."""
    text = f"Last updated: {timestamp}"
    bbox = draw.textbbox((0, 0), text, font=font_small)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    draw.text(
        ((SCREEN_WIDTH - text_width) // 2, y),
        text,
        fill=GRAY_MID,
        font=font_small,
    )

    y += text_height + PADDING
    return y
