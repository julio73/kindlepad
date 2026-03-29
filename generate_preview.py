"""Generate a sample dashboard preview image for the README."""

import sys
sys.path.insert(0, ".")

from PIL import Image, ImageDraw
from collections import OrderedDict

from server.renderer.components import (
    draw_departure_row,
    draw_footer,
    draw_header,
    draw_light_group,
    draw_room_header,
    draw_section_header,
    draw_tfl_row,
    draw_vertical_divider,
    draw_weather,
)
from server.renderer.theme import BG, DIVIDER_X, PADDING, PANEL_GAP, SECTION_GAP

WIDTH, HEIGHT = 1024, 758

# --- Sample data ---
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

station_name = "King's Cross St Pancras"
current_time = "08:15"
current_date = "Tue 01 Apr"
battery_pct = 72

# --- Render ---
img = Image.new("L", (WIDTH, HEIGHT), BG)
draw = ImageDraw.Draw(img)

y = PADDING
y = draw_header(draw, "KindlePad", current_time, current_date, WIDTH, y)
header_bottom = y

left_x = PADDING
left_width = DIVIDER_X - PANEL_GAP - PADDING
right_x = DIVIDER_X + PANEL_GAP
right_width = WIDTH - PADDING - right_x

# Left panel: Transit
ly = header_bottom

header_label = f"NEXT TRAINS \u00b7 {station_name}"
ly = draw_section_header(draw, header_label, left_x, ly)
for dep in departures[:5]:
    ly = draw_departure_row(
        draw,
        minutes=dep["minutes"],
        destination=dep["destination"],
        direction=dep["direction"],
        x=left_x,
        y=ly,
        width=left_width,
    )
ly += SECTION_GAP

ly = draw_section_header(draw, "LINE STATUS", left_x, ly)
for status in tfl_statuses:
    ly = draw_tfl_row(
        draw,
        line_name=status["name"],
        status_text=status["status_text"],
        severity=status["severity"],
        x=left_x,
        y=ly,
        width=left_width,
    )

footer_y = max(ly + SECTION_GAP, HEIGHT - 44)
draw_footer(draw, current_time, left_x, footer_y, left_width, battery_pct=battery_pct)

# Right panel: Lights
ry = header_bottom
ry = draw_section_header(draw, "LIGHTS", right_x, ry)

rooms = OrderedDict()
for light in lights:
    room = light.get("room", "Other")
    rooms.setdefault(room, []).append(light)

for room_name, room_lights in rooms.items():
    ry = draw_room_header(draw, room_name, right_x, ry)
    ry, zones = draw_light_group(draw, room_lights, right_x, ry, right_width)
    ry += SECTION_GAP // 2

weather_y = max(ry + SECTION_GAP, HEIGHT - 110)
draw_weather(draw, weather, right_x, weather_y, right_width)

draw_vertical_divider(draw, DIVIDER_X, header_bottom, HEIGHT - PADDING)

# Save landscape (not rotated) for README
img.save("preview.png")
print("Saved preview.png")
