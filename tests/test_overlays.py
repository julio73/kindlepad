"""Tests for the offline overlay images served to the Kindle."""

import io

from PIL import Image

from server.renderer.overlays import (
    BANNER_HEIGHT,
    BOX_HEIGHT,
    BOX_WIDTH,
    render_disconnected_banner,
    render_offline_box,
)

PNG_MAGIC = b"\x89PNG"


class TestDisconnectedBanner:
    def test_banner_is_rotated_png(self):
        """Banner should be a valid PNG rotated for the portrait framebuffer."""
        png_bytes = render_disconnected_banner("14:02", width=1024)
        assert png_bytes[:4] == PNG_MAGIC
        img = Image.open(io.BytesIO(png_bytes))
        assert img.size == (BANNER_HEIGHT, 1024)
        assert img.mode == "L"

    def test_banner_varies_with_since(self):
        """Different timestamps must produce different pixels."""
        a = render_disconnected_banner("14:02")
        b = render_disconnected_banner("09:41")
        assert a != b


class TestOfflineBox:
    def test_box_is_rotated_png(self):
        png_bytes = render_offline_box()
        assert png_bytes[:4] == PNG_MAGIC
        img = Image.open(io.BytesIO(png_bytes))
        assert img.size == (BOX_HEIGHT, BOX_WIDTH)
        assert img.mode == "L"
