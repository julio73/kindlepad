"""Grayscale theme constants and font loading for e-ink rendering.

Editorial utilitarian design system: DIN Condensed + Avenir Next.
Think London Underground signage meets broadsheet newspaper.
"""

from __future__ import annotations

from typing import Union

from pathlib import Path

from PIL import ImageFont

# --- Font directory (bundled fonts for portability) ---
_FONT_DIR = str(Path(__file__).resolve().parent.parent.parent / "fonts")

# --- Grayscale palette ---
BG = 255        # white
FG = 0          # black
GRAY_LIGHT = 180
GRAY_MID = 100  # darker than before for e-ink readability
GRAY_DARK = 60

# --- Font loading ---
# Display: DIN Condensed Bold (transit signage feel)
# Heading: DIN Alternate Bold (section headers)
# Body:    Avenir Next (clean, readable)
# Each loader falls back through system fonts, then to the bitmap default.

_SYSTEM_FALLBACKS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/SFCompact.ttf",
    "/System/Library/Fonts/SFNS.ttf",
]


def _try_load(paths: list[str], size: int) -> Union[ImageFont.FreeTypeFont, ImageFont.ImageFont, None]:
    """Try loading a TrueType font from a list of candidate paths."""
    for path in paths:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return None


def _load_default(size: int) -> Union[ImageFont.FreeTypeFont, ImageFont.ImageFont]:
    """Load the Pillow default font, sized if possible."""
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _load_display_font(size: int) -> Union[ImageFont.FreeTypeFont, ImageFont.ImageFont]:
    """Load DIN Condensed Bold for display numerals, falling back to system fonts."""
    return (
        _try_load([f"{_FONT_DIR}/DIN Condensed Bold.ttf", "/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf"], size)
        or _try_load(_SYSTEM_FALLBACKS, size)
        or _load_default(size)
    )


def _load_heading_font(size: int) -> Union[ImageFont.FreeTypeFont, ImageFont.ImageFont]:
    """Load DIN Alternate Bold for section headers."""
    return (
        _try_load([f"{_FONT_DIR}/DIN Alternate Bold.ttf", "/System/Library/Fonts/Supplemental/DIN Alternate Bold.ttf"], size)
        or _try_load(_SYSTEM_FALLBACKS, size)
        or _load_display_font(size)
    )


def _load_body_font(size: int) -> Union[ImageFont.FreeTypeFont, ImageFont.ImageFont]:
    """Load Avenir Next for body text."""
    return (
        _try_load([f"{_FONT_DIR}/Avenir Next.ttc", "/System/Library/Fonts/Avenir Next.ttc"], size)
        or _try_load(_SYSTEM_FALLBACKS, size)
        or _load_display_font(size)
    )


# --- Font instances ---
font_display_xl = _load_display_font(48)   # departure minutes (hero element)
font_display = _load_display_font(38)       # "KINDLEPAD" header
font_section = _load_heading_font(26)       # "NEXT TRAINS", "LIGHTS"
font_body = _load_body_font(22)             # destinations, line names
font_small = _load_body_font(16)            # "min", station names, room labels

# Legacy aliases so any straggling imports still work
font_heading = font_display
font_label = font_section

# --- Spacing ---
PADDING = 24
SECTION_GAP = 20
ROW_HEIGHT = 52
DIVIDER_X = 614   # ~60% of 1024
PANEL_GAP = 20
