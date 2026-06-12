"""Metadata enriquecida de pista (Deezer / iTunes)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TrackMeta(BaseModel):
    """Artista, título y álbum resueltos desde APIs externas."""

    title: str | None = None
    artist: str | None = None
    album: str | None = None
    artwork_url: str | None = Field(default=None)

    def display_line(self, *, max_len: int = 36) -> str:
        """Una línea para la barra o el screensaver."""
        if self.artist and self.title:
            text = f"{self.artist} — {self.title}"
        elif self.artist:
            text = self.artist
        elif self.title:
            text = self.title
        else:
            return "-"
        if len(text) <= max_len:
            return text
        return text[: max_len - 1] + "…"
