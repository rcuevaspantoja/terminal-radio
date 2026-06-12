"""Tests de la barra del reproductor."""

from __future__ import annotations

from terminal_radio.models.player import PlayerState
from terminal_radio.widgets.player_bar import PlayerBar, format_volume_meter


def test_format_volume_meter() -> None:
    assert format_volume_meter(0) == "[--------------]   0%"
    assert format_volume_meter(100) == "[##############] 100%"
    assert " 65%" in format_volume_meter(65)
    assert "#" in format_volume_meter(50)
    assert "-" in format_volume_meter(50)


def test_format_state_playing() -> None:
    state = PlayerState(
        station_name="Jazz FM",
        is_playing=True,
        volume=50,
        track_title="Artist - Song",
    )
    text = PlayerBar.format_state(state)
    assert "Jazz FM" in text
    assert "Artist - Song" in text
    assert text.startswith(">")
    assert "VOL" in text
    assert "50%" in text
    assert "VOL" in text


def test_format_state_paused() -> None:
    state = PlayerState(station_name="Jazz FM", is_playing=False, volume=30)
    text = PlayerBar.format_state(state)
    assert text.startswith("||")
    assert "30%" in text
