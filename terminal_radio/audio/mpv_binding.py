"""Backend de audio vía binding python-mpv (libmpv)."""

from __future__ import annotations

import logging
from collections.abc import Callable

from terminal_radio.audio.backend import AudioBackend, MetadataCallback
from terminal_radio.audio.mpv_options import get_mpv_stream_kwargs

logger = logging.getLogger(__name__)


class MpvBindingBackend(AudioBackend):
    """Controla libmpv en proceso mediante python-mpv."""

    def __init__(self, volume: int = 50) -> None:
        try:
            import mpv  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError("python-mpv no está instalado") from exc

        self._volume = max(0, min(100, volume))
        self._playing = False
        self._metadata_callbacks: list[MetadataCallback] = []

        try:
            self._player = mpv.MPV(
                ytdl=False,
                input_default_bindings=False,
                input_vo_keyboard=False,
                **get_mpv_stream_kwargs(),
            )
            self._player.volume = self._volume
        except Exception as exc:
            raise RuntimeError("libmpv no disponible") from exc

        @self._player.property_observer("media-title")
        def _on_media_title(_name: str, value: object) -> None:
            title = str(value) if value else None
            for callback in self._metadata_callbacks:
                try:
                    callback(title)
                except Exception:
                    logger.exception("Error en callback de metadata")

        self._title_observer = _on_media_title

    def play(self, url: str) -> None:
        self._player.play(url)
        self._playing = True
        self._player.pause = False

    def stop(self) -> None:
        self._player.command("stop")
        self._playing = False

    def pause(self) -> None:
        self._player.pause = True

    def resume(self) -> None:
        self._player.pause = False

    def set_volume(self, level: int) -> None:
        self._volume = max(0, min(100, level))
        self._player.volume = self._volume

    def get_volume(self) -> int:
        try:
            self._volume = int(self._player.volume)
        except (AttributeError, TypeError, ValueError):
            pass
        return self._volume

    @property
    def is_playing(self) -> bool:
        if not self._playing:
            return False
        try:
            return not bool(self._player.pause)
        except AttributeError:
            return self._playing

    def on_metadata(self, callback: MetadataCallback) -> None:
        self._metadata_callbacks.append(callback)

    def shutdown(self) -> None:
        try:
            self._player.terminate()
        except Exception:
            logger.exception("Error al cerrar mpv binding")
        self._playing = False
