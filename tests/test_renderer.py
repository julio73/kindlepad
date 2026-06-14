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
    {"name": "Green Line", "status_text": "Good Service", "severity": 10},
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
        assert img.size == (758, 1024)
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
        assert img.size == (758, 1024)


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

        light_zones = [z for z in touchmap.zones if z.action in ("light_on", "light_off")]
        assert len(light_zones) == len(MOCK_LIGHTS)

        zone_ids = {z.params.get("device_id") for z in light_zones}
        expected_ids = {light["id"] for light in MOCK_LIGHTS}
        assert zone_ids == expected_ids

        # Lights that are ON should have light_off action, and vice versa
        for zone in light_zones:
            did = zone.params["device_id"]
            light = next(l for l in MOCK_LIGHTS if l["id"] == did)
            expected_action = "light_off" if light["is_on"] else "light_on"
            assert zone.action == expected_action


class TestRenderBrightnessZones:
    def test_render_brightness_zones(self):
        """The header should emit four set_brightness zones (levels 0-3)."""
        engine = RenderEngine(SCREEN)
        _, touchmap = engine.render_dashboard(
            lights=MOCK_LIGHTS,
            tfl_statuses=[],
            departures=[],
            current_time="04:35",
            current_date="Sat 29 Mar",
            brightness_level=2,
        )

        levels = sorted(
            z.params["level"] for z in touchmap.zones if z.action == "set_brightness"
        )
        assert levels == [0, 1, 2, 3]


class TestRenderStaleFlags:
    def test_render_stale_flags(self):
        """Stale flags should render without error and still produce a valid PNG."""
        engine = RenderEngine(SCREEN)
        png_bytes, _ = engine.render_dashboard(
            lights=MOCK_LIGHTS,
            tfl_statuses=MOCK_TFL,
            departures=MOCK_DEPARTURES,
            current_time="04:35",
            current_date="Sat 29 Mar",
            weather={"temperature": 9, "high": 11, "low": 4, "rain_chance": 80,
                     "condition_code": 61, "condition_text": "Rain"},
            lights_stale=True,
            tfl_stale=True,
            weather_stale=True,
        )

        assert png_bytes[:4] == PNG_MAGIC
        img = Image.open(io.BytesIO(png_bytes))
        assert img.size == (758, 1024)


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
        assert img.size == (758, 1024)
        assert img.mode == "L"
