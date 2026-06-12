"""Persistencia de historial en history.json."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from terminal_radio.models.history import HistoryEntry
from terminal_radio.models.station import Station
from terminal_radio.platform.detect import get_config_dir

HISTORY_FILENAME = "history.json"


def get_history_path() -> Path:
    return get_config_dir() / HISTORY_FILENAME


class HistoryStore:
    """Historial de reproducción con deduplicación por UUID."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or get_history_path()
        self._entries: list[HistoryEntry] = self.load()

    def load(self) -> list[HistoryEntry]:
        if not self._path.is_file():
            return []
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        if not isinstance(data, list):
            return []
        return [HistoryEntry.model_validate(item) for item in data]

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = [entry.model_dump(mode="json") for entry in self._entries]
        self._path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def list_entries(self) -> list[HistoryEntry]:
        return list(self._entries)

    def stations(self) -> list[Station]:
        return [entry.station for entry in self._entries]

    def add(self, station: Station, *, max_entries: int) -> None:
        now = datetime.now(timezone.utc)
        self._entries = [
            entry for entry in self._entries if entry.station.stationuuid != station.stationuuid
        ]
        self._entries.insert(0, HistoryEntry(station=station, played_at=now))
        if len(self._entries) > max_entries:
            self._entries = self._entries[:max_entries]
        self.save()
