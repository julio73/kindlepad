"""Tests for TflClient with mocked HTTP responses."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from server.integrations.tfl_client import TflClient, TrainDeparture


GOOD_SERVICE_RESPONSE = [
    {
        "id": "green-line",
        "name": "Green Line",
        "lineStatuses": [
            {
                "statusSeverity": 10,
                "statusSeverityDescription": "Good Service",
                "reason": None,
            }
        ],
    }
]

DISRUPTED_RESPONSE = [
    {
        "id": "green-line",
        "name": "Green Line",
        "lineStatuses": [
            {
                "statusSeverity": 6,
                "statusSeverityDescription": "Severe Delays",
                "reason": "Signal failure at Green Line",
            }
        ],
    }
]

LINES = [{"id": "green-line", "display_name": "Green Line"}]

NAPTAN_ID = "XXXXXXXXXXX"

ARRIVALS_RESPONSE = [
    {
        "destinationName": "Northtown Underground Station",
        "timeToStation": 120,
        "direction": "outbound",
        "lineName": "Blue Line",
    },
    {
        "destinationName": "Southbury Underground Station",
        "timeToStation": 300,
        "direction": "inbound",
        "lineName": "Blue Line",
    },
]

UNSORTED_ARRIVALS_RESPONSE = [
    {
        "destinationName": "Southbury Underground Station",
        "timeToStation": 300,
        "direction": "inbound",
        "lineName": "Blue Line",
    },
    {
        "destinationName": "Northtown Underground Station",
        "timeToStation": 60,
        "direction": "outbound",
        "lineName": "Blue Line",
    },
    {
        "destinationName": "Westfield Underground Station",
        "timeToStation": 180,
        "direction": "outbound",
        "lineName": "Blue Line",
    },
]


def _mock_response(json_data, status_code=200):
    """Create a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp


class TestParseGoodService:
    def test_parse_good_service(self):
        """Verify LineStatus fields for a good-service response."""
        client = TflClient(lines=LINES)

        with patch("server.integrations.tfl_client.httpx.Client") as MockClient:
            mock_http = MagicMock()
            mock_http.__enter__ = MagicMock(return_value=mock_http)
            mock_http.__exit__ = MagicMock(return_value=False)
            mock_http.get.return_value = _mock_response(GOOD_SERVICE_RESPONSE)
            MockClient.return_value = mock_http

            statuses = client.get_statuses_sync()

        assert len(statuses) == 1
        s = statuses[0]
        assert s.id == "green-line"
        assert s.name == "Green Line"
        assert s.severity == 10
        assert s.status_text == "Good Service"
        assert s.disruption_reason is None


class TestParseDisruption:
    def test_parse_disruption(self):
        """Verify disruption_reason is populated when severity != 10."""
        client = TflClient(lines=LINES)

        with patch("server.integrations.tfl_client.httpx.Client") as MockClient:
            mock_http = MagicMock()
            mock_http.__enter__ = MagicMock(return_value=mock_http)
            mock_http.__exit__ = MagicMock(return_value=False)
            mock_http.get.return_value = _mock_response(DISRUPTED_RESPONSE)
            MockClient.return_value = mock_http

            statuses = client.get_statuses_sync()

        assert len(statuses) == 1
        s = statuses[0]
        assert s.severity == 6
        assert s.status_text == "Severe Delays"
        assert s.disruption_reason == "Signal failure at Green Line"


class TestCaching:
    def test_caching(self):
        """Two rapid calls should result in only one HTTP request."""
        client = TflClient(lines=LINES, refresh_interval=120)

        with patch("server.integrations.tfl_client.httpx.Client") as MockClient:
            mock_http = MagicMock()
            mock_http.__enter__ = MagicMock(return_value=mock_http)
            mock_http.__exit__ = MagicMock(return_value=False)
            mock_http.get.return_value = _mock_response(GOOD_SERVICE_RESPONSE)
            MockClient.return_value = mock_http

            first = client.get_statuses_sync()
            second = client.get_statuses_sync()

        assert first == second
        # httpx.Client() should only have been constructed once
        MockClient.assert_called_once()


class TestNetworkError:
    def test_network_error(self):
        """A connection error returns an empty list without crashing."""
        client = TflClient(lines=LINES)

        with patch("server.integrations.tfl_client.httpx.Client") as MockClient:
            mock_http = MagicMock()
            mock_http.__enter__ = MagicMock(return_value=mock_http)
            mock_http.__exit__ = MagicMock(return_value=False)
            mock_http.get.side_effect = httpx.ConnectError("Connection refused")
            MockClient.return_value = mock_http

            statuses = client.get_statuses_sync()

        assert statuses == []


class TestParseDepartures:
    def test_parse_departures(self):
        """Mock arrivals API response and verify TrainDeparture parsing."""
        client = TflClient(lines=LINES)

        with patch("server.integrations.tfl_client.httpx.Client") as MockClient:
            mock_http = MagicMock()
            mock_http.__enter__ = MagicMock(return_value=mock_http)
            mock_http.__exit__ = MagicMock(return_value=False)
            mock_http.get.return_value = _mock_response(ARRIVALS_RESPONSE)
            MockClient.return_value = mock_http

            departures = client.get_departures_sync(NAPTAN_ID)

        assert len(departures) == 2

        d0 = departures[0]
        assert isinstance(d0, TrainDeparture)
        assert d0.destination == "Northtown"
        assert d0.minutes == 2  # 120 seconds // 60
        assert d0.direction == "outbound"
        assert d0.line_name == "Blue Line"

        d1 = departures[1]
        assert d1.destination == "Southbury"
        assert d1.minutes == 5  # 300 seconds // 60
        assert d1.direction == "inbound"


class TestDeparturesSorted:
    def test_departures_sorted(self):
        """Results should be sorted by minutes ascending."""
        client = TflClient(lines=LINES)

        with patch("server.integrations.tfl_client.httpx.Client") as MockClient:
            mock_http = MagicMock()
            mock_http.__enter__ = MagicMock(return_value=mock_http)
            mock_http.__exit__ = MagicMock(return_value=False)
            mock_http.get.return_value = _mock_response(UNSORTED_ARRIVALS_RESPONSE)
            MockClient.return_value = mock_http

            departures = client.get_departures_sync(NAPTAN_ID)

        minutes_list = [d.minutes for d in departures]
        assert minutes_list == sorted(minutes_list)
        # First should be 1 min (60s // 60), then 3 min (180s // 60), then 5 min (300s // 60)
        assert minutes_list == [1, 3, 5]


class TestDeparturesCaching:
    def test_departures_caching(self):
        """Two rapid calls should result in only one HTTP request."""
        client = TflClient(lines=LINES)

        with patch("server.integrations.tfl_client.httpx.Client") as MockClient:
            mock_http = MagicMock()
            mock_http.__enter__ = MagicMock(return_value=mock_http)
            mock_http.__exit__ = MagicMock(return_value=False)
            mock_http.get.return_value = _mock_response(ARRIVALS_RESPONSE)
            MockClient.return_value = mock_http

            first = client.get_departures_sync(NAPTAN_ID)
            second = client.get_departures_sync(NAPTAN_ID)

        assert first == second
        # httpx.Client() should only have been constructed once
        MockClient.assert_called_once()
