"""Music control section: track title + 5 media-control buttons."""

from __future__ import annotations

from PIL import ImageDraw

from ...touchmap import TouchZone
from ..theme import FG, GRAY_MID, font_small
from .layout import draw_section_header, ellipsize


def _glyph_prev(draw: ImageDraw.ImageDraw, cx: int, cy: int, ink: int) -> None:
    # Bar + left-pointing triangle
    draw.rectangle([cx - 11, cy - 9, cx - 8, cy + 9], fill=ink)
    draw.polygon([(cx + 8, cy - 9), (cx + 8, cy + 9), (cx - 4, cy)], fill=ink)


def _glyph_next(draw: ImageDraw.ImageDraw, cx: int, cy: int, ink: int) -> None:
    draw.polygon([(cx - 8, cy - 9), (cx - 8, cy + 9), (cx + 4, cy)], fill=ink)
    draw.rectangle([cx + 8, cy - 9, cx + 11, cy + 9], fill=ink)


def _glyph_play(draw: ImageDraw.ImageDraw, cx: int, cy: int, ink: int) -> None:
    draw.polygon([(cx - 9, cy - 11), (cx - 9, cy + 11), (cx + 10, cy)], fill=ink)


def _glyph_pause(draw: ImageDraw.ImageDraw, cx: int, cy: int, ink: int) -> None:
    draw.rectangle([cx - 8, cy - 10, cx - 3, cy + 10], fill=ink)
    draw.rectangle([cx + 3, cy - 10, cx + 8, cy + 10], fill=ink)


def _glyph_vol_down(draw: ImageDraw.ImageDraw, cx: int, cy: int, ink: int) -> None:
    draw.rectangle([cx - 11, cy - 2, cx + 11, cy + 2], fill=ink)


def _glyph_vol_up(draw: ImageDraw.ImageDraw, cx: int, cy: int, ink: int) -> None:
    draw.rectangle([cx - 11, cy - 2, cx + 11, cy + 2], fill=ink)
    draw.rectangle([cx - 2, cy - 11, cx + 2, cy + 11], fill=ink)


_MEDIA_GLYPHS = {
    "prev": _glyph_prev,
    "next": _glyph_next,
    "play": _glyph_play,
    "pause": _glyph_pause,
    "vol_down": _glyph_vol_down,
    "vol_up": _glyph_vol_up,
}


def _draw_media_glyph(
    draw: ImageDraw.ImageDraw,
    kind: str,
    cx: int,
    cy: int,
    ink: int,
) -> None:
    """Draw filled media-control glyphs centered on (cx, cy)."""
    handler = _MEDIA_GLYPHS.get(kind)
    if handler is not None:
        handler(draw, cx, cy, ink)


def draw_music_section(
    draw: ImageDraw.ImageDraw,
    sonos: dict,
    x: int,
    y: int,
    width: int,
    stale: bool = False,
    stale_since: str | None = None,
) -> tuple[int, list[TouchZone]]:
    """Draw the music control section: header, track title, 5 control buttons.

    `sonos` keys: speaker_id, room, name, is_playing, track_title.
    When ``stale`` is set the header shows an "offline" marker (with the time
    of the last successful fetch, when known).
    Returns (new_y, list of TouchZones).
    """
    zones: list[TouchZone] = []
    speaker_id = sonos.get("speaker_id", "")
    room = sonos.get("room") or sonos.get("name") or "Music"
    is_playing = bool(sonos.get("is_playing", False))
    title = (sonos.get("track_title") or "").strip()

    # Section header
    if stale:
        subtitle = f"offline since {stale_since}" if stale_since else "offline"
    else:
        subtitle = room
    y = draw_section_header(draw, f"MUSIC · {subtitle}", x, y)

    # Track title row (em-dash placeholder when nothing playing)
    label = title if title else "—"
    label = ellipsize(draw, label, width, font_small)
    draw.text((x, y), label, fill=GRAY_MID, font=font_small)
    bbox = draw.textbbox((0, 0), label, font=font_small)
    y += (bbox[3] - bbox[1]) + 12

    # 5 equal-width buttons
    gap = 6
    btn_w = (width - 4 * gap) // 5
    btn_h = 56
    buttons = [
        ("sonos_prev", "prev"),
        ("sonos_vol_down", "vol_down"),
        ("sonos_play_pause", "pause" if is_playing else "play"),
        ("sonos_vol_up", "vol_up"),
        ("sonos_next", "next"),
    ]
    bx = x
    for action, kind in buttons:
        filled = action == "sonos_play_pause" and is_playing
        if filled:
            draw.rectangle([bx, y, bx + btn_w, y + btn_h], fill=FG)
            ink = 255
        else:
            draw.rectangle(
                [bx, y, bx + btn_w, y + btn_h],
                fill=255,
                outline=FG,
                width=2,
            )
            ink = FG
        _draw_media_glyph(draw, kind, bx + btn_w // 2, y + btn_h // 2, ink)
        zones.append(
            TouchZone(
                x=bx,
                y=y,
                width=btn_w,
                height=btn_h,
                action=action,
                params={"speaker_id": speaker_id},
            )
        )
        bx += btn_w + gap

    y += btn_h
    return y, zones
