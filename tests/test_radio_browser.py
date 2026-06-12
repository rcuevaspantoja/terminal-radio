"""Tests del cliente radio-browser."""

from __future__ import annotations

import asyncio

import httpx
import pytest

from terminal_radio.api.radio_browser import RadioBrowserClient, RadioBrowserError
from terminal_radio.models.station import Station


def _sample_station_json() -> dict:
    return {
        "stationuuid": "96202f73-0601-11e8-ae97-52543be04c81",
        "name": "Groove Salad",
        "url": "http://ice1.somafm.com/groovesalad-128-mp3",
        "url_resolved": "https://ice1.somafm.com/groovesalad-128-mp3",
        "country": "USA",
        "codec": "mp3",
        "bitrate": 128,
    }


def test_station_stream_url_prefers_resolved() -> None:
    station = Station.from_api(_sample_station_json())
    assert station.stream_url == "https://ice1.somafm.com/groovesalad-128-mp3"
    assert "Groove Salad" in station.format_list_line()
    assert "MP3" in station.format_list_line()
    assert "128k" in station.format_list_line()
    assert "USA" in station.format_list_line()


def test_search_parses_results() -> None:
    async def run() -> None:
        payload = [_sample_station_json()]

        def handler(request: httpx.Request) -> httpx.Response:
            assert "/json/stations/search" in str(request.url)
            assert request.headers.get("User-Agent", "").startswith("TerminalRadio/")
            return httpx.Response(200, json=payload)

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        api = RadioBrowserClient(client=client)

        stations = await api.search("groove")
        await api.aclose()

        assert len(stations) == 1
        assert stations[0].name == "Groove Salad"

    asyncio.run(run())


def test_top_voted() -> None:
    async def run() -> None:
        payload = [_sample_station_json()]

        def handler(request: httpx.Request) -> httpx.Response:
            assert "/json/stations/topvote" in str(request.url)
            return httpx.Response(200, json=payload)

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        api = RadioBrowserClient(client=client)

        stations = await api.top_voted(limit=10)
        await api.aclose()

        assert len(stations) == 1

    asyncio.run(run())


def test_click_posts_to_url_endpoint() -> None:
    async def run() -> None:
        seen: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(f"{request.method} {request.url.path}")
            return httpx.Response(200, json=[])

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        api = RadioBrowserClient(client=client)

        await api.click("96202f73-0601-11e8-ae97-52543be04c81")
        await api.aclose()

        assert any("POST" in entry and "/json/url/" in entry for entry in seen)

    asyncio.run(run())


def test_rotates_server_on_failure() -> None:
    async def run() -> None:
        calls: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(str(request.url.host))
            if len(calls) == 1:
                return httpx.Response(500)
            return httpx.Response(200, json=[_sample_station_json()])

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        api = RadioBrowserClient(client=client)

        stations = await api.top_voted()
        await api.aclose()

        assert len(stations) == 1
        assert len(calls) == 2
        assert calls[0] != calls[1]

    asyncio.run(run())


def test_all_servers_fail_raises_friendly_error() -> None:
    async def run() -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503)

        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        api = RadioBrowserClient(client=client)

        with pytest.raises(RadioBrowserError, match="Server error"):
            await api.top_voted()
        await api.aclose()

    asyncio.run(run())
