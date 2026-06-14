# KindlePad

I've got a Kindle Paperwhite 3 from 2014, turned into a wall-mounted smart home panel. The server runs on a Samsung Galaxy Note 9 from 2018, otherwise mostly a dust collector. I welcomed them to their second life.

![Dashboard preview](preview.png)
*What's displayed on the Kindle*

Built over a weekend with [Claude Code](https://claude.ai/code).

## What it does

My Kindle now shows me train departures and line status from TfL, lets me tap to toggle IKEA lights (via a Dirigera hub), control my Sonos speaker, and gives me weather at a glance. Handy prep device when heading out.

The whole thing runs locally, so no cloud (except cumulonimbus), also no accounts (anon everywhere), and no subscriptions (just daemons on the run).

## How it works

A Python server renders a grayscale image, sends it to the Kindle over HTTP. The Kindle refreshes every couple of minutes and after each tap. Taps get sent back to the server, which figures out what was pressed and does the thing (toggle a light, mostly).

The Kindle is ~~jailbroken~~ free-ranged, with FBInk for the display and a shell script running the fetch/display/touch loop. The Note 9 runs Termux with Python and uvicorn.

## The pieces

| | |
|---|---|
| Kindle PW3 | Display and touch input |
| Galaxy Note 9 | Runs the server in Termux |
| IKEA Dirigera | Controls the lights locally |
| Sonos Move 2 | Music control over local SOAP |
| TfL API | Train times and service status |
| Open-Meteo | Weather, but it's always raining |
| Pillow | Draws the dashboard server-side |
| FBInk | Pushes images to the Kindle screen |

## Setup

**Server (Note 9 / Termux, or any machine with Python 3.9+):**

```sh
git clone <this repo> && cd kindlepad
pip install -r requirements.txt        # or: pip install -e .
cp config.example.yaml config.yaml     # then edit: token, hub IP, lines, speakers
python -m server                        # serves on config.server host/port (default 0.0.0.0:8070)
```

The server refuses to start without a `config.yaml`, and logs a loud warning if no
`server.token` is set (which disables auth — set one for anything beyond localhost).

**Kindle (jailbroken, with FBInk + SSH):**

```sh
# copy the kindle/ directory to /mnt/us/ first, then on the Kindle:
ssh root@kindle "sh /mnt/us/kindle/install.sh"
vi /mnt/us/kindlepad/config.sh          # set SERVER_URL and TOKEN
/etc/init.d/kindlepad start
```

**Fonts:** the bundled [Barlow Condensed](https://fonts.google.com/specimen/Barlow+Condensed)
(SIL OFL, in `fonts/`) is used by default so it looks consistent on Termux. The original
design used DIN Condensed + Avenir Next, which are proprietary and not redistributable —
they're used automatically if present on the host (e.g. macOS).

## But why?

Well, I got a Dirigera hub and wanted to control house lights without pulling out my phone every time. The Kindle and the Note 9 were both just sitting around. Seemed like a waste to let them rot away. The train times and weather ended up being the most useful bit — quick check on the way out the door.

I look forward to doing another project with my current newer daily drivers.

## License

MIT — it worked for me, maybe it will for you and your devices. See [LICENSE](LICENSE).
The bundled Barlow Condensed font is under the SIL Open Font License (`fonts/OFL.txt`).
