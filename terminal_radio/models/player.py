"""Estado del reproductor."""

from __future__ import annotations

from pydantic import BaseModel, Field


from terminal_radio.models.metadata import TrackMeta


class PlayerState(BaseModel):
    """Snapshot observable del estado de reproducción."""

    station_name: str | None = None
    station_uuid: str | None = None
    stream_url: str | None = None
    is_playing: bool = False
    volume: int = Field(default=50, ge=0, le=100)
    track_title: str | None = None
    track_meta: TrackMeta | None = None
    error: str | None = None
