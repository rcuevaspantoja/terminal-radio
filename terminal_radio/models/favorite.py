"""Modelo de estación favorita."""

from __future__ import annotations

from pydantic import BaseModel, Field

from terminal_radio.models.station import Station


class FavoriteStation(BaseModel):
    """Estación guardada con nombre personalizable."""

    station: Station
    custom_name: str | None = Field(default=None)

    @property
    def display_name(self) -> str:
        if self.custom_name and self.custom_name.strip():
            return self.custom_name.strip()
        return self.station.name
