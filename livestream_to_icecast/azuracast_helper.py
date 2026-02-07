# -*- coding: utf-8 -*-
"""Helper for interacting with AzuraCast now‑playing metadata via API."""

import logging
from typing import Dict, Optional

import requests

log = logging.getLogger("azuracast-helper")


def get_current_azuracast_metadata(cfg) -> Optional[Dict[str, str]]:
    """Retrieve the current now‑playing metadata from AzuraCast.

    Returns a dictionary with ``title`` and ``artist`` keys if successful,
    otherwise ``None``. The function validates that the configuration includes a
    base API URL, bearer token **and** station number before attempting the request.
    """
    if (
        not cfg
        or not getattr(cfg, "api_url", None)
        or not getattr(cfg, "bearer_token", None)
        or not getattr(cfg, "station", None)
    ):
        log.warning(
            "AzuraCast config missing or incomplete (API URL, bearer token, or station), skipping metadata retrieval."
        )
        return None

    # Build the URL for retrieving now‑playing information.
    get_url = f"{cfg.api_url.rstrip('/')}/api/nowplaying/{cfg.station}"
    headers = {"X-API-Key": cfg.bearer_token, "Accept": "application/json"}

    try:
        resp = requests.get(get_url, headers=headers, timeout=10)
        if resp.status_code != 200:
            log.error(
                "Failed to retrieve AzuraCast now‑playing metadata: %s %s",
                resp.status_code,
                resp.text,
            )
            return None
        data = resp.json()
        song_info = data.get("now_playing", {}).get("song", {})
        title = song_info.get("title") or ""
        artist = song_info.get("artist") or ""
        return {"title": title, "artist": artist}
    except Exception as exc:  # pragma: no cover – defensive
        log.error("Exception while retrieving AzuraCast metadata: %s", exc)
        return None


def update_azuracast_metadata(cfg, title: str, artist: str) -> bool:
    """Update the AzuraCast stream metadata via a POST request.

    Parameters
    ----------
    cfg : AzuraCastConfig
        The AzuraCast configuration object (from config).
    title : str
        The title of the stream (e.g., livestream title).
    artist : str
        The artist name (e.g., channel name).

    Returns
    -------
    bool
        True if the update was successful, False otherwise.
    """
    if (
        not cfg
        or not getattr(cfg, "api_url", None)
        or not getattr(cfg, "bearer_token", None)
        or not getattr(cfg, "station", None)
    ):
        log.warning(
            "AzuraCast config missing or incomplete (API URL, bearer token, or station), skipping metadata update."
        )
        return False

    # Construct the endpoint URL dynamically based on the base API URL and station number.
    update_url = (
        f"{cfg.api_url.rstrip('/')}/api/station/{cfg.station}/nowplaying/update"
    )

    headers = {
        "X-API-Key": cfg.bearer_token,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {"title": title, "artist": artist}

    try:
        resp = requests.post(update_url, json=payload, headers=headers, timeout=10)
        if resp.status_code == 200:
            log.info("Successfully updated AzuraCast metadata: %r", payload)
            return True
        else:
            log.error(
                "Failed to update AzuraCast metadata: %s %s",
                resp.status_code,
                resp.text,
            )
            return False
    except Exception as exc:  # pragma: no cover – defensive
        log.error("Exception while updating AzuraCast metadata: %s", exc)
        return False
