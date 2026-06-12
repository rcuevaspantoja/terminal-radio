"""Modelo de estación de radio (radio-browser)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Station(BaseModel):
    """Estación devuelta por la API radio-browser."""

    stationuuid: str
    name: str
    url: str
    url_resolved: str | None = None
    country: str | None = None
    codec: str | None = None
    bitrate: int | None = None
    tags: str | None = None

    @property
    def stream_url(self) -> str:
        """URL de reproducción preferida."""
        return (self.url_resolved or self.url).strip()

    def format_list_line(
        self,
        favorite: bool = False,
        *,
        active: bool = False,
        playing: bool = False,
        display_name: str | None = None,
    ) -> str:
        """Una línea para la lista: indicador, nombre, codec, bitrate, país."""
        if active and playing:
            prefix = "> "
        elif active:
            prefix = "|| "
        elif favorite:
            prefix = "* "
        else:
            prefix = "  "
        parts = [display_name or self.name]
        if self.codec:
            parts.append(self.codec.upper())
        if self.bitrate:
            parts.append(f"{self.bitrate}k")
        if self.country:
            parts.append(self.country)
        return prefix + " · ".join(parts)

    @classmethod
    def from_api(cls, data: dict) -> Station:
        """Construye desde un dict de la API (campos extra ignorados)."""
        return cls.model_validate(data)
