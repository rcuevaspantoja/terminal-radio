"""Orquesta búsqueda de metadata enriquecida."""

from __future__ import annotations

import httpx

from terminal_radio.api.metadata_providers import (
    build_search_query,
    search_deezer,
    search_itunes,
)
from terminal_radio.models.metadata import TrackMeta


class MetadataService:
    """Resuelve ICY title → artista/título vía Deezer, con fallback iTunes."""

    def __init__(self, *, client: httpx.AsyncClient | None = None) -> None:
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            headers={"User-Agent": "TerminalRadio/1.0"},
            timeout=8.0,
            follow_redirects=True,
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def fetch(self, track_title: str | None) -> TrackMeta | None:
        if not track_title or not track_title.strip():
            return None
        query, artist_hint, title_hint = build_search_query(track_title)
        meta = await search_deezer(
            self._client,
            query,
            artist_hint=artist_hint,
            title_hint=title_hint,
        )
        if meta is not None:
            return meta
        return await search_itunes(
            self._client,
            query,
            artist_hint=artist_hint,
            title_hint=title_hint,
        )
