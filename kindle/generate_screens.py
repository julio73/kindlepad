#!/usr/bin/env python3
"""Generate static e-ink screens (sleep + loading) for KindlePad.

Run once from the repo root:
    python kindle/generate_screens.py

Produces kindle/sleep.png and kindle/loading.png (758x1024 portrait,
matching the Kindle PW3 framebuffer after rotation).
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw

# Reuse the project's theme if available, fall back to defaults
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from server.renderer.theme import BG, FG, GRAY_MID, font_display, font_body
except ImportError:
    from PIL import ImageFont
    BG, FG, GRAY_MID = 255, 0, 100
    font_display = ImageFont.load_default()
    font_body = ImageFont.load_default()

WIDTH, HEIGHT = 1024, 758  # landscape, rotated later


def _centered_text(draw, text, font, fill, y, width):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    draw.text(((width - tw) // 2, y), text, fill=fill, font=font)


def make_sleep_screen(path):
    img = Image.new("L", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    cy = HEIGHT // 2

    _centered_text(draw, "KINDLEPAD", font_display, GRAY_MID, cy - 50, WIDTH)
    _centered_text(draw, "Tap to wake", font_body, GRAY_MID, cy + 10, WIDTH)

    img.rotate(-90, expand=True).save(path, "PNG")
    print(f"  {path}")


def make_loading_screen(path):
    img = Image.new("L", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    cy = HEIGHT // 2

    _centered_text(draw, "Loading...", font_display, GRAY_MID, cy - 20, WIDTH)

    img.rotate(-90, expand=True).save(path, "PNG")
    print(f"  {path}")


if __name__ == "__main__":
    out = Path(__file__).resolve().parent
    print("Generating static screens:")
    make_sleep_screen(str(out / "sleep.png"))
    make_loading_screen(str(out / "loading.png"))
