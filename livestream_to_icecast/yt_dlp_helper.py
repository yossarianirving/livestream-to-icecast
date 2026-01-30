# -*- coding: utf-8 -*-
"""Utility wrappers around ``yt-dlp``.

The helpers are deliberately tiny – they just invoke the external binary and parse its
output.  All error handling is performed by raising ``RuntimeError`` (or returning
``None``) so the calling code can decide what to do next.
"""

from __future__ import annotations

import json
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
    """Return ``True`` if *channel_url* currently has a live broadcast.

    The function asks yt‑dlp for JSON metadata (``-j``).  The returned dictionary may be a
    single video entry or a playlist with an ``entries`` list – we handle both cases.
    """
    try:
        json_text = _run_yt_dlp(["-j", "--skip-download", channel_url])
        info = json.loads(json_text)

        # yt‑dlp can return a playlist dict that contains an ``entries`` array.
        if isinstance(info, dict) and "entries" in info:
            for entry in info["entries"] or []:
                if entry and entry.get("is_live"):
                    return True
            return False

        # Single video case – the key may be missing, default to ``False``.
        return bool(info.get("is_live"))
    except Exception:
        # Any problem (network, parsing…) is treated as "not live" to avoid false
        # positives.
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
