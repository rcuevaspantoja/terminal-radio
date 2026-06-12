"""Modelo de entrada de historial de reproducción."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from terminal_radio.models.station import Station


class HistoryEntry(BaseModel):
    """Estación reproducida con marca temporal."""

    station: Station
    played_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
