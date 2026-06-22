"""FastAPI application factory for KindlePad."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI

from server.config import load_config
from server.renderer.engine import RenderEngine
from server.routes import router

logger = logging.getLogger(__name__)

# Default config lives at the repo root (parent of the `server` package), so the
# server resolves the same file regardless of the current working directory.
DEFAULT_CONFIG_PATH = str(Path(__file__).resolve().parent.parent / "config.yaml")


def create_app(config_path: str | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    config = load_config(config_path or DEFAULT_CONFIG_PATH)

    if not config.server.token:
        logger.warning(
            "No server token configured — AUTHENTICATION IS DISABLED. "
            "Set server.token in config.yaml to require a Bearer token."
        )

    app = FastAPI(title="KindlePad", version="0.1.0")

    # Store config and engine on app state
    app.state.config = config
    app.state.engine = RenderEngine(config.screen)
    app.state.touchmap = None
    app.state.brightness_level = 2  # 0=off, 1=low, 2=med, 3=high

    # Attempt to initialize integration clients.
    # These modules may not be fully built yet, so we handle import errors.
    dirigera_client = None
    try:
        from server.integrations.dirigera_client import DirigeraClient

        if config.dirigera.hub_ip and config.dirigera.token:
            device_ids = [d.id for d in config.dirigera.devices]
            name_map = {d.id: d.name for d in config.dirigera.devices}
            dirigera_client = DirigeraClient(
                hub_ip=config.dirigera.hub_ip,
                token=config.dirigera.token,
                device_ids=device_ids,
                name_map=name_map,
            )
    except Exception as e:
        logger.warning("Failed to construct Dirigera client: %s", e, exc_info=True)
        dirigera_client = None
    app.state.dirigera_client = dirigera_client

    tfl_client = None
    try:
        from server.integrations.tfl_client import TflClient

        if config.tfl.lines or config.tfl.stations:
            lines = [
                {"id": ln.id, "display_name": ln.display_name}
                for ln in config.tfl.lines
            ]
            tfl_client = TflClient(
                lines=lines,
                refresh_interval=config.tfl.refresh_interval_seconds,
            )
    except Exception as e:
        logger.warning("Failed to construct TfL client: %s", e, exc_info=True)
        tfl_client = None
    app.state.tfl_client = tfl_client

    weather_client = None
    try:
        from server.integrations.weather_client import WeatherClient

        weather_client = WeatherClient(
            latitude=config.weather.latitude,
            longitude=config.weather.longitude,
        )
    except Exception as e:
        logger.warning("Failed to construct weather client: %s", e, exc_info=True)
        weather_client = None
    app.state.weather_client = weather_client

    sonos_client = None
    try:
        from server.integrations.sonos_client import Speaker, SonosClient

        if config.sonos.speakers:
            speakers = [
                Speaker(
                    id=s.id,
                    ip=s.ip,
                    name=s.name,
                    room=s.room,
                    max_volume=s.max_volume,
                    vol_step=s.vol_step,
                )
                for s in config.sonos.speakers
            ]
            sonos_client = SonosClient(speakers)
    except Exception as e:
        logger.warning("Failed to construct Sonos client: %s", e, exc_info=True)
        sonos_client = None
    app.state.sonos_client = sonos_client

    # Include routes
    app.include_router(router)

    return app
