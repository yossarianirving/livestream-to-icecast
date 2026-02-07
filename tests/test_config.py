"""Tests for configuration loading and validation."""

import pytest
from pathlib import Path

from livestream_to_icecast.config import load_config, AppConfig


def test_load_config_success(tmp_path: Path):
    """Test successful config loading from TOML file."""
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text("""
platform = "twitch"
channel_url = "https://www.twitch.tv/your_channel"
channel_name = "YourChannelName"
poll_interval = 30

[icecast]
host = "localhost"
port = 8000
mount = "/live.mp3"
source_user = "source"
source_password = "hackme"

[audio]
codec = "libmp3lame"
bitrate = "128k"
""")
    cfg = load_config(cfg_file)
    
    assert cfg.platform == "twitch"
    assert cfg.channel_url == "https://www.twitch.tv/your_channel"
    assert cfg.channel_name == "YourChannelName"
    assert cfg.poll_interval == 30
    assert cfg.icecast.host == "localhost"
    assert cfg.icecast.port == 8000
    assert cfg.audio.codec == "libmp3lame"


def test_load_config_missing_file(tmp_path: Path):
    """Test that FileNotFoundError is raised for missing files."""
    non_existent = tmp_path / "nonexistent.toml"
    with pytest.raises(FileNotFoundError):
        load_config(non_existent)


def test_load_config_missing_required_keys(tmp_path: Path):
    """Test validation catches missing required keys."""
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text("""
platform = "twitch"
channel_url = "https://example.com"
""")
    with pytest.raises(ValueError, match="Missing required"):
        load_config(cfg_file)


def test_load_config_invalid_platform(tmp_path: Path):
    """Test validation rejects invalid platform values."""
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text("""
platform = "invalid"
channel_url = "https://example.com"
channel_name = "Test"
poll_interval = 30

[icecast]
host = "localhost"
port = 8000
mount = "/live.mp3"
source_user = "src"
source_password = "pwd"
""")
    with pytest.raises(ValueError, match="Invalid platform"):
        load_config(cfg_file)


def test_load_config_negative_poll_interval(tmp_path: Path):
    """Test validation rejects non-positive poll intervals."""
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text("""
platform = "twitch"
channel_url = "https://example.com"
channel_name = "Test"
poll_interval = -5

[icecast]
host = "localhost"
port = 8000
mount = "/live.mp3"
source_user = "src"
source_password = "pwd"
""")
    with pytest.raises(ValueError, match="must be positive"):
        load_config(cfg_file)


def test_load_config_empty_channel_url(tmp_path: Path):
    """Test validation rejects empty channel URL."""
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text("""
platform = "twitch"
channel_url = ""
channel_name = "Test"
poll_interval = 30

[icecast]
host = "localhost"
port = 8000
mount = "/live.mp3"
source_user = "src"
source_password = "pwd"
""")
    with pytest.raises(ValueError, match="cannot be empty"):
        load_config(cfg_file)


def test_load_config_with_azuracast(tmp_path: Path):
    """Test config loading with optional AzuraCast section."""
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text("""
platform = "youtube"
channel_url = "https://www.youtube.com/channel/UCxyz"
channel_name = "YouTubeChannel"
poll_interval = 60

[icecast]
host = "localhost"
port = 8000
mount = "/live.mp3"
source_user = "src"
source_password = "pwd"

[azuracast]
api_url = "https://azuracast.example.com"
bearer_token = "token123"
station = "1"

[audio]
codec = "libvorbis"
bitrate = "192k"
""")
    cfg = load_config(cfg_file)
    
    assert cfg.platform == "youtube"
    assert cfg.azuracast is not None
    assert cfg.azuracast.api_url == "https://azuracast.example.com"
    assert cfg.audio.codec == "libvorbis"


def test_mount_path_stripping(tmp_path: Path):
    """Test mount path leading slash handling."""
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text("""
platform = "twitch"
channel_url = "https://example.com"
channel_name = "Test"
poll_interval = 30

[icecast]
host = "localhost"
port = 8000
mount = "/live.mp3"
source_user = "src"
source_password = "pwd"
""")
    cfg = load_config(cfg_file)
    
    # Mount should have leading slash stripped in config object
    assert cfg.icecast.mount == "live.mp3"


def test_default_audio_config(tmp_path: Path):
    """Test default audio codec and bitrate."""
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text("""
platform = "twitch"
channel_url = "https://example.com"
channel_name = "Test"
poll_interval = 30

[icecast]
host = "localhost"
port = 8000
mount = "/live.mp3"
source_user = "src"
source_password = "pwd"
""")
    cfg = load_config(cfg_file)
    
    assert cfg.audio.codec == "libmp3lame"
    assert cfg.audio.bitrate == "128k"


def test_load_missing_icecast_key(tmp_path: Path):
    """Test validation catches missing icecast keys."""
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text("""
platform = "twitch"
channel_url = "https://example.com"
channel_name = "Test"
poll_interval = 30

[icecast]
host = "localhost"
port = 8000
mount = "/live.mp3"
""")
    with pytest.raises(ValueError, match="missing required key: source_user"):
        load_config(cfg_file)
