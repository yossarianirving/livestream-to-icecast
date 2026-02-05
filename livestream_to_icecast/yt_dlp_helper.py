# -*- coding: utf-8 -*-
"""Utility wrappers around ``yt-dlp``.

The helpers are deliberately tiny – they just invoke the external binary and parse its
output.  All error handling is performed by raising ``RuntimeError`` (or returning
``None``) so the calling code can decide what to do next.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from typing import Optional

import requests

log = logging.getLogger("livestream-to-icecast")


@dataclass
class StreamInfo:
    title: str
    description: str
    m3u8_url: str


def _run_yt_dlp(args: list[str]) -> str:
    """Execute ``yt-dlp`` with *args* and return its stdout.

    The function captures both stdout and stderr.  If the process exits with a non‑zero
    status, a ``RuntimeError`` is raised containing the error output.
    """
    result = subprocess.run(
        ["yt-dlp", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {result.stderr.strip()}")
    return result.stdout.strip()


def is_live(channel_url: str) -> bool:
    """Return ``True`` if *channel_url* appears to be a live broadcast.

    The original implementation queried yt‑dlp for JSON metadata (``-j``), which can be
    slow.  Instead we now attempt to retrieve the best‑audio URL using ``yt-dlp -g``
    via :func:`get_m3u8_url`. If any stream URL is returned, we treat the channel as live.
    This approach is faster and aligns with the updated requirement.
    """
    try:
        # Reuse the existing helper that extracts the best‑audio (usually HLS) URL.
        url = get_m3u8_url(channel_url)
        # If any stream URL is obtained, consider the channel as live.
        return bool(url)
    except Exception as exc:  # pragma: no cover – defensive fallback
        log.debug("is_live check failed: %s", exc)
        return False


def get_stream_info(channel_url: str) -> Optional[StreamInfo]:
    """
    Obtain the best-audio (usually an m3u8 playlist) URL and the title for a live stream.

    Returns:
        (m3u8_url, title, description) if available, otherwise None.
    """
    import json

    try:
        # Use yt-dlp to get JSON metadata
        output = _run_yt_dlp(["-J", "-f", "bestaudio", channel_url])
        info = json.loads(output)
        title = info.get("title", "")
        description = info.get("description")
        # Find the best m3u8 URL in formats
        m3u8_url = None

        for fmt in info.get("formats", []):
            if fmt.get("protocol") == "m3u8" and fmt.get("url"):
                m3u8_url = fmt["url"]
                break
        if not m3u8_url:
            # fallback: try url field
            m3u8_url = info.get("url")
        if m3u8_url and title and description:
            return StreamInfo(title=title, m3u8_url=m3u8_url, description=description)
        return None
    except Exception as exc:
        log.error("Failed to get stream info: %s", exc)
        return None


def get_m3u8_url(channel_url: str) -> Optional[str]:
    """Obtain the best‑audio (usually an m3u8 playlist) URL for a live stream.

    ``yt-dlp -g`` prints the final media URL.  Using the ``bestaudio`` format selector
    typically yields an HLS (m3u8) stream when one is available.
    """
    try:
        url = _run_yt_dlp(
            ["-g", "-f", "bestaudio", "--no-check-certificate", channel_url]
        )
        log.info(f"Found stream {url}")
        return url
    except Exception:
        return None


def check_m3u8_url(m3u8_url: str) -> bool:
    try:
        response = requests.get(m3u8_url, timeout=10)
        if response.status_code != 200:
            return False
        return True

    except:
        return False
