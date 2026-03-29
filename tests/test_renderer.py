"""Tests for the rendering engine producing valid PNG output."""

import io

from PIL import Image

from server.renderer.engine import RenderEngine
from server.config import ScreenConfig


MOCK_LIGHTS = [
    {"id": "abc", "name": "Lamp 1", "is_on": True, "room": "Living Room"},
    {"id": "def", "name": "Lamp 2", "is_on": False, "room": "Living Room"},
    {"id": "ghi", "name": "Hallway", "is_on": True, "room": "Hallway"},
]
MOCK_TFL = [
    {"name": "Blue Line", "status_text": "Good Service", "severity": 10},
    {"name": "Red Line", "status_text": "Part Closure", "severity": 6},
]
MOCK_DEPARTURES = [
    {"destination": "Northtown", "minutes": 2, "direction": "Eastbound"},
    {"destination": "Southbury", "minutes": 5, "direction": "Westbound"},
]
SCREEN = ScreenConfig(width=1024, height=758)

PNG_MAGIC = b"\x89PNG"


class TestRenderProducesPng:
    def test_render_produces_png(self):
        """render_dashboard should return bytes starting with PNG magic."""
        engine = RenderEngine(SCREEN)
        png_bytes, touchmap = engine.render_dashboard(
            lights=MOCK_LIGHTS,
            tfl_statuses=MOCK_TFL,
            departures=MOCK_DEPARTURES,
            current_time="04:35",
            current_date="Sat 29 Mar",
        )

        assert isinstance(png_bytes, bytes)
        assert png_bytes[:4] == PNG_MAGIC


class TestRenderLandscapeDimensions:
    def test_render_landscape_dimensions(self):
        """Rendered PNG should be 1024x758 in grayscale (mode 'L')."""
        engine = RenderEngine(SCREEN)
        png_bytes, touchmap = engine.render_dashboard(
            lights=MOCK_LIGHTS,
            tfl_statuses=MOCK_TFL,
            departures=MOCK_DEPARTURES,
            current_time="04:35",
            current_date="Sat 29 Mar",
        )

        img = Image.open(io.BytesIO(png_bytes))
        assert img.size == (1024, 758)
        assert img.mode == "L"


class TestRenderWithEmptyData:
    def test_render_with_empty_data(self):
        """Empty lights, tfl, and departures lists should still produce a valid PNG."""
        engine = RenderEngine(SCREEN)
        png_bytes, touchmap = engine.render_dashboard(
            lights=[],
            tfl_statuses=[],
            departures=[],
            current_time="04:35",
            current_date="Sat 29 Mar",
        )

        assert isinstance(png_bytes, bytes)
        assert png_bytes[:4] == PNG_MAGIC
        img = Image.open(io.BytesIO(png_bytes))
        assert img.size == (1024, 758)


class TestRenderTouchZones:
    def test_render_touch_zones(self):
        """Rendering lights should produce toggle_light touch zones."""
        engine = RenderEngine(SCREEN)
        _, touchmap = engine.render_dashboard(
            lights=MOCK_LIGHTS,
            tfl_statuses=[],
            departures=[],
            current_time="04:35",
            current_date="Sat 29 Mar",
        )

        toggle_zones = [z for z in touchmap.zones if z.action == "toggle_light"]
        assert len(toggle_zones) == len(MOCK_LIGHTS)

        zone_ids = {z.params.get("device_id") for z in toggle_zones}
        expected_ids = {light["id"] for light in MOCK_LIGHTS}
        assert zone_ids == expected_ids


class TestRenderWithDepartures:
    def test_render_with_departures(self):
        """Departures data should render without error and produce valid PNG."""
        engine = RenderEngine(SCREEN)
        png_bytes, touchmap = engine.render_dashboard(
            lights=MOCK_LIGHTS,
            tfl_statuses=MOCK_TFL,
            departures=MOCK_DEPARTURES,
            current_time="04:35",
            current_date="Sat 29 Mar",
        )

        assert isinstance(png_bytes, bytes)
        assert png_bytes[:4] == PNG_MAGIC
        img = Image.open(io.BytesIO(png_bytes))
        assert img.size == (1024, 758)
        assert img.mode == "L"
