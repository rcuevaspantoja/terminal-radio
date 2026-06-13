"""Orquestación de reproducción: audio backend + estado observable."""

from __future__ import annotations

import logging
import queue
import threading
from collections.abc import Callable

from terminal_radio.audio.backend import AudioBackend, MpvNotFoundError, create_audio_backend
from terminal_radio.config import AppSettings
from terminal_radio.debug.perf import perf
from terminal_radio.models.metadata import TrackMeta
from terminal_radio.models.player import PlayerState
from terminal_radio.models.station import Station

logger = logging.getLogger(__name__)

TEST_STREAM_NAME = "SomaFM Groove Salad"
TEST_STREAM_URL = "https://ice1.somafm.com/groovesalad-128-mp3"

StateCallback = Callable[[PlayerState], None]

_AUDIO_WORKER_NAME = "player-audio"


class PlayerService:
    """Fuente de verdad del player. La UI solo observa y envía comandos."""

    def __init__(self, settings: AppSettings) -> None:
        from terminal_radio.audio.mpv_subprocess import MpvSubprocessBackend

        MpvSubprocessBackend.cleanup_stale_process()
        self.settings = settings
        self.state = PlayerState(volume=settings.volume)
        self._listeners: list[StateCallback] = []
        self._closing = False
        self._work_queue: queue.Queue[Callable[[], None] | None] = queue.Queue()
        self._worker = threading.Thread(
            target=self._worker_loop,
            name=_AUDIO_WORKER_NAME,
            daemon=True,
        )
        self._worker.start()
        self._backend: AudioBackend = create_audio_backend(volume=settings.volume)
        self._backend.on_metadata(self._on_metadata)

    def on_state_change(self, callback: StateCallback) -> None:
        self._listeners.append(callback)

    def play_test_stream(self) -> None:
        self.play_stream(TEST_STREAM_URL, TEST_STREAM_NAME)

    def play_station(self, station: Station) -> None:
        self.play_stream(
            station.stream_url,
            station.name,
            station_uuid=station.stationuuid,
        )

    def play_stream(
        self,
        url: str,
        name: str,
        *,
        station_uuid: str | None = None,
    ) -> None:
        self.state.stream_url = url
        self.state.station_name = name
        self.state.station_uuid = station_uuid
        self.state.is_playing = True
        self.state.error = None
        self.state.track_title = None
        self.state.track_meta = None
        if station_uuid:
            self.settings.last_station_uuid = station_uuid
        self._notify(source="play")

        def work() -> None:
            try:
                self._backend.play(url)
            except Exception as exc:
                logger.exception("Error al reproducir")
                self.state.error = str(exc)
                self.state.is_playing = False
                self._notify(source="error")

        self._submit(work)

    def toggle_pause(self) -> None:
        if not self.state.stream_url:
            return
        target_playing = not self.state.is_playing
        self.state.is_playing = target_playing
        self._notify(source="pause")

        def work() -> None:
            if target_playing:
                self._backend.resume()
            else:
                self._backend.pause()

        self._submit(work)

    def stop(self) -> None:
        def work() -> None:
            self._backend.stop()
            self.state.is_playing = False
            self.state.track_title = None
            self.state.track_meta = None
            self._notify(source="stop")

        self.state.is_playing = False
        self.state.track_title = None
        self.state.track_meta = None
        self._notify(source="stop")
        self._submit(work)

    def adjust_volume(self, delta: int) -> None:
        new_volume = max(0, min(100, self.state.volume + delta))
        self.set_volume(new_volume)

    def set_volume(self, level: int) -> None:
        level = max(0, min(100, level))
        self.state.volume = level
        self.settings.volume = level
        self._notify(source="volume")

        def work() -> None:
            self._backend.set_volume(level)

        self._submit(work)

    def shutdown(self) -> None:
        """Cierra mpv; preferir desde el hilo de audio (ver PlayerService)."""
        if self._closing:
            return
        self._closing = True

        done = threading.Event()

        def work() -> None:
            try:
                self._backend.shutdown()
            except Exception:
                logger.exception("Error al cerrar backend de audio")
            finally:
                done.set()

        self._work_queue.put(work)
        if not done.wait(timeout=5.0):
            logger.warning("Timeout cerrando mpv; forzando kill")
            try:
                self._backend.shutdown()
            except Exception:
                logger.exception("Error al forzar cierre de mpv")

        try:
            self._work_queue.put_nowait(None)
        except queue.Full:
            pass
        self._worker.join(timeout=2.0)

    def _submit(self, work: Callable[[], None]) -> None:
        if self._closing:
            return
        self._work_queue.put(work)

    def _worker_loop(self) -> None:
        while True:
            item = self._work_queue.get()
            if item is None:
                break
            try:
                item()
            except Exception:
                logger.exception("Error en hilo de audio")

    def _on_metadata(self, title: str | None) -> None:
        if title == self.state.track_title:
            return
        self.state.track_title = title
        self.state.track_meta = None
        self._notify(source="metadata")

    def set_track_meta(self, meta: TrackMeta | None) -> None:
        if meta == self.state.track_meta:
            return
        self.state.track_meta = meta
        self._notify(source="metadata_enriched")

    def _notify(self, *, source: str = "other") -> None:
        perf.count(f"player.notify.{source}")
        snapshot = self.state.model_copy()
        for listener in self._listeners:
            try:
                listener(snapshot)
            except Exception:
                logger.exception("Error en listener de estado")


def create_player_service(settings: AppSettings) -> PlayerService:
    try:
        return PlayerService(settings)
    except MpvNotFoundError:
        raise
