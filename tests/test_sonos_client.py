"""Tests for SonosClient — envelope construction, parsing, security bounds."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from server.integrations.sonos_client import (
    AV_SERVICE,
    RC_SERVICE,
    Speaker,
    SonosClient,
    UnknownSpeaker,
)


SPEAKER = Speaker(
    id="living-room",
    ip="192.168.0.42",
    name="Move 2",
    room="Living Room",
    max_volume=60,
    vol_step=5,
)


TRANSPORT_PLAYING = """<?xml version="1.0"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
 <s:Body>
  <u:GetTransportInfoResponse xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
   <CurrentTransportState>PLAYING</CurrentTransportState>
   <CurrentTransportStatus>OK</CurrentTransportStatus>
   <CurrentSpeed>1</CurrentSpeed>
  </u:GetTransportInfoResponse>
 </s:Body>
</s:Envelope>"""

TRANSPORT_PAUSED = TRANSPORT_PLAYING.replace("PLAYING", "PAUSED_PLAYBACK")

VOLUME_RESPONSE = """<?xml version="1.0"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
 <s:Body>
  <u:GetVolumeResponse xmlns:u="urn:schemas-upnp-org:service:RenderingControl:1">
   <CurrentVolume>25</CurrentVolume>
  </u:GetVolumeResponse>
 </s:Body>
</s:Envelope>"""

POSITION_RESPONSE = """<?xml version="1.0"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
 <s:Body>
  <u:GetPositionInfoResponse xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
   <Track>1</Track>
   <TrackMetaData>&lt;DIDL-Lite xmlns:dc=&quot;http://purl.org/dc/elements/1.1/&quot;&gt;&lt;item&gt;&lt;dc:title&gt;Heart of Glass&lt;/dc:title&gt;&lt;/item&gt;&lt;/DIDL-Lite&gt;</TrackMetaData>
  </u:GetPositionInfoResponse>
 </s:Body>
</s:Envelope>"""

GENERIC_OK = """<?xml version="1.0"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
 <s:Body><u:Empty/></s:Body>
</s:Envelope>"""


def _mock_response(text: str) -> MagicMock:
    r = MagicMock(spec=httpx.Response)
    r.text = text
    r.raise_for_status = MagicMock()
    return r


def test_unknown_speaker_rejected():
    client = SonosClient([SPEAKER])
    with pytest.raises(UnknownSpeaker):
        client.set_volume("not-a-real-id", 20)


def test_volume_clamped_to_max():
    client = SonosClient([SPEAKER])
    with patch.object(client._client, "post", return_value=_mock_response(GENERIC_OK)) as post:
        result = client.set_volume(SPEAKER.id, 200)
    assert result == SPEAKER.max_volume
    # Inspect the SOAP envelope sent — should contain the clamped value.
    body = post.call_args.kwargs["content"].decode()
    assert "<DesiredVolume>60</DesiredVolume>" in body
    assert "<DesiredVolume>200</DesiredVolume>" not in body


def test_volume_clamped_to_zero():
    client = SonosClient([SPEAKER])
    with patch.object(client._client, "post", return_value=_mock_response(GENERIC_OK)) as post:
        result = client.set_volume(SPEAKER.id, -50)
    assert result == 0
    body = post.call_args.kwargs["content"].decode()
    assert "<DesiredVolume>0</DesiredVolume>" in body


def test_get_state_parses_playing_and_track():
    client = SonosClient([SPEAKER])
    responses = iter([
        _mock_response(TRANSPORT_PLAYING),
        _mock_response(VOLUME_RESPONSE),
        _mock_response(POSITION_RESPONSE),
    ])
    with patch.object(client._client, "post", side_effect=lambda *a, **k: next(responses)):
        state = client.get_state(SPEAKER.id)
    assert state.is_playing is True
    assert state.volume == 25
    assert state.track_title == "Heart of Glass"


def test_get_state_paused():
    client = SonosClient([SPEAKER])
    responses = iter([
        _mock_response(TRANSPORT_PAUSED),
        _mock_response(VOLUME_RESPONSE),
        _mock_response(POSITION_RESPONSE),
    ])
    with patch.object(client._client, "post", side_effect=lambda *a, **k: next(responses)):
        state = client.get_state(SPEAKER.id)
    assert state.is_playing is False


def test_play_pause_envelope_when_paused_sends_play():
    client = SonosClient([SPEAKER])
    # First three calls satisfy get_state, fourth is the Play action.
    responses = iter([
        _mock_response(TRANSPORT_PAUSED),
        _mock_response(VOLUME_RESPONSE),
        _mock_response(POSITION_RESPONSE),
        _mock_response(GENERIC_OK),
    ])
    with patch.object(client._client, "post", side_effect=lambda *a, **k: next(responses)) as post:
        client.play_pause(SPEAKER.id)
    # Last call is the action — verify Play envelope + SOAPAction header.
    final = post.call_args_list[-1]
    body = final.kwargs["content"].decode()
    assert "<u:Play " in body
    assert "<Speed>1</Speed>" in body
    assert final.kwargs["headers"]["SOAPAction"] == f'"{AV_SERVICE}#Play"'


def test_play_pause_envelope_when_playing_sends_pause():
    client = SonosClient([SPEAKER])
    responses = iter([
        _mock_response(TRANSPORT_PLAYING),
        _mock_response(VOLUME_RESPONSE),
        _mock_response(POSITION_RESPONSE),
        _mock_response(GENERIC_OK),
    ])
    with patch.object(client._client, "post", side_effect=lambda *a, **k: next(responses)) as post:
        client.play_pause(SPEAKER.id)
    final = post.call_args_list[-1]
    body = final.kwargs["content"].decode()
    assert "<u:Pause " in body
    assert "<Speed>" not in body


def test_next_and_previous_envelopes():
    client = SonosClient([SPEAKER])
    with patch.object(client._client, "post", return_value=_mock_response(GENERIC_OK)) as post:
        client.next(SPEAKER.id)
    body = post.call_args.kwargs["content"].decode()
    assert "<u:Next " in body
    assert post.call_args.kwargs["headers"]["SOAPAction"] == f'"{AV_SERVICE}#Next"'

    with patch.object(client._client, "post", return_value=_mock_response(GENERIC_OK)) as post:
        client.previous(SPEAKER.id)
    body = post.call_args.kwargs["content"].decode()
    assert "<u:Previous " in body


def test_set_volume_soap_action_header():
    client = SonosClient([SPEAKER])
    with patch.object(client._client, "post", return_value=_mock_response(GENERIC_OK)) as post:
        client.set_volume(SPEAKER.id, 30)
    assert post.call_args.kwargs["headers"]["SOAPAction"] == f'"{RC_SERVICE}#SetVolume"'


def test_xxe_payload_does_not_expand():
    """A response with an external entity must not be expanded or crash the client."""
    malicious = """<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
 <s:Body>
  <u:GetTransportInfoResponse xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
   <CurrentTransportState>&xxe;</CurrentTransportState>
  </u:GetTransportInfoResponse>
 </s:Body>
</s:Envelope>"""
    client = SonosClient([SPEAKER])
    responses = iter([
        _mock_response(malicious),
        _mock_response(VOLUME_RESPONSE),
        _mock_response(POSITION_RESPONSE),
    ])
    with patch.object(client._client, "post", side_effect=lambda *a, **k: next(responses)):
        # Either defusedxml raises (treated as parse failure -> STOPPED default)
        # or the entity is left unresolved. Either way: must not read /etc/passwd
        # and must not crash.
        try:
            state = client.get_state(SPEAKER.id)
        except Exception as e:
            # defusedxml may raise EntitiesForbidden — that's an acceptable outcome.
            assert "Entit" in type(e).__name__ or "forbidden" in str(e).lower()
            return
    assert "root:" not in state.track_title
    # If parsing failed silently, transport defaults to STOPPED (not playing).
    assert state.is_playing is False


def test_billion_laughs_payload_does_not_expand():
    bomb = """<?xml version="1.0"?>
<!DOCTYPE lolz [
  <!ENTITY lol "lol">
  <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
  <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
]>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
 <s:Body>
  <u:GetTransportInfoResponse xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
   <CurrentTransportState>&lol3;</CurrentTransportState>
  </u:GetTransportInfoResponse>
 </s:Body>
</s:Envelope>"""
    client = SonosClient([SPEAKER])
    responses = iter([
        _mock_response(bomb),
        _mock_response(VOLUME_RESPONSE),
        _mock_response(POSITION_RESPONSE),
    ])
    with patch.object(client._client, "post", side_effect=lambda *a, **k: next(responses)):
        try:
            state = client.get_state(SPEAKER.id)
        except Exception as e:
            assert "Entit" in type(e).__name__ or "forbidden" in str(e).lower()
            return
    # If it didn't raise, state is parsed with the entity unexpanded — fine.
    assert state.is_playing is False


def test_vol_up_and_down_use_step():
    client = SonosClient([SPEAKER])
    # vol_up: get_state returns 25, +step(5) -> 30
    responses = iter([
        _mock_response(TRANSPORT_PAUSED),
        _mock_response(VOLUME_RESPONSE),
        _mock_response(POSITION_RESPONSE),
        _mock_response(GENERIC_OK),
    ])
    with patch.object(client._client, "post", side_effect=lambda *a, **k: next(responses)) as post:
        result = client.vol_up(SPEAKER.id)
    assert result == 30
    body = post.call_args_list[-1].kwargs["content"].decode()
    assert "<DesiredVolume>30</DesiredVolume>" in body
