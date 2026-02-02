# -*- coding: utf-8 -*-
"""Helper for updating AzuraCast (Icecast) stream metadata via API."""

import logging

import requests

log = logging.getLogger("azuracast-helper")


def update_azuracast_metadata(cfg, title: str, artist: str) -> bool:
    """
    Update the AzuraCast stream metadata via a POST request.

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
    if not cfg or not cfg.api_url or not cfg.bearer_token:
        log.warning("AzuraCast config missing or incomplete, skipping metadata update.")
        return False

    headers = {
        "X-API-Key": f"{cfg.bearer_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {
        "title": title,
        "artist": artist,
    }

    try:
        resp = requests.post(cfg.api_url, json=payload, headers=headers, timeout=10)
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
    except Exception as exc:
        log.error("Exception while updating AzuraCast metadata: %s", exc)
        return False
