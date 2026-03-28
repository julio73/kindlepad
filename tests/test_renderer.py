"""Tests for the rendering engine producing valid PNG output."""

import io

from PIL import Image

from server.renderer.engine import RenderEngine
from server.config import ScreenConfig


MOCK_LIGHTS = [{"id": "abc", "name": "Living Room", "is_on": True}]
MOCK_TFL = [{"name": "Green Line", "status_text": "Good Service", "severity": 10}]
SCREEN = ScreenConfig(width=1072, height=1448)

PNG_MAGIC = b"\x89PNG"


class TestRenderProducesPng:
    def test_render_produces_png(self):
        """render_dashboard should return bytes starting with PNG magic."""
        engine = RenderEngine(SCREEN)
        png_bytes, touchmap = engine.render_dashboard(
            lights=MOCK_LIGHTS, tfl_statuses=MOCK_TFL, current_time="14:35"
        )

        assert isinstance(png_bytes, bytes)
        assert png_bytes[:4] == PNG_MAGIC


class TestRenderDimensions:
    def test_render_dimensions(self):
        """Rendered PNG should be 1072x1448 in grayscale (mode 'L')."""
        engine = RenderEngine(SCREEN)
        png_bytes, touchmap = engine.render_dashboard(
            lights=MOCK_LIGHTS, tfl_statuses=MOCK_TFL, current_time="14:35"
        )

        img = Image.open(io.BytesIO(png_bytes))
        assert img.size == (1072, 1448)
        assert img.mode == "L"


class TestRenderWithEmptyData:
    def test_render_with_empty_data(self):
        """Empty lights and tfl lists should still produce a valid PNG."""
        engine = RenderEngine(SCREEN)
        png_bytes, touchmap = engine.render_dashboard(
            lights=[], tfl_statuses=[], current_time="14:35"
        )

        assert isinstance(png_bytes, bytes)
        assert png_bytes[:4] == PNG_MAGIC
        img = Image.open(io.BytesIO(png_bytes))
        assert img.size == (1072, 1448)


class TestRenderTouchZones:
    def test_light_toggle_creates_zones(self):
        """Rendering lights should produce touch zones for ON/OFF buttons."""
        engine = RenderEngine(SCREEN)
        _, touchmap = engine.render_dashboard(
            lights=MOCK_LIGHTS, tfl_statuses=[], current_time="14:35"
        )

        assert len(touchmap.zones) == 2
        actions = {z.action for z in touchmap.zones}
        assert actions == {"light_on", "light_off"}
        assert all(z.params.get("device_id") == "abc" for z in touchmap.zones)
