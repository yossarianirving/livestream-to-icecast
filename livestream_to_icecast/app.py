# -*- coding: utf-8 -*-
"""Entry‑point for the ``livestream-to-icecast`` CLI.

The script follows the workflow described in the original request:

1. Load configuration from a TOML file (default ``config.toml``).
2. Periodically check whether the configured Twitch/YouTube channel is live using
   :func:`yt_dlp_helper.is_live`.
3. When the channel goes live, obtain an HLS (m3u8) audio URL via
   :func:`yt_dlp_helper.get_m3u8_url`.
4. Launch ``ffmpeg`` to pull the audio and push it to Icecast.
5. If the stream stops or ``ffmpeg`` exits unexpectedly we retry a few times with
   the same URL, then fetch a fresh one; if that also fails we wait for the next
   live event.

All heavy lifting (network calls) is delegated to external binaries – ``yt‑dlp``
and ``ffmpeg`` – which must be present on the system's ``PATH``.  The script only
handles orchestration, logging and retry logic.
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
import time
from pathlib import Path

from .config import AppConfig, load_config
from .yt_dlp_helper import get_m3u8_url, is_live

log = logging.getLogger("livestream-to-icecast")


def _build_icecast_url(cfg: AppConfig) -> str:
    """Construct the Icecast destination URL for ffmpeg.

    ``ffmpeg`` expects a URL of the form::

        icecast://user:password@host:port/mount
    """
    ice = cfg.icecast
    mount = ice.mount if ice.mount.startswith("/") else f"/{ice.mount}"
    return f"icecast://{ice.source_user}:{ice.source_password}@{ice.host}:{ice.port}{mount}"


def _start_ffmpeg(m3u8_url: str, cfg: AppConfig) -> subprocess.Popen:
    """Spawn ``ffmpeg`` to read *m3u8_url* and push audio to Icecast.

    Returns the :class:`subprocess.Popen` object so the caller can monitor its exit
    status.  The command is deliberately quiet – only errors are printed to stderr.
    """
    out_url = _build_icecast_url(cfg)
    audio_cfg = cfg.audio

    # Choose a container format that matches the codec; mp3 works with libmp3lame,
    # ogg works with libvorbis, etc.
    fmt = "mp3" if audio_cfg.codec == "libmp3lame" else "ogg"

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        m3u8_url,
        "-vn",
        "-c:a",
        audio_cfg.codec,
        "-b:a",
        audio_cfg.bitrate,
        "-f",
        fmt,
        out_url,
    ]

    log.info("Starting ffmpeg: %s", " ".join(cmd))
    # ``stdout`` is discarded; we only keep stderr for diagnostics.
    return subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )


def _monitor_stream(cfg: AppConfig) -> None:
    """Main loop that watches the channel and keeps ffmpeg alive.

    The algorithm mirrors the specification:

    * Poll for live status every ``cfg.poll_interval`` seconds.
    * When live, fetch an m3u8 URL and start ffmpeg.
    * If ffmpeg exits, retry a few times with the same URL; after exhausting those
      attempts request a fresh URL.  If we cannot obtain a new working URL we wait for
      the next live event.
    """
    max_retries_per_url = 3

    while True:
        # -----------------------------------------------------------------
        # Wait until the channel is broadcasting.
        # -----------------------------------------------------------------
        if not is_live(cfg.channel_url):
            log.info(
                "Channel not live – checking again in %s seconds", cfg.poll_interval
            )
            time.sleep(cfg.poll_interval)
            continue

        # Channel is live; obtain an m3u8 URL.
        current_m3u8 = get_m3u8_url(cfg.channel_url)
        if not current_m3u8:
            log.error("Failed to retrieve m3u8 URL while channel appears live")
            time.sleep(cfg.poll_interval)
            continue

        retries_left = max_retries_per_url

        # -----------------------------------------------------------------
        # Inner loop: keep ffmpeg running for the *current* stream.
        # -----------------------------------------------------------------
        while True:
            proc = _start_ffmpeg(current_m3u8, cfg)

            # Poll ffmpeg every few seconds; if it exits we break to retry logic.
            while True:
                retcode = proc.poll()
                if retcode is not None:  # Process terminated.
                    err_msg = proc.stderr.read().strip() if proc.stderr else ""
                    log.warning(
                        "ffmpeg exited (code %s). Stderr: %s",
                        retcode,
                        err_msg or "<empty>",
                    )
                    break
                time.sleep(5)

            # -----------------------------------------------------------------
            # Retry the same URL a limited number of times.
            # -----------------------------------------------------------------
            retries_left -= 1
            if retries_left > 0:
                log.info("Retrying current stream – %s attempts left", retries_left)
                time.sleep(2)  # short back‑off before restarting ffmpeg
                continue

            # Exhausted retries for this URL – fetch a fresh one.
            new_m3u8 = get_m3u8_url(cfg.channel_url)
            if not new_m3u8 or new_m3u8 == current_m3u8:
                log.error(
                    "Unable to obtain a new working m3u8 URL. Waiting for channel to go offline"
                )
                break  # exit inner loop; outer will re‑check live status.

            log.info("Obtained fresh m3u8 URL – resetting retry counter")
            current_m3u8 = new_m3u8
            retries_left = max_retries_per_url

        # End of broadcast for this live session – pause before next check.
        time.sleep(cfg.poll_interval)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Forward Twitch/YouTube live audio to an Icecast server."
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        default=Path("config.toml"),
        help="Path to the TOML configuration file (default: config.toml)",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    try:
        cfg = load_config(args.config)
    except Exception as exc:  # pragma: no cover – configuration errors are fatal.
        log.error("Failed to load configuration: %s", exc)
        sys.exit(1)

    log.info("Starting livestream‑to‑icecast for channel: %s", cfg.channel_url)
    _monitor_stream(cfg)


if __name__ == "__main__":
    main()
