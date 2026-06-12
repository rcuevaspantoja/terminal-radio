"""Tests de historial persistido."""

from __future__ import annotations

from terminal_radio.data.history import HistoryStore
from terminal_radio.models.station import Station


def _station(uuid: str, name: str) -> Station:
    return Station(
        stationuuid=uuid,
        name=name,
        url=f"http://example.com/{uuid}",
    )


def test_history_dedup_moves_to_front(tmp_path) -> None:
    path = tmp_path / "history.json"
    store = HistoryStore(path=path)
    a = _station("a", "Alpha")
    b = _station("b", "Beta")

    store.add(a, max_entries=10)
    store.add(b, max_entries=10)
    store.add(a, max_entries=10)

    stations = store.stations()
    assert [s.stationuuid for s in stations] == ["a", "b"]


def test_history_respects_max_entries(tmp_path) -> None:
    path = tmp_path / "history.json"
    store = HistoryStore(path=path)

    for index in range(5):
        store.add(_station(f"id-{index}", f"Station {index}"), max_entries=3)

    assert len(store.list_entries()) == 3
    assert [s.stationuuid for s in store.stations()] == ["id-4", "id-3", "id-2"]


def test_history_persistence_roundtrip(tmp_path) -> None:
    path = tmp_path / "history.json"
    store = HistoryStore(path=path)
    store.add(_station("x", "X FM"), max_entries=50)

    reloaded = HistoryStore(path=path)
    assert len(reloaded.list_entries()) == 1
    assert reloaded.stations()[0].name == "X FM"
