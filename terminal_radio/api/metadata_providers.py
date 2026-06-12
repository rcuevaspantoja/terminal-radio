"""Clientes Deezer e iTunes para enriquecer metadata ICY."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote

import httpx

from terminal_radio.models.metadata import TrackMeta

logger = logging.getLogger(__name__)

DEEZER_SEARCH = "https://api.deezer.com/search"
ITUNES_SEARCH = "https://itunes.apple.com/search"
DEFAULT_TIMEOUT = 8.0


def parse_icy_title(raw: str) -> tuple[str | None, str | None]:
    """Separa 'Artist - Title' en componentes."""
    text = raw.strip()
    if not text:
        return None, None
    for sep in (" - ", " – ", " — ", " | "):
        if sep in text:
            left, _, right = text.partition(sep)
            artist = left.strip() or None
            title = right.strip() or None
            return artist, title
    return None, text


async def search_deezer(
    client: httpx.AsyncClient,
    query: str,
    *,
    artist_hint: str | None = None,
    title_hint: str | None = None,
) -> TrackMeta | None:
    try:
        response = await client.get(
            DEEZER_SEARCH,
            params={"q": query, "limit": 1},
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as exc:
        logger.debug("Deezer search failed: %s", exc)
        return None

    items = data.get("data") if isinstance(data, dict) else None
    if not items:
        return None
    item = items[0]
    if not isinstance(item, dict):
        return None

    artist = _nested_name(item.get("artist"))
    title = item.get("title") if isinstance(item.get("title"), str) else None
    album = _nested_name(item.get("album"))
    artwork = item.get("album", {}).get("cover_medium") if isinstance(item.get("album"), dict) else None

    if not artist and not title:
        return None
    return TrackMeta(
        title=title or title_hint,
        artist=artist or artist_hint,
        album=album,
        artwork_url=artwork if isinstance(artwork, str) else None,
    )


async def search_itunes(
    client: httpx.AsyncClient,
    query: str,
    *,
    artist_hint: str | None = None,
    title_hint: str | None = None,
) -> TrackMeta | None:
    try:
        response = await client.get(
            ITUNES_SEARCH,
            params={"term": query, "media": "music", "limit": 1},
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPError as exc:
        logger.debug("iTunes search failed: %s", exc)
        return None

    results = data.get("results") if isinstance(data, dict) else None
    if not results:
        return None
    item = results[0]
    if not isinstance(item, dict):
        return None

    artist = item.get("artistName") if isinstance(item.get("artistName"), str) else None
    title = item.get("trackName") if isinstance(item.get("trackName"), str) else None
    album = item.get("collectionName") if isinstance(item.get("collectionName"), str) else None
    artwork = item.get("artworkUrl100") if isinstance(item.get("artworkUrl100"), str) else None

    if not artist and not title:
        return None
    return TrackMeta(
        title=title or title_hint,
        artist=artist or artist_hint,
        album=album,
        artwork_url=artwork,
    )


def _nested_name(value: Any) -> str | None:
    if isinstance(value, dict):
        name = value.get("name")
        return name if isinstance(name, str) else None
    return None


def build_search_query(track_title: str) -> tuple[str, str | None, str | None]:
    artist, title = parse_icy_title(track_title)
    if artist and title:
        return f"{artist} {title}", artist, title
    return track_title.strip(), artist, title
