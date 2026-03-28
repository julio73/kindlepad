"""Grayscale theme constants and font loading for e-ink rendering."""

from __future__ import annotations

from typing import Union

from PIL import ImageFont

# --- Grayscale palette ---
BG = 255
FG = 0
GRAY_LIGHT = 200
GRAY_MID = 140
GRAY_DARK = 80

# --- Font sizes ---
HEADING = 42
BODY = 32
SMALL = 24
LABEL = 28

# --- Font loading ---
# Pillow 11+ supports ImageFont.load_default(size=N).
# Older versions need a TrueType font file or the basic default bitmap font.


def _load_font(size: int) -> Union[ImageFont.FreeTypeFont, ImageFont.ImageFont]:
    """Load a font at the given size, with fallbacks for older Pillow."""
    # Try Pillow 11+ sized default first
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        pass

    # Try common system TrueType fonts
    for path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFCompact.ttf",
        "/System/Library/Fonts/SFNS.ttf",
    ]:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue

    # Last resort: unsized default bitmap font
    return ImageFont.load_default()


font_heading = _load_font(HEADING)
font_body = _load_font(BODY)
font_small = _load_font(SMALL)
font_label = _load_font(LABEL)

# --- Spacing ---
PADDING = 40
SECTION_GAP = 30
ROW_HEIGHT = 70
