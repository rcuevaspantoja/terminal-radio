"""Tests de PlayerService con backend simulado."""

from __future__ import annotations

from unittest.mock import MagicMock

from terminal_radio.config import AppSettings
from terminal_radio.models.player import PlayerState
from terminal_radio.models.station import Station
from terminal_radio.services.player import PlayerService, TEST_STREAM_URL


def _make_service() -> tuple[PlayerService, MagicMock]:
    backend = MagicMock()
    backend.is_playing = False
    backend.get_volume.return_value = 50

    settings = AppSettings(volume=50)
    service = PlayerService.__new__(PlayerService)
    service.settings = settings
    service.state = PlayerState(volume=50)
    service._listeners = []
    service._backend = backend
    service._submit = lambda work: work()  # noqa: SLF001 — ejecución síncrona en tests
    return service, backend


def test_play_station_updates_state_and_config() -> None:
    service, backend = _make_service()
    station = Station(
        stationuuid="uuid-1",
        name="Jazz FM",
        url="http://example.com/stream",
        url_resolved="https://example.com/stream",
    )

    service.play_station(station)

    backend.play.assert_called_once_with("https://example.com/stream")
    assert service.state.station_name == "Jazz FM"
    assert service.state.station_uuid == "uuid-1"
    assert service.settings.last_station_uuid == "uuid-1"


def test_play_stream_updates_state() -> None:
    service, backend = _make_service()
    states: list[PlayerState] = []
    service.on_state_change(states.append)

    service.play_stream("http://example.com/stream", "Test FM")

    backend.play.assert_called_once_with("http://example.com/stream")
    assert service.state.station_name == "Test FM"
    assert service.state.is_playing is True
    assert len(states) == 1


def test_toggle_pause() -> None:
    service, backend = _make_service()
    service.state.stream_url = TEST_STREAM_URL
    service.state.is_playing = True
    backend.is_playing = True

    service.toggle_pause()
    backend.pause.assert_called_once()
    assert service.state.is_playing is False

    backend.is_playing = False
    service.toggle_pause()
    backend.resume.assert_called_once()


def test_metadata_callback() -> None:
    service, _backend = _make_service()
    states: list[PlayerState] = []
    service.on_state_change(states.append)

    service._on_metadata("Artist - Song")

    assert service.state.track_title == "Artist - Song"
    assert len(states) == 1
