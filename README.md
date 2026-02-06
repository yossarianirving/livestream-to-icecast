# livestream-to-icecast

CLI that forwards Twitch or YouTube live audio streams to an Icecast server using `yt-dlp` and `ffmpeg`.

## Table of Contents
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Development](#development)

## Installation

```sh
# Clone the repository
git clone https://github.com/yourusername/livestream-to-icecast.git
cd livestream-to-icecast

# Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate   # on Windows: .venv\Scripts\activate

# Install the package with development extras
pip install -e .[dev]       # or, if you have uv installed:
uv sync --all-extras
```

### Prerequisites

- Python ≥ 3.10
- `ffmpeg` available on your system PATH
- `yt-dlp` will be installed as a dependency (or can be installed manually)

## Configuration

The application expects a TOML configuration file (`config.toml`). An example is provided in `config.example.toml`.

```toml
platform = "twitch"               # or "youtube"
channel_url = "https://www.twitch.tv/your_channel"
channel_name = "YourChannelName"

poll_interval = 30                # seconds between live‑status checks

[icecast]
host = "localhost"
port = 8000
mount = "/live.mp3"
source_user = "source"
source_password = "hackme"

# Optional AzuraCast integration
azuracast_api_key = "your_azuracast_api_key_here"

[azuracast]
api_url = "https://azuracast.example.com"
bearer_token = "your_azuracast_api_bearer_token"
station = "1"

[audio]
codec = "libmp3lame"   # libmp3lame, libvorbis, aac, …
bitrate = "256k"
```

Only the `[icecast]` table is mandatory; other sections are optional.

## Usage

```sh
livestream-to-icecast --config config.toml
```

The CLI will:

1. Load the configuration.
2. Poll the specified Twitch/YouTube channel for live status.
3. When the stream goes live, retrieve an HLS (`m3u8`) URL with `yt‑dlp`.
4. Pipe the audio to `ffmpeg` which streams it to the Icecast server.
5. Optionally update AzuraCast metadata while the stream is active.

Press `Ctrl+C` to stop gracefully.
