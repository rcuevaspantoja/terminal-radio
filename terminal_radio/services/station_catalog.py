"""Servicio de favoritos e historial."""

from __future__ import annotations

from terminal_radio.config import AppSettings
from terminal_radio.data.favorites import FavoritesStore
from terminal_radio.data.history import HistoryStore
from terminal_radio.models.favorite import FavoriteStation
from terminal_radio.models.history import HistoryEntry
from terminal_radio.models.station import Station


class StationCatalogService:
    """Orquesta favoritos e historial persistidos."""

    def __init__(
        self,
        settings: AppSettings,
        *,
        favorites: FavoritesStore | None = None,
        history: HistoryStore | None = None,
    ) -> None:
        self.settings = settings
        self.favorites = favorites or FavoritesStore()
        self.history = history or HistoryStore()

    def favorite_uuids(self) -> set[str]:
        return self.favorites.favorite_uuids()

    def list_favorites(self) -> list[FavoriteStation]:
        return self.favorites.list_favorites()

    def list_history(self) -> list[HistoryEntry]:
        return self.history.list_entries()

    def history_stations(self) -> list[Station]:
        return self.history.stations()

    def favorite_display_names(self) -> dict[str, str]:
        return {item.station.stationuuid: item.display_name for item in self.list_favorites()}

    def is_favorite(self, station_uuid: str) -> bool:
        return self.favorites.is_favorite(station_uuid)

    def toggle_favorite(self, station: Station) -> bool:
        return self.favorites.toggle(station)

    def rename_favorite(self, station_uuid: str, custom_name: str | None) -> bool:
        return self.favorites.rename(station_uuid, custom_name)

    def find_favorite(self, station_uuid: str) -> FavoriteStation | None:
        return self.favorites.find(station_uuid)

    def record_play(self, station: Station) -> None:
        self.history.add(station, max_entries=self.settings.history_max)
