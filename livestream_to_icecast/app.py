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
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

from .azuracast_helper import get_current_azuracast_metadata, update_azuracast_metadata
from .config import AppConfig, load_config
from .yt_dlp_helper import check_m3u8_url, get_m3u8_url, get_stream_info, is_live

log = logging.getLogger("livestream-to-icecast")

# Global stop event for clean shutdown and reference to the current ffmpeg process.
STOP_EVENT = threading.Event()
CURRENT_PROC: subprocess.Popen | None = None


def _handle_signal(signum, frame):  # pragma: no cover – exercised via manual signal.
    """Signal handler that triggers a graceful shutdown.

    It sets ``STOP_EVENT`` which is checked throughout the main loop. The actual
    termination of the ffmpeg child process happens in the monitoring code to avoid
    doing heavy work inside the signal context.
    """
    log.info("Received signal %s – initiating clean shutdown", signum)
    STOP_EVENT.set()


def _cleanup_ffmpeg(proc: subprocess.Popen | None) -> None:
    """Terminate a running ffmpeg process gracefully.

    If the process does not exit within 5 seconds, it is force‑killed. Any
    exception during termination is logged but otherwise ignored to avoid masking
    the original shutdown reason.
    """
    if proc is None:
        return
    try:
        log.info("Terminating ffmpeg process (pid %s)", proc.pid)
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            log.warning("ffmpeg did not terminate in time – killing")
            proc.kill()
    except Exception as exc:  # pragma: no cover – defensive
        log.error("Error while terminating ffmpeg: %s", exc)


# Register handlers for common termination signals.
signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)


def _build_icecast_url(cfg: AppConfig) -> str:
    """Construct the Icecast destination URL for ffmpeg.

    ``ffmpeg`` expects a URL of the form::

        icecast://user:password@host:port/mount
    """
    ice = cfg.icecast
    mount = ice.mount if ice.mount.startswith("/") else f"/{ice.mount}"
    return f"icecast://{ice.source_user}:{ice.source_password}@{ice.host}:{ice.port}{mount}"


def _start_ffmpeg(m3u8_url: str, cfg: AppConfig) -> subprocess.Popen:
    """Spawn ``ffmpeg`` and keep a reference to the process.

    The global ``CURRENT_PROC`` is updated so that signal handling can terminate it
    cleanly if the program receives SIGINT/SIGTERM.
    """
    global CURRENT_PROC
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
        "-ac",
        "1",
        "-f",
        fmt,
        out_url,
    ]

    log.info("Starting ffmpeg: %s", " ".join(cmd))
    # ``stdout`` is discarded; we only keep stderr for diagnostics.
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    # Store reference for graceful shutdown.
    global CURRENT_PROC
    CURRENT_PROC = proc
    return proc


def _monitor_stream(cfg: AppConfig) -> None:
    """Main loop that watches the channel and keeps ffmpeg alive.

    The algorithm mirrors the specification:

    * Poll for live status every ``cfg.poll_interval`` seconds.
    * When live, fetch an m3u8 URL and start ffmpeg.
    * If ffmpeg exits, retry a few times with the same URL; after exhausting those
      attempts request a fresh URL.  If we cannot obtain a new working URL we wait for
      the next live event.
    """
    global CURRENT_PROC

    while True:
        # Check for shutdown request before each iteration.
        if STOP_EVENT.is_set():
            log.info("Shutdown requested – exiting monitor loop")
            break
        # -----------------------------------------------------------------
        # Wait until the channel is broadcasting.
        # -----------------------------------------------------------------
        if not is_live(cfg.channel_url):
            log.info(
                "Channel not live – checking again in %s seconds", cfg.poll_interval
            )
            STOP_EVENT.wait(cfg.poll_interval)
            continue

        # Channel is live; obtain stream info (m3u8 URL and title).
        stream_info = get_stream_info(cfg.channel_url, cfg.platform)

        if not stream_info:
            log.error("Failed to retrieve stream info while channel appears live")
            STOP_EVENT.wait(cfg.poll_interval)
            continue

        # Stream url used to check if it is still up
        stream_url = stream_info.m3u8_url
        # Update AzuraCast metadata if configured
        # Update AzuraCast metadata if configured and changed.
        if getattr(cfg, "azuracast", None):
            new_title = stream_info.title
            new_artist = cfg.channel_name
            current_meta = get_current_azuracast_metadata(cfg.azuracast)
            if (
                not current_meta
                or current_meta.get("title") != new_title
                or current_meta.get("artist") != new_artist
            ):
                update_azuracast_metadata(
                    cfg.azuracast, title=new_title, artist=new_artist
                )
            else:
                log.info("AzuraCast metadata unchanged; skipping update.")

        # -----------------------------------------------------------------
        # Inner loop: keep ffmpeg running for the *current* stream.
        # -----------------------------------------------------------------
        while True:
            if STOP_EVENT.is_set():
                _cleanup_ffmpeg(CURRENT_PROC)
                update_azuracast_metadata(
                    cfg.azuracast, title="OFFLINE", artist="OFFLINE"
                )
                return

            proc = None
            if CURRENT_PROC is not None:
                proc = CURRENT_PROC
            else:
                proc = _start_ffmpeg(stream_info.m3u8_url, cfg)

            # Poll ffmpeg every few seconds; if it exits we break to retry logic.
            if STOP_EVENT.is_set():
                _cleanup_ffmpeg(proc)
                return
            retcode = proc.poll()
            if retcode is not None:  # Process terminated.
                err_msg = proc.stderr.read().strip() if proc.stderr else ""
                log.warning(
                    "ffmpeg exited (code %s). Stderr: %s",
                    retcode,
                    err_msg or "<empty>",
                )
                update_azuracast_metadata(
                    cfg.azuracast, title="OFFLINE", artist="OFFLINE"
                )
                # Process is done – clear global reference.
                CURRENT_PROC = None
                break

            new_stream_info = get_stream_info(cfg.channel_url, cfg.platform)

            if not new_stream_info:
                _cleanup_ffmpeg(CURRENT_PROC)
                log.error(
                    "Unable to obtain a new working m3u8 URL. Waiting for channel to go offline"
                )
                update_azuracast_metadata(
                    cfg.azuracast, title="OFFLINE", artist="OFFLINE"
                )
                break  # exit inner loop; outer will re‑check live status.

            # Update AzuraCast metadata if configured and changed.
            if getattr(cfg, "azuracast", None):
                new_title = new_stream_info.title
                new_artist = cfg.channel_name
                current_meta = get_current_azuracast_metadata(cfg.azuracast)
                if (
                    not current_meta
                    or current_meta.get("title") != new_title
                    or current_meta.get("artist") != new_artist
                ):
                    update_azuracast_metadata(
                        cfg.azuracast, title=new_title, artist=new_artist
                    )
                else:
                    log.info(
                        "AzuraCast metadata unchanged after fresh URL – skipping update."
                    )
            stream_info = new_stream_info
            # Check if curent stream is still up
            stream_ok = check_m3u8_url(stream_url)
            if not stream_ok:
                _cleanup_ffmpeg(CURRENT_PROC)
                CURRENT_PROC = None
                continue
            STOP_EVENT.wait(cfg.poll_interval)

        # End of broadcast for this live session – pause before next check.
        STOP_EVENT.wait(cfg.poll_interval)

    # Clean up any lingering ffmpeg process on exit.
    _cleanup_ffmpeg(CURRENT_PROC)


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
