"""Tests de TrackMeta y barra con artista."""

from __future__ import annotations

from terminal_radio.models.metadata import TrackMeta
from terminal_radio.models.player import PlayerState
from terminal_radio.widgets.player_bar import PlayerBar


def test_track_meta_display_line() -> None:
    meta = TrackMeta(artist="Artist", title="Song")
    assert meta.display_line() == "Artist — Song"


def test_player_bar_shows_enriched_artist() -> None:
    state = PlayerState(
        station_name="Jazz FM",
        is_playing=True,
        track_title="Unknown ICY",
        track_meta=TrackMeta(artist="Miles Davis", title="So What"),
    )
    text = PlayerBar.format_state(state)
    assert "Miles Davis" in text
    assert "So What" in text
    assert "Unknown ICY" not in text
