"""Overlay images the Kindle caches for when the server is unreachable.

The Kindle displays server-rendered PNGs; FBInk can only draw text in the
framebuffer's portrait orientation, which would appear sideways on the
landscape dashboard. So the server pre-renders these overlays — rotated the
same way as the dashboard — and the Kindle fetches them after every
successful screen fetch, overlaying them locally once the server can no
longer be reached.
"""

from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageDraw

from .theme import BG, FG, font_section, font_small

BANNER_HEIGHT = 44
BOX_WIDTH = 360
BOX_HEIGHT = 120


def _to_png(img: Image.Image) -> bytes:
    # Rotate like the dashboard: landscape content into the portrait framebuffer.
    buf = BytesIO()
    img.rotate(-90, expand=True).save(buf, format="PNG")
    return buf.getvalue()


def render_disconnected_banner(since: str, width: int = 1024) -> bytes:
    """Full-width black banner: shown along the top of the frozen dashboard.

    ``since`` is stamped at render time, i.e. the moment of the fetch that
    cached this banner — which IS the last successful update.
    """
    img = Image.new("L", (width, BANNER_HEIGHT), FG)
    draw = ImageDraw.Draw(img)

    text = f"DISCONNECTED SINCE {since} — SHOWING OLD DATA"
    bbox = draw.textbbox((0, 0), text, font=font_section)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(
        ((width - tw) // 2 - bbox[0], (BANNER_HEIGHT - th) // 2 - bbox[1]),
        text,
        fill=BG,
        font=font_section,
    )
    return _to_png(img)


def render_offline_box() -> bytes:
    """Centred box flashed when a tap can't reach the server."""
    img = Image.new("L", (BOX_WIDTH, BOX_HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, BOX_WIDTH - 1, BOX_HEIGHT - 1], outline=FG, width=5)

    title = "OFFLINE"
    t_bbox = draw.textbbox((0, 0), title, font=font_section)
    tw = t_bbox[2] - t_bbox[0]
    draw.text(
        ((BOX_WIDTH - tw) // 2 - t_bbox[0], 26 - t_bbox[1]),
        title,
        fill=FG,
        font=font_section,
    )

    sub = "server unreachable"
    s_bbox = draw.textbbox((0, 0), sub, font=font_small)
    sw = s_bbox[2] - s_bbox[0]
    draw.text(
        ((BOX_WIDTH - sw) // 2 - s_bbox[0], 68 - s_bbox[1]),
        sub,
        fill=FG,
        font=font_small,
    )
    return _to_png(img)
