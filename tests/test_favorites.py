"""Tests de favoritos persistidos."""

from __future__ import annotations

from terminal_radio.data.favorites import FavoritesStore
from terminal_radio.models.station import Station


def _station(uuid: str, name: str) -> Station:
    return Station(
        stationuuid=uuid,
        name=name,
        url=f"http://example.com/{uuid}",
    )


def test_toggle_add_and_remove(tmp_path) -> None:
    path = tmp_path / "favorites.json"
    store = FavoritesStore(path=path)
    station = _station("a1", "Jazz FM")

    assert store.toggle(station) is True
    assert store.is_favorite("a1")
    assert len(store.list_favorites()) == 1

    assert store.toggle(station) is False
    assert not store.is_favorite("a1")
    assert store.list_favorites() == []


def test_rename_custom_name(tmp_path) -> None:
    path = tmp_path / "favorites.json"
    store = FavoritesStore(path=path)
    station = _station("a1", "Jazz FM")
    store.toggle(station)

    assert store.rename("a1", "Mi Jazz") is True
    favorite = store.find("a1")
    assert favorite is not None
    assert favorite.display_name == "Mi Jazz"


def test_rename_clears_when_same_as_station_name(tmp_path) -> None:
    path = tmp_path / "favorites.json"
    store = FavoritesStore(path=path)
    station = _station("a1", "Jazz FM")
    store.toggle(station)
    store.rename("a1", "Alias")
    store.rename("a1", "Jazz FM")

    favorite = store.find("a1")
    assert favorite is not None
    assert favorite.custom_name is None
    assert favorite.display_name == "Jazz FM"


def test_persistence_roundtrip(tmp_path) -> None:
    path = tmp_path / "favorites.json"
    store = FavoritesStore(path=path)
    store.toggle(_station("a1", "One"))
    store.rename("a1", "Uno")

    reloaded = FavoritesStore(path=path)
    favorite = reloaded.find("a1")
    assert favorite is not None
    assert favorite.display_name == "Uno"
    assert reloaded.favorite_uuids() == {"a1"}
