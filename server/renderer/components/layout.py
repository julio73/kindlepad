"""Structural layout components: header, section labels, dividers, footer."""

from __future__ import annotations

from PIL import ImageDraw

from ..theme import (
    FG,
    GRAY_DARK,
    GRAY_LIGHT,
    GRAY_MID,
    PADDING,
    SECTION_GAP,
    font_body,
    font_display,
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
    if " · " in label:
        main_part, sub_part = label.split(" · ", 1)
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


def draw_no_data_row(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
) -> int:
    """Placeholder body for a section whose source is down with nothing cached.

    Returns the y position below the row.
    """
    draw.text((x, y), "no data", fill=GRAY_MID, font=font_small)
    bbox = draw.textbbox((0, 0), "no data", font=font_small)
    return y + (bbox[3] - bbox[1]) + 8


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


def ellipsize(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    font,
) -> str:
    """Trim text to fit max_width, appending an ellipsis if truncated."""
    if not text:
        return ""
    bbox = draw.textbbox((0, 0), text, font=font)
    if bbox[2] - bbox[0] <= max_width:
        return text

    ell = "…"
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi) // 2
        candidate = text[:mid].rstrip() + ell
        cb = draw.textbbox((0, 0), candidate, font=font)
        if cb[2] - cb[0] <= max_width:
            lo = mid + 1
        else:
            hi = mid
    return (text[: max(0, lo - 1)].rstrip() + ell) if lo > 0 else ell
