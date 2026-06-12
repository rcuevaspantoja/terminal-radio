"""Tests de parseo y providers de metadata."""

from __future__ import annotations

import asyncio

import httpx
import pytest

from terminal_radio.api.metadata_providers import (
    build_search_query,
    parse_icy_title,
    search_deezer,
    search_itunes,
)


def test_parse_icy_title_artist_dash_title() -> None:
    artist, title = parse_icy_title("Daft Punk - Around the World")
    assert artist == "Daft Punk"
    assert title == "Around the World"


def test_parse_icy_title_plain() -> None:
    artist, title = parse_icy_title("Live from Studio")
    assert artist is None
    assert title == "Live from Studio"


def test_build_search_query() -> None:
    query, artist, title = build_search_query("Artist - Song")
    assert query == "Artist Song"
    assert artist == "Artist"
    assert title == "Song"


def test_search_deezer_parses_response() -> None:
    async def run() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "title": "Song",
                            "artist": {"name": "Artist"},
                            "album": {"name": "Album", "cover_medium": "http://img"},
                        }
                    ]
                },
            )

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        meta = await search_deezer(client, "Artist Song")
        await client.aclose()
        assert meta is not None
        assert meta.artist == "Artist"
        assert meta.title == "Song"
        assert meta.album == "Album"

    asyncio.run(run())


def test_search_itunes_fallback() -> None:
    async def run() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "artistName": "Artist",
                            "trackName": "Song",
                            "collectionName": "Album",
                        }
                    ]
                },
            )

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        meta = await search_itunes(client, "Artist Song")
        await client.aclose()
        assert meta is not None
        assert meta.artist == "Artist"
        assert meta.title == "Song"

    asyncio.run(run())
