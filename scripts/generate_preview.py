"""Generate a sample dashboard preview image for the README.

Renders through the real engine so the preview always matches what the Kindle
sees (fonts, power button, brightness stepper, layout), then rotates back to
landscape for display in the README.
"""

import io
import sys

sys.path.insert(0, ".")

from PIL import Image

from server.config import ScreenConfig
from server.renderer.engine import RenderEngine

departures = [
    {"minutes": 1, "destination": "High Barnet", "direction": "Northbound"},
    {"minutes": 4, "destination": "Morden", "direction": "Southbound"},
    {"minutes": 7, "destination": "Edgware", "direction": "Northbound"},
    {"minutes": 11, "destination": "Morden via Bank", "direction": "Southbound"},
    {"minutes": 14, "destination": "High Barnet", "direction": "Northbound"},
]

tfl_statuses = [
    {"name": "Blue Line", "status_text": "Good Service", "severity": 10},
    {"name": "Northern", "status_text": "Minor Delays", "severity": 6},
    {"name": "Green Line", "status_text": "Good Service", "severity": 10},
]

lights = [
    {"id": "1", "name": "Floor Lamp", "is_on": True, "room": "Living Room"},
    {"id": "2", "name": "Desk Light", "is_on": False, "room": "Living Room"},
    {"id": "3", "name": "Hallway", "is_on": False, "room": "Hallway"},
    {"id": "4", "name": "Bedroom", "is_on": True, "room": "Bedroom"},
]

weather = {
    "temperature": 14,
    "high": 18,
    "low": 7,
    "rain_chance": 35,
    "condition_code": 2,
    "condition_text": "Partly Cloudy",
}

sonos = {
    "speaker_id": "living-room",
    "name": "Move 2",
    "room": "Living Room",
    "is_playing": True,
    "volume": 32,
    "track_title": "Wellerman — Nathan Evans",
}

engine = RenderEngine(ScreenConfig(width=1024, height=758))
png_bytes, _ = engine.render_dashboard(
    lights=lights,
    tfl_statuses=tfl_statuses,
    departures=departures,
    current_time="08:15",
    current_date="Tue 01 Apr",
    weather=weather,
    battery_pct=72,
    station_name="King's Cross St Pancras",
    sonos=sonos,
    brightness_level=2,
)

# The engine rotates the layout 90° clockwise for the portrait framebuffer;
# rotate it back so the README shows the familiar landscape composition.
img = Image.open(io.BytesIO(png_bytes)).rotate(90, expand=True)
img.save("preview.png")
print("Saved preview.png")
