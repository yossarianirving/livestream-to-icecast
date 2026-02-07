"""Tests for AzuraCast helper functions."""

import pytest
from unittest.mock import patch, MagicMock
from livestream_to_icecast.azuracast_helper import (
    get_current_azuracast_metadata,
    update_azuracast_metadata,
)
from livestream_to_icecast.config import AzuraCastConfig


def create_mock_config():
    """Create a test AzuraCastConfig instance."""
    return AzuraCastConfig(
        api_url="https://azuracast.example.com",
        bearer_token="test-token",
        station="1",
    )


def test_get_metadata_success():
    """Test successful metadata retrieval."""
    cfg = create_mock_config()
    
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "now_playing": {"song": {"title": "Song Title", "artist": "Artist Name"}}
        }
        mock_get.return_value = mock_response
        
        result = get_current_azuracast_metadata(cfg)
        
        assert result is not None
        assert result["title"] == "Song Title"
        assert result["artist"] == "Artist Name"


def test_get_metadata_empty_song_info():
    """Test handling of empty song info."""
    cfg = create_mock_config()
    
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"now_playing": {}}
        mock_get.return_value = mock_response
        
        result = get_current_azuracast_metadata(cfg)
        
        assert result is not None
        assert result["title"] == ""
        assert result["artist"] == ""


def test_get_metadata_missing_config():
    """Test handling of missing config."""
    with patch("requests.get") as mock_get:
        result = get_current_azuracast_metadata(None)
        
        assert result is None
        mock_get.assert_not_called()


def test_get_metadata_api_error():
    """Test handling of API error response."""
    cfg = create_mock_config()
    
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response
        
        result = get_current_azuracast_metadata(cfg)
        
        assert result is None


def test_update_metadata_success():
    """Test successful metadata update."""
    cfg = create_mock_config()
    
    with patch("requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        result = update_azuracast_metadata(cfg, title="New Title", artist="New Artist")
        
        assert result is True


def test_update_metadata_api_error():
    """Test handling of API error on update."""
    cfg = create_mock_config()
    
    with patch("requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_post.return_value = mock_response
        
        result = update_azuracast_metadata(cfg, title="New Title", artist="Artist")
        
        assert result is False


def test_update_metadata_missing_config():
    """Test handling of missing config on update."""
    with patch("requests.post") as mock_post:
        result = update_azuracast_metadata(None, "Title", "Artist")
        
        assert result is False
        mock_post.assert_not_called()


def test_update_metadata_offline_status():
    """Test updating to OFFLINE status."""
    cfg = create_mock_config()
    
    with patch("requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        result = update_azuracast_metadata(cfg, title="OFFLINE", artist="OFFLINE")
        
        assert result is True
