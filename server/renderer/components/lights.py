"""Light controls: power button, brightness stepper, and light toggles."""

from __future__ import annotations

from PIL import ImageDraw

from ...touchmap import TouchZone
from ..theme import FG, GRAY_MID, font_small


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
    draw.arc(
        [cx - r, cy - r, cx + r, cy + r], start=40, end=320, fill=GRAY_MID, width=2
    )
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


def draw_brightness_control(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    current_level: int,
) -> list[TouchZone]:
    """Draw a 4-step brightness stepper (off → high) as increasing bars.

    Bars up to ``current_level`` are filled; the rest are outlined. Each bar is
    a tap target emitting ``set_brightness`` with its level (0-3), wired through
    to the Kindle backlight sysfs write.
    """
    zones: list[TouchZone] = []
    bar_w = 16
    pitch = 22
    base_y = y + 26  # common bottom baseline
    heights = [8, 13, 18, 23]
    for i, h in enumerate(heights):
        bx = x + i * pitch
        top = base_y - h
        if i <= current_level:
            draw.rectangle([bx, top, bx + bar_w, base_y], fill=FG)
        else:
            draw.rectangle([bx, top, bx + bar_w, base_y], outline=GRAY_MID, width=2)
        zones.append(
            TouchZone(
                x=bx - 3,
                y=y - 4,
                width=pitch,
                height=base_y - y + 12,
                action="set_brightness",
                params={"level": i},
            )
        )
    return zones


def draw_light_button(
    draw: ImageDraw.ImageDraw,
    light: dict,
    x: int,
    y: int,
    width: int,
) -> tuple[int, TouchZone]:
    """Draw a single toggle button for a light.

    ``light`` keys: name, is_on, id. ON = filled black with white text;
    OFF = white with black 2px outline. Returns (new_y, TouchZone).
    """
    name = light["name"]
    is_on = light["is_on"]
    device_id = light["id"]

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
            y1, zone1 = draw_light_button(draw, room_lights[i], x, y, btn_w)
            y2, zone2 = draw_light_button(
                draw, room_lights[i + 1], x + btn_w + btn_gap, y, btn_w
            )
            zones.extend([zone1, zone2])
            y = max(y1, y2)
            i += 2
        else:
            # Single button -- same half-width size
            y, zone = draw_light_button(draw, room_lights[i], x, y, btn_w)
            zones.append(zone)
            i += 1
    return y, zones
