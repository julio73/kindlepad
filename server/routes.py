"""API routes for KindlePad."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from pydantic import BaseModel

from server.auth import require_auth

router = APIRouter()


class TouchRequest(BaseModel):
    x: int
    y: int


@router.get("/screen", dependencies=[Depends(require_auth)])
async def get_screen(request: Request) -> Response:
    """Render the dashboard and return a grayscale PNG."""
    engine = request.app.state.engine
    tfl_client = request.app.state.tfl_client
    dirigera_client = request.app.state.dirigera_client
    config = request.app.state.config

    now = datetime.now().strftime("%H:%M")
    current_date = datetime.now().strftime("%a %d %b")

    # Build a mapping of device id -> room from config
    device_room_map: dict[str, str] = {
        d.id: d.room for d in config.dirigera.devices
    }

    # Fetch TfL statuses
    tfl_statuses: list[dict] = []
    if tfl_client is not None:
        try:
            statuses = await tfl_client.get_statuses()
            tfl_statuses = [
                {"name": s.name, "status_text": s.status_text, "severity": s.severity}
                for s in statuses
            ]
        except Exception:
            tfl_statuses = []

    # Fetch TfL departures
    departures: list[dict] = []
    if tfl_client is not None and config.tfl.stations:
        try:
            naptan_id = config.tfl.stations[0].naptan_id
            deps = await tfl_client.get_departures(naptan_id)
            departures = [
                {
                    "minutes": d.minutes,
                    "destination": d.destination,
                    "direction": d.direction,
                }
                for d in deps
            ]
        except Exception:
            departures = []

    # Fetch light states
    lights: list[dict] = []
    if dirigera_client is not None:
        try:
            light_states = dirigera_client.get_lights()
            lights = [
                {
                    "id": lt.id,
                    "name": lt.name,
                    "is_on": lt.is_on,
                    "room": device_room_map.get(lt.id, ""),
                }
                for lt in light_states
            ]
        except Exception:
            lights = []

    # Fall back to config-defined devices as mock data if no live data
    if not lights and config.dirigera.devices:
        lights = [
            {
                "id": d.id,
                "name": d.name,
                "is_on": False,
                "room": d.room,
            }
            for d in config.dirigera.devices
            if d.type == "light"
        ]

    brightness_level = getattr(request.app.state, "brightness_level", 2)

    png_bytes, touchmap = engine.render_dashboard(
        lights=lights,
        tfl_statuses=tfl_statuses,
        departures=departures,
        current_time=now,
        current_date=current_date,
        brightness_level=brightness_level,
    )

    # Store latest touchmap for touch resolution
    request.app.state.touchmap = touchmap

    return Response(content=png_bytes, media_type="image/png")


@router.post("/touch", dependencies=[Depends(require_auth)])
async def handle_touch(body: TouchRequest, request: Request) -> dict:
    """Resolve a touch event and dispatch the corresponding action."""
    touchmap = getattr(request.app.state, "touchmap", None)
    if touchmap is None:
        return {"action": None, "refresh": False}

    zone = touchmap.resolve(body.x, body.y)
    if zone is None:
        return {"action": None, "refresh": False}

    dirigera_client = request.app.state.dirigera_client

    # Dispatch actions
    refresh = False
    if zone.action in ("light_on", "light_off") and dirigera_client is not None:
        target_state = zone.action == "light_on"
        device_id = zone.params.get("device_id", "")
        try:
            dirigera_client.set_on(device_id, target_state)
            refresh = True
        except Exception:
            pass

    if zone.action == "toggle_light" and dirigera_client is not None:
        device_id = zone.params.get("device_id", "")
        try:
            dirigera_client.toggle(device_id)
            refresh = True
        except Exception:
            pass

    if zone.action == "set_brightness":
        level = zone.params.get("level", 2)
        request.app.state.brightness_level = level
        # Map level to actual brightness value for the Kindle
        brightness_map = {0: 0, 1: 512, 2: 1024, 3: 2048}
        refresh = True
        return {
            "action": zone.action,
            "refresh": refresh,
            "brightness": brightness_map.get(level, 1024),
        }

    return {"action": zone.action, "refresh": refresh}


@router.get("/health")
async def health() -> dict:
    """Health check endpoint — no auth required."""
    return {"status": "ok"}
