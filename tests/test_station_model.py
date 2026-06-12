"""Tests del modelo Station."""

from __future__ import annotations

from terminal_radio.models.station import Station


def test_format_list_line_with_favorite() -> None:
    station = Station(
        stationuuid="abc",
        name="Jazz FM",
        url="http://example.com",
        codec="aac",
        bitrate=64,
        country="UK",
    )
    normal = station.format_list_line()
    favorite = station.format_list_line(favorite=True)
    assert normal.startswith("  Jazz FM")
    assert favorite.startswith("* ")
    playing = station.format_list_line(active=True, playing=True)
    paused = station.format_list_line(active=True, playing=False)
    assert playing.startswith("> ")
    assert paused.startswith("|| ")


def test_format_list_line_custom_display_name() -> None:
    station = Station(
        stationuuid="abc",
        name="Jazz FM",
        url="http://example.com",
    )
    line = station.format_list_line(display_name="Mi Jazz")
    assert line.startswith("  Mi Jazz")
