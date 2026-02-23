"""Unit tests for discovery module"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from radio_ingestion.discovery.radio_browser import RadioBrowserClient, discover_stations


class TestRadioBrowserClient:
    """Test RadioBrowserClient"""

    def test_init(self):
        """Test client initialization"""
        client = RadioBrowserClient("https://api.example.com")
        assert client.api_url == "https://api.example.com"
        assert "User-Agent" in client.session.headers

    @patch("radio_ingestion.discovery.radio_browser.requests.Session.get")
    def test_search_stations_success(self, mock_get):
        """Test successful station search"""
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "name": "Test Station",
                "url_resolved": "https://stream.example.com/test",
                "countrycode": "SOM",
                "language": "somali",
                "tags": "news, talk",
                "stationuuid": "test-uuid-123",
                "votes": 100,
            }
        ]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        client = RadioBrowserClient()
        stations = client.search_stations(country="SOM", limit=10)

        assert len(stations) == 1
        assert stations[0]["name"] == "Test Station"
        mock_get.assert_called_once()

    @patch("radio_ingestion.discovery.radio_browser.requests.Session.get")
    def test_search_stations_error(self, mock_get):
        """Test error handling in station search"""
        mock_get.side_effect = Exception("Network error")

        client = RadioBrowserClient()

        with pytest.raises(Exception):
            client.search_stations(country="SOM")

    def test_parse_station(self):
        """Test station parsing"""
        station_data = {
            "name": "Radio Muqdisho",
            "url_resolved": "https://stream.example.com/radio",
            "countrycode": "som",
            "language": "somali",
            "timezone": "Africa/Mogadishu",
            "bitrate": 128,
            "codec": "mp3",
            "stationuuid": "uuid-123",
            "homepage": "https://radio.example.com",
            "tags": "news, talk, somali",
            "votes": 150,
            "clickcount": 500,
        }

        parsed = RadioBrowserClient().parse_station(station_data)

        assert parsed["name"] == "Radio Muqdisho"
        assert parsed["stream_url"] == "https://stream.example.com/radio"
        assert parsed["country"] == "SOM"
        assert parsed["lang_hint"] == "somali"
        assert parsed["bitrate"] == 128
        assert parsed["codec"] == "mp3"
        assert parsed["station_uuid"] == "uuid-123"
        assert isinstance(parsed["tags"], list)
        assert "news" in parsed["tags"]

    def test_parse_station_no_url(self):
        """Test parsing station without stream URL"""
        station_data = {"name": "Test", "url": "", "url_resolved": None}

        parsed = RadioBrowserClient().parse_station(station_data)
        assert parsed["stream_url"] is None

    @patch("radio_ingestion.discovery.radio_browser.RadioBrowserClient")
    def test_discover_stations(self, mock_client_class):
        """Test discover_stations function"""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.search_stations.return_value = [
            {
                "name": "Radio Test",
                "url_resolved": "https://stream.example.com/test",
                "countrycode": "SOM",
                "language": "somali",
                "tags": "",
                "stationuuid": "test-uuid",
                "votes": 50,
            }
        ]

        stations = discover_stations(api_url="https://api.example.com", country="SOM", limit=5)

        assert len(stations) == 1
        assert stations[0]["name"] == "Radio Test"
        mock_client.search_stations.assert_called_once()


class TestParseStation:
    """Test station parsing edge cases"""

    def test_parse_station_empty_tags(self):
        """Test parsing with empty tags"""
        client = RadioBrowserClient()
        station_data = {"name": "Test", "url_resolved": "https://example.com", "tags": ""}

        parsed = client.parse_station(station_data)
        assert parsed["tags"] == []

    def test_parse_station_missing_fields(self):
        """Test parsing with missing optional fields"""
        client = RadioBrowserClient()
        station_data = {"name": "Minimal Station", "url_resolved": "https://example.com/stream"}

        parsed = client.parse_station(station_data)
        assert parsed["name"] == "Minimal Station"
        assert parsed["country"] is None
        assert parsed["lang_hint"] is None
