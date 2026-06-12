"""Persistencia de favoritos en favorites.json."""

from __future__ import annotations

import json
from pathlib import Path

from terminal_radio.models.favorite import FavoriteStation
from terminal_radio.models.station import Station
from terminal_radio.platform.detect import get_config_dir

FAVORITES_FILENAME = "favorites.json"


def get_favorites_path() -> Path:
    return get_config_dir() / FAVORITES_FILENAME


class FavoritesStore:
    """CRUD de favoritos en disco."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or get_favorites_path()
        self._items: list[FavoriteStation] = self.load()

    def load(self) -> list[FavoriteStation]:
        if not self._path.is_file():
            return []
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        if not isinstance(data, list):
            return []
        return [FavoriteStation.model_validate(item) for item in data]

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = [item.model_dump(mode="json") for item in self._items]
        self._path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def list_favorites(self) -> list[FavoriteStation]:
        return list(self._items)

    def favorite_uuids(self) -> set[str]:
        return {item.station.stationuuid for item in self._items}

    def is_favorite(self, station_uuid: str) -> bool:
        return station_uuid in self.favorite_uuids()

    def find(self, station_uuid: str) -> FavoriteStation | None:
        for item in self._items:
            if item.station.stationuuid == station_uuid:
                return item
        return None

    def toggle(self, station: Station) -> bool:
        """Alterna favorito. Devuelve True si quedó marcada."""
        existing = self.find(station.stationuuid)
        if existing is not None:
            self._items = [
                item for item in self._items if item.station.stationuuid != station.stationuuid
            ]
            self.save()
            return False
        self._items.append(FavoriteStation(station=station))
        self.save()
        return True

    def rename(self, station_uuid: str, custom_name: str | None) -> bool:
        item = self.find(station_uuid)
        if item is None:
            return False
        cleaned = custom_name.strip() if custom_name else None
        if cleaned == item.station.name:
            cleaned = None
        index = self._items.index(item)
        self._items[index] = item.model_copy(update={"custom_name": cleaned})
        self.save()
        return True
