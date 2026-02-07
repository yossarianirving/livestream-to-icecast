"""Tests for yt-dlp helper functions."""

import pytest
from unittest.mock import patch, MagicMock
from livestream_to_icecast.yt_dlp_helper import (
    get_m3u8_url,
    is_live,
    get_stream_info,
    check_m3u8_url,
)


def test_get_m3u8_url_success():
    """Test successful URL retrieval."""
    with patch("livestream_to_icecast.yt_dlp_helper._run_yt_dlp") as mock_run:
        mock_run.return_value = "https://example.com/stream.m3u8"
        
        result = get_m3u8_url("https://twitch.tv/channel")
        
        assert result == "https://example.com/stream.m3u8"
        mock_run.assert_called_once()


def test_get_m3u8_url_failure():
    """Test URL retrieval failure returns None."""
    with patch("livestream_to_icecast.yt_dlp_helper._run_yt_dlp") as mock_run:
        mock_run.side_effect = RuntimeError("yt-dlp failed")
        
        result = get_m3u8_url("https://invalid")
        
        assert result is None


def test_is_live_returns_true():
    """Test is_live returns True when stream URL exists."""
    with patch("livestream_to_icecast.yt_dlp_helper.get_m3u8_url") as mock_get:
        mock_get.return_value = "https://example.com/stream.m3u8"
        
        result = is_live("https://twitch.tv/channel")
        
        assert result is True


def test_is_live_returns_false():
    """Test is_live returns False when stream URL doesn't exist."""
    with patch("livestream_to_icecast.yt_dlp_helper.get_m3u8_url") as mock_get:
        mock_get.return_value = None
        
        result = is_live("https://twitch.tv/channel")
        
        assert result is False


def test_is_live_exception_handling():
    """Test is_live catches and handles exceptions gracefully."""
    with patch("livestream_to_icecast.yt_dlp_helper.get_m3u8_url") as mock_get:
        mock_get.side_effect = RuntimeError("Network error")
        
        result = is_live("https://twitch.tv/channel")
        
        assert result is False


def test_get_stream_info_twitch():
    """Test stream info extraction for Twitch."""
    with patch("livestream_to_icecast.yt_dlp_helper._run_yt_dlp") as mock_run:
        mock_run.return_value = """
{
  "description": "Twitch Stream Title",
  "formats": [
    {"protocol": "m3u8", "url": "https://example.com/twitch.m3u8"}
  ]
}
"""
        result = get_stream_info("https://twitch.tv/channel", "twitch")
        
        assert result is not None
        assert result.title == "Twitch Stream Title"
        assert result.m3u8_url == "https://example.com/twitch.m3u8"


def test_get_stream_info_youtube():
    """Test stream info extraction for YouTube."""
    with patch("livestream_to_icecast.yt_dlp_helper._run_yt_dlp") as mock_run:
        mock_run.return_value = """
{
  "title": "YouTube Stream Title",
  "formats": [
    {"protocol": "m3u8", "url": "https://example.com/youtube.m3u8"}
  ]
}
"""
        result = get_stream_info("https://youtube.com/channel", "youtube")
        
        assert result is not None
        assert result.title == "YouTube Stream Title"


def test_get_stream_info_fallback_url():
    """Test fallback to info.url when no formats available."""
    with patch("livestream_to_icecast.yt_dlp_helper._run_yt_dlp") as mock_run:
        mock_run.return_value = """
{
  "title": "Stream",
  "url": "https://example.com/fallback.m3u8"
}
"""
        result = get_stream_info("https://example.com", "youtube")
        
        assert result is not None
        assert result.m3u8_url == "https://example.com/fallback.m3u8"


def test_get_stream_info_failure():
    """Test handling of yt-dlp failures."""
    with patch("livestream_to_icecast.yt_dlp_helper._run_yt_dlp") as mock_run:
        mock_run.side_effect = RuntimeError("yt-dlp failed")
        
        result = get_stream_info("https://example.com", "youtube")
        
        assert result is None


def test_check_m3u8_url_success():
    """Test URL check returns True for valid stream."""
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        result = check_m3u8_url("https://example.com/stream.m3u8")
        
        assert result is True


def test_check_m3u8_url_not_found():
    """Test URL check returns False for 404."""
    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        result = check_m3u8_url("https://example.com/missing.m3u8")
        
        assert result is False


def test_check_m3u8_url_exception():
    """Test URL check handles exceptions gracefully."""
    with patch("requests.get") as mock_get:
        mock_get.side_effect = ConnectionError("Network error")
        
        result = check_m3u8_url("https://example.com/stream.m3u8")
        
        assert result is False
