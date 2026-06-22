"""API routes for KindlePad."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from pydantic import BaseModel

from server.auth import require_auth

logger = logging.getLogger(__name__)

router = APIRouter()


class TouchRequest(BaseModel):
    x: int
    y: int


def _parse_battery(raw: str | None) -> int | None:
    """Parse the ``battery`` query param into a 0-100 percentage, or None."""
    if not (raw and raw.isdigit()):
        return None
    return min(int(raw), 100)


async def _collect_tfl(tfl_client, config) -> tuple[list[dict], list[dict], bool]:
    """Fetch line statuses and departures. Returns (statuses, departures, stale)."""
    if tfl_client is None:
        return [], [], False

    tfl_statuses: list[dict] = []
    try:
        statuses = await tfl_client.get_statuses()
        tfl_statuses = [
            {"name": s.name, "status_text": s.status_text, "severity": s.severity}
            for s in statuses
        ]
    except Exception as e:
        logger.warning("Failed to fetch TfL statuses: %s", e, exc_info=True)
        tfl_statuses = []

    departures: list[dict] = []
    if config.tfl.stations:
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
        except Exception as e:
            logger.warning("Failed to fetch TfL departures: %s", e, exc_info=True)
            departures = []

    return tfl_statuses, departures, not tfl_client.last_ok


async def _collect_lights(dirigera_client, config) -> tuple[list[dict], bool]:
    """Fetch light states, falling back to config devices. Returns (lights, stale)."""
    device_room_map = {d.id: d.room for d in config.dirigera.devices}

    lights: list[dict] = []
    lights_stale = False
    if dirigera_client is not None:
        try:
            light_states = await asyncio.to_thread(dirigera_client.get_lights)
            lights = [
                {
                    "id": lt.id,
                    "name": lt.name,
                    "is_on": lt.is_on,
                    "room": device_room_map.get(lt.id, ""),
                }
                for lt in light_states
            ]
            lights_stale = not dirigera_client.last_ok
        except Exception as e:
            logger.warning("Failed to fetch light states: %s", e, exc_info=True)
            lights = []
            lights_stale = True

    # Fall back to config-defined devices if no live data. This is NOT real
    # state — mark it stale so the panel shows an "offline" marker rather than
    # confidently rendering every light as OFF.
    if not lights and config.dirigera.devices:
        lights = [
            {"id": d.id, "name": d.name, "is_on": False, "room": d.room}
            for d in config.dirigera.devices
            if d.type == "light"
        ]
        if lights:
            lights_stale = True

    return lights, lights_stale


async def _collect_weather(weather_client) -> tuple[dict | None, bool]:
    """Fetch weather (blocking httpx call → off the event loop). Returns (weather, stale)."""
    if weather_client is None:
        return None, False

    weather: dict | None = None
    try:
        wd = await asyncio.to_thread(weather_client.get_weather)
        if wd is not None:
            weather = {
                "temperature": wd.temperature,
                "high": wd.high,
                "low": wd.low,
                "rain_chance": wd.rain_chance,
                "condition_code": wd.condition_code,
                "condition_text": wd.condition_text,
            }
    except Exception as e:
        logger.warning("Failed to fetch weather: %s", e, exc_info=True)
        weather = None

    weather_stale = weather is not None and not weather_client.last_ok
    return weather, weather_stale


async def _collect_sonos(sonos_client, config) -> tuple[dict | None, bool]:
    """Fetch state for the first configured speaker. Returns (sonos, stale)."""
    if sonos_client is None or not config.sonos.speakers:
        return None, False

    sp = config.sonos.speakers[0]
    try:
        state = await asyncio.to_thread(sonos_client.get_state, sp.id)
        sonos = {
            "speaker_id": state.speaker_id,
            "name": sp.name,
            "room": sp.room,
            "is_playing": state.is_playing,
            "volume": state.volume,
            "track_title": state.track_title,
        }
        return sonos, False
    except Exception as e:
        logger.warning("Failed to fetch Sonos state: %s", e, exc_info=True)
        sonos = {
            "speaker_id": sp.id,
            "name": sp.name,
            "room": sp.room,
            "is_playing": False,
            "volume": 0,
            "track_title": "",
        }
        return sonos, True


@router.get("/screen", dependencies=[Depends(require_auth)])
async def get_screen(request: Request) -> Response:
    """Render the dashboard and return a grayscale PNG."""
    engine = request.app.state.engine
    config = request.app.state.config

    now = datetime.now().strftime("%H:%M")
    current_date = datetime.now().strftime("%a %d %b")
    battery_pct = _parse_battery(request.query_params.get("battery"))
    is_charging = request.query_params.get("charging", "0") == "1"

    tfl_statuses, departures, tfl_stale = await _collect_tfl(
        request.app.state.tfl_client, config
    )
    lights, lights_stale = await _collect_lights(
        request.app.state.dirigera_client, config
    )
    weather, weather_stale = await _collect_weather(
        getattr(request.app.state, "weather_client", None)
    )
    sonos, sonos_stale = await _collect_sonos(
        getattr(request.app.state, "sonos_client", None), config
    )

    station_name = config.tfl.stations[0].display_name if config.tfl.stations else None

    png_bytes, touchmap = engine.render_dashboard(
        lights=lights,
        tfl_statuses=tfl_statuses,
        departures=departures,
        current_time=now,
        current_date=current_date,
        weather=weather,
        battery_pct=battery_pct,
        is_charging=is_charging,
        station_name=station_name,
        sonos=sonos,
        brightness_level=getattr(request.app.state, "brightness_level", 2),
        lights_stale=lights_stale,
        tfl_stale=tfl_stale,
        weather_stale=weather_stale,
        sonos_stale=sonos_stale,
    )

    # Store latest touchmap for touch resolution.
    # NOTE: this is a single global slot. It assumes ONE client (the Kindle).
    # A second concurrent fetcher (e.g. a curious `curl /screen`) would overwrite
    # the map between the Kindle's fetch and its tap, resolving the tap against
    # the wrong layout. Fine for the single-panel setup; key by client if that
    # ever changes.
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
    sonos_client = getattr(request.app.state, "sonos_client", None)

    refresh = False
    if zone.action == "screen_off":
        return {"action": "screen_off", "refresh": False}

    elif zone.action in ("light_on", "light_off") and dirigera_client is not None:
        target_state = zone.action == "light_on"
        device_id = zone.params.get("device_id", "")
        try:
            await asyncio.to_thread(dirigera_client.set_on, device_id, target_state)
            refresh = True
        except Exception as e:
            logger.warning("Failed to set light %s: %s", device_id, e, exc_info=True)
            refresh = False

    elif (
        zone.action
        in (
            "sonos_play_pause",
            "sonos_vol_up",
            "sonos_vol_down",
            "sonos_next",
            "sonos_prev",
        )
        and sonos_client is not None
    ):
        speaker_id = zone.params.get("speaker_id", "")
        sonos_dispatch = {
            "sonos_play_pause": sonos_client.play_pause,
            "sonos_vol_up": sonos_client.vol_up,
            "sonos_vol_down": sonos_client.vol_down,
            "sonos_next": sonos_client.next,
            "sonos_prev": sonos_client.previous,
        }
        try:
            await asyncio.to_thread(sonos_dispatch[zone.action], speaker_id)
            refresh = True
        except Exception as e:
            logger.warning("Failed Sonos action %s: %s", zone.action, e, exc_info=True)
            refresh = False

    elif zone.action == "set_brightness":
        level = zone.params.get("level", 2)
        request.app.state.brightness_level = level
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
