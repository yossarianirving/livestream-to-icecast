# -*- coding: utf-8 -*-
"""Utility wrappers around ``yt-dlp``.

The helpers are deliberately tiny – they just invoke the external binary and parse its
output.  All error handling is performed by raising ``RuntimeError`` (or returning
``None``) so the calling code can decide what to do next.
"""

from __future__ import annotations


import logging
import subprocess
from typing import Optional

log = logging.getLogger("livestream-to-icecast")


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
