"""FastAPI application factory for KindlePad."""

from __future__ import annotations

from fastapi import FastAPI

from server.config import load_config
from server.renderer.engine import RenderEngine
from server.routes import router


def create_app(config_path: str = "config.yaml") -> FastAPI:
    """Create and configure the FastAPI application."""
    config = load_config(config_path)

    app = FastAPI(title="KindlePad", version="0.1.0")

    # Store config and engine on app state
    app.state.config = config
    app.state.engine = RenderEngine(config.screen)
    app.state.touchmap = None

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
    except (ImportError, Exception):
        pass
    app.state.dirigera_client = dirigera_client

    tfl_client = None
    try:
        from server.integrations.tfl_client import TflClient

        if config.tfl.lines:
            lines = [{"id": l.id, "display_name": l.display_name} for l in config.tfl.lines]
            tfl_client = TflClient(
                lines=lines,
                refresh_interval=config.tfl.refresh_interval_seconds,
            )
    except (ImportError, Exception):
        pass
    app.state.tfl_client = tfl_client

    # Include routes
    app.include_router(router)

    return app
