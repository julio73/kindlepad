"""Minimal Sonos SOAP client.

Speaks only the AVTransport + RenderingControl actions we need: Play, Pause,
Next, Previous, GetTransportInfo, GetVolume, SetVolume, GetPositionInfo.

Security choices:
- Speakers locked at startup via an allowlist (id -> ip). Methods accept a
  speaker_id, never a raw IP.
- Volume bounded to [0, max_volume] inside the client, even if the caller
  forgets.
- Responses parsed with defusedxml (no XXE, no billion-laughs).
- Tight HTTP timeouts so a dead speaker can't hang the dashboard.
- Poll-only — no UPnP event subscription, no inbound listener.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional

import httpx
from defusedxml import ElementTree as ET

logger = logging.getLogger(__name__)

AV_SERVICE = "urn:schemas-upnp-org:service:AVTransport:1"
RC_SERVICE = "urn:schemas-upnp-org:service:RenderingControl:1"
AV_PATH = "/MediaRenderer/AVTransport/Control"
RC_PATH = "/MediaRenderer/RenderingControl/Control"

SOAP_ENVELOPE = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
    's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
    '<s:Body><u:{action} xmlns:u="{service}">{body}</u:{action}></s:Body>'
    "</s:Envelope>"
)

CONNECT_TIMEOUT = 2.0
READ_TIMEOUT = 3.0
CACHE_TTL = 5.0


@dataclass
class Speaker:
    id: str
    ip: str
    name: str
    room: str
    max_volume: int
    vol_step: int


@dataclass
class SonosState:
    speaker_id: str
    is_playing: bool
    volume: int
    track_title: str


class SonosError(Exception):
    pass


class UnknownSpeaker(SonosError):
    pass


class SonosClient:
    def __init__(self, speakers: list[Speaker]):
        self._speakers: dict[str, Speaker] = {s.id: s for s in speakers}
        self._cache: dict[str, tuple[float, SonosState]] = {}
        self._client = httpx.Client(
            timeout=httpx.Timeout(READ_TIMEOUT, connect=CONNECT_TIMEOUT),
        )
        # False until the first successful state fetch; flipped to False when a
        # fetch fails so callers can mark the rendered state as stale.
        self.last_ok: bool = False
        # Wall-clock time of the last successful fetch, for "offline since"
        # markers. None until the first success.
        self.last_ok_at: Optional[float] = None

    def close(self) -> None:
        self._client.close()

    def speakers(self) -> list[Speaker]:
        return list(self._speakers.values())

    def _speaker(self, speaker_id: str) -> Speaker:
        sp = self._speakers.get(speaker_id)
        if sp is None:
            raise UnknownSpeaker(f"speaker_id not in allowlist: {speaker_id!r}")
        return sp

    def _invalidate(self, speaker_id: str) -> None:
        self._cache.pop(speaker_id, None)

    def _soap(
        self,
        speaker_id: str,
        path: str,
        service: str,
        action: str,
        body: str,
    ) -> str:
        sp = self._speaker(speaker_id)
        envelope = SOAP_ENVELOPE.format(action=action, service=service, body=body)
        url = f"http://{sp.ip}:1400{path}"
        headers = {
            "Content-Type": 'text/xml; charset="utf-8"',
            "SOAPAction": f'"{service}#{action}"',
        }
        resp = self._client.post(url, content=envelope.encode("utf-8"), headers=headers)
        resp.raise_for_status()
        return resp.text

    def _extract(self, xml_text: str, tag: str) -> Optional[str]:
        """Return the text of the first element with local-name == tag.

        defusedxml prevents XXE / entity expansion. We walk the tree rather
        than using XPath to avoid namespace gymnastics.
        """
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return None
        for el in root.iter():
            local = el.tag.rsplit("}", 1)[-1]
            if local == tag:
                return el.text or ""
        return None

    def get_state(self, speaker_id: str) -> SonosState:
        cached = self._cache.get(speaker_id)
        now = time.monotonic()
        if cached and (now - cached[0]) < CACHE_TTL:
            return cached[1]

        sp = self._speaker(speaker_id)
        body = "<InstanceID>0</InstanceID>"
        try:
            ti = self._soap(speaker_id, AV_PATH, AV_SERVICE, "GetTransportInfo", body)

            vol_body = "<InstanceID>0</InstanceID><Channel>Master</Channel>"
            vr = self._soap(speaker_id, RC_PATH, RC_SERVICE, "GetVolume", vol_body)

            pi = self._soap(speaker_id, AV_PATH, AV_SERVICE, "GetPositionInfo", body)
        except Exception:
            self.last_ok = False
            raise

        transport = self._extract(ti, "CurrentTransportState") or "STOPPED"
        is_playing = transport == "PLAYING"
        try:
            volume = int(self._extract(vr, "CurrentVolume") or "0")
        except ValueError:
            volume = 0
        volume = max(0, min(volume, sp.max_volume))

        # TrackMetaData is escaped DIDL-Lite. The outer parser already decoded
        # one level of entities when extracting the text node — feed it
        # directly to the inner parser (no extra html.unescape, which would
        # corrupt &amp; inside Spotify URI params).
        meta_raw = self._extract(pi, "TrackMetaData") or ""
        title = ""
        creator = ""
        if meta_raw.strip():
            try:
                meta_root = ET.fromstring(meta_raw)
                for el in meta_root.iter():
                    local = el.tag.rsplit("}", 1)[-1]
                    if local == "title" and not title:
                        title = (el.text or "").strip()
                    elif local == "creator" and not creator:
                        creator = (el.text or "").strip()
            except ET.ParseError:
                pass
        if title and creator:
            title = f"{title} — {creator}"

        state = SonosState(
            speaker_id=speaker_id,
            is_playing=is_playing,
            volume=volume,
            track_title=title,
        )
        self._cache[speaker_id] = (now, state)
        self.last_ok = True
        self.last_ok_at = time.time()
        return state

    def play_pause(self, speaker_id: str) -> None:
        try:
            state = self.get_state(speaker_id)
        except (httpx.HTTPError, SonosError):
            state = SonosState(speaker_id, False, 0, "")
        action = "Pause" if state.is_playing else "Play"
        body = "<InstanceID>0</InstanceID>"
        if action == "Play":
            body += "<Speed>1</Speed>"
        self._soap(speaker_id, AV_PATH, AV_SERVICE, action, body)
        self._invalidate(speaker_id)

    def next(self, speaker_id: str) -> None:
        body = "<InstanceID>0</InstanceID>"
        self._soap(speaker_id, AV_PATH, AV_SERVICE, "Next", body)
        self._invalidate(speaker_id)

    def previous(self, speaker_id: str) -> None:
        body = "<InstanceID>0</InstanceID>"
        self._soap(speaker_id, AV_PATH, AV_SERVICE, "Previous", body)
        self._invalidate(speaker_id)

    def set_volume(self, speaker_id: str, volume: int) -> int:
        sp = self._speaker(speaker_id)
        clamped = max(0, min(int(volume), sp.max_volume))
        body = (
            "<InstanceID>0</InstanceID>"
            "<Channel>Master</Channel>"
            f"<DesiredVolume>{clamped}</DesiredVolume>"
        )
        self._soap(speaker_id, RC_PATH, RC_SERVICE, "SetVolume", body)
        self._invalidate(speaker_id)
        return clamped

    def vol_up(self, speaker_id: str) -> int:
        sp = self._speaker(speaker_id)
        state = self.get_state(speaker_id)
        return self.set_volume(speaker_id, state.volume + sp.vol_step)

    def vol_down(self, speaker_id: str) -> int:
        sp = self._speaker(speaker_id)
        state = self.get_state(speaker_id)
        return self.set_volume(speaker_id, state.volume - sp.vol_step)
