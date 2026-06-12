"""Interfaz de audio y factory con detección de plataforma."""

from __future__ import annotations

import os
import sys
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import TYPE_CHECKING

from terminal_radio.debug.perf import perf
from terminal_radio.platform.deps import find_mpv_binary  # re-exported
from terminal_radio.platform.detect import is_termux

__all__ = [
    "AudioBackend",
    "MpvNotFoundError",
    "create_audio_backend",
    "find_mpv_binary",
    "get_ipc_endpoint",
]

if TYPE_CHECKING:
    from terminal_radio.audio.mpv_binding import MpvBindingBackend
    from terminal_radio.audio.mpv_subprocess import MpvSubprocessBackend

MetadataCallback = Callable[[str | None], None]

IPC_SOCKET_UNIX = "/tmp/terminal-radio-mpv.sock"
IPC_PIPE_WINDOWS = r"\\.\pipe\terminal-radio-mpv"


class MpvNotFoundError(RuntimeError):
    """mpv no está instalado o no está en PATH."""

    def __init__(self) -> None:
        if is_termux():
            hint = "pkg install mpv"
        elif sys.platform == "win32":
            hint = "scoop bucket add extras && scoop install mpv"
        else:
            hint = "sudo apt install mpv  (or your distro equivalent)"
        super().__init__(f"mpv not found in PATH. Install with: {hint}")


class AudioBackend(ABC):
    """Contrato congelado para todos los backends de reproducción."""

    @abstractmethod
    def play(self, url: str) -> None:
        """Inicia o cambia el stream activo."""

    @abstractmethod
    def stop(self) -> None:
        """Detiene la reproducción."""

    @abstractmethod
    def pause(self) -> None:
        """Pausa el stream si el backend lo permite."""

    @abstractmethod
    def resume(self) -> None:
        """Reanuda tras una pausa."""

    @abstractmethod
    def set_volume(self, level: int) -> None:
        """Establece volumen 0–100."""

    @abstractmethod
    def get_volume(self) -> int:
        """Devuelve volumen actual 0–100."""

    @property
    @abstractmethod
    def is_playing(self) -> bool:
        """True si hay reproducción activa (no pausada)."""

    @abstractmethod
    def on_metadata(self, callback: MetadataCallback) -> None:
        """Registra listener para cambios de media-title (ICY)."""

    @abstractmethod
    def shutdown(self) -> None:
        """Libera procesos, sockets y threads."""


def get_ipc_endpoint() -> str:
    if sys.platform == "win32":
        # Pipe único por proceso: evita pipes zombis y bloqueos entre sesiones.
        return f"{IPC_PIPE_WINDOWS}-{os.getpid()}"
    return IPC_SOCKET_UNIX


def get_ipc_endpoint_for_pid(pid: int) -> str:
    if sys.platform == "win32":
        return f"{IPC_PIPE_WINDOWS}-{pid}"
    return IPC_SOCKET_UNIX


def _mpv_binding_enabled(prefer_binding: bool) -> bool:
    """Windows/Termux usan subprocess por defecto (mpv aislado de la TUI)."""
    if not prefer_binding:
        return False
    if os.environ.get("TERMINAL_RADIO_MPV_BINDING", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }:
        return True
    if is_termux() or sys.platform == "win32":
        return False
    return True


def _register_backend(backend: AudioBackend) -> AudioBackend:
    perf.note("audio_backend", type(backend).__name__)
    return backend


def create_audio_backend(
    volume: int = 50,
    *,
    prefer_binding: bool = True,
) -> AudioBackend:
    """
    Crea el backend adecuado para la plataforma actual.

    Termux / Windows → subprocess (mpv en proceso aparte).
    Linux/macOS → python-mpv si está disponible, si no subprocess.
    """
    if find_mpv_binary() is None:
        raise MpvNotFoundError()

    from terminal_radio.audio.mpv_subprocess import MpvSubprocessBackend

    if is_termux() or sys.platform == "win32":
        if not _mpv_binding_enabled(prefer_binding):
            return _register_backend(MpvSubprocessBackend(volume=volume))

    if _mpv_binding_enabled(prefer_binding):
        try:
            from terminal_radio.audio.mpv_binding import MpvBindingBackend

            return _register_backend(MpvBindingBackend(volume=volume))
        except (ImportError, OSError, RuntimeError):
            pass

    return _register_backend(MpvSubprocessBackend(volume=volume))
