"""Persistencia de favoritos e historial."""

from terminal_radio.data.favorites import FavoritesStore, get_favorites_path
from terminal_radio.data.history import HistoryStore, get_history_path

__all__ = [
    "FavoritesStore",
    "HistoryStore",
    "get_favorites_path",
    "get_history_path",
]
