# -*- coding: utf-8 -*-
"""Configuration handling for livestream-to-icecast.

The project expects a TOML file (default ``config.toml``) with the following
structure:

```toml
platform = "twitch"                # or "youtube"
channel_url = "https://www.twitch.tv/your_channel"
poll_interval = 30                 # seconds between live‑status checks
azuracast_api_key = "your_bearer_token_here"   # Bearer token for AzuraCast API (optional)

[icecast]
host = "localhost"
port = 8000
mount = "/live.mp3"
source_user = "source"
source_password = "hackme"

[audio]
codec = "libmp3lame"               # libmp3lame, libvorbis, aac, …
bitrate = "128k"
```

Only the ``icecast`` table is mandatory; ``audio`` falls back to MP3 128 kbps if omitted.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

# Python >=3.11 ships with tomllib in the stdlib. For older versions we fall back
# to ``tomli`` which provides a compatible API.
try:
    import tomllib  # type: ignore
except ModuleNotFoundError:  # pragma: no cover – only on <3.11
    import tomli as tomllib  # type: ignore


@dataclass
class IcecastConfig:
    host: str
    port: int
    mount: str
    source_user: str
    source_password: str


@dataclass
class AudioConfig:
    codec: str = "libmp3lame"
    bitrate: str = "128k"


@dataclass
class AzuraCastConfig:
    api_url: str
    bearer_token: str
    station: str = ""
    mount: str = ""
    # Optionally allow more fields for flexibility


@dataclass
class AppConfig:
    platform: str
    channel_url: str
    poll_interval: int
    icecast: IcecastConfig
    audio: AudioConfig
    azuracast: AzuraCastConfig | None = None
    azuracast_api_key: str = ""


def load_config(path: Path) -> AppConfig:
    """Load and validate a TOML configuration file.

    Parameters
    ----------
    path:
        Path to the ``.toml`` file.
    Returns
    -------
    AppConfig
        A fully‑populated configuration object.
    Raises
    ------
    FileNotFoundError
        If ``path`` does not exist.
    ValueError
        If required keys are missing or have the wrong type.
    """
    if not path.is_file():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("rb") as f:
        data = tomllib.load(f)

    # -----------------------------------------------------------------
    # Basic validation – we keep it simple but explicit.
    # -----------------------------------------------------------------
    required_root_keys = {"platform", "channel_url", "poll_interval", "icecast"}
    missing = required_root_keys - set(data.keys())
    if missing:
        raise ValueError(f"Missing required top‑level config keys: {missing}")

    ice_cfg = data["icecast"]
    for key in ("host", "port", "mount", "source_user", "source_password"):
        if key not in ice_cfg:
            raise ValueError(f"Icecast configuration missing required key: {key}")

    audio_cfg = data.get("audio", {})

    azuracast_cfg = data.get("azuracast")
    azuracast = None
    if azuracast_cfg:
        for key in ("api_url", "bearer_token"):
            if key not in azuracast_cfg:
                raise ValueError(f"Azuracast configuration missing required key: {key}")
        azuracast = AzuraCastConfig(
            api_url=azuracast_cfg["api_url"],
            bearer_token=azuracast_cfg["bearer_token"],
            station=azuracast_cfg.get("station", ""),
            mount=azuracast_cfg.get("mount", ""),
        )

    return AppConfig(
        platform=data["platform"],
        channel_url=data["channel_url"],
        poll_interval=int(data.get("poll_interval", 30)),
        icecast=IcecastConfig(
            host=ice_cfg["host"],
            port=int(ice_cfg["port"]),
            mount=str(ice_cfg["mount"]).lstrip("/"),
            source_user=ice_cfg["source_user"],
            source_password=ice_cfg["source_password"],
        ),
        audio=AudioConfig(
            codec=audio_cfg.get("codec", "libmp3lame"),
            bitrate=audio_cfg.get("bitrate", "128k"),
        ),
        azuracast=azuracast,
    )
