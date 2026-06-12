"""Backend de audio vía proceso mpv e IPC JSON."""

from __future__ import annotations

import atexit
import logging
import os
import subprocess
import sys
import threading
import time
import weakref
from collections.abc import Callable
from pathlib import Path
from typing import Any

from terminal_radio.audio.backend import (
    AudioBackend,
    MetadataCallback,
    find_mpv_binary,
    get_ipc_endpoint,
)
from terminal_radio.audio.mpv_ipc import MpvIpcClient, send_command
from terminal_radio.audio.mpv_options import get_mpv_stream_cli_args
from terminal_radio.debug.perf import perf

logger = logging.getLogger(__name__)

_IPC_CONNECT_RETRIES = 30
_IPC_CONNECT_DELAY = 0.1
_SHUTDOWN_PROCESS_TIMEOUT = 0.5
_MEDIA_TITLE_OBSERVE_ID = 1
_METADATA_MIN_INTERVAL = 1.0 if sys.platform == "win32" else 0.5

_ACTIVE_BACKENDS: weakref.WeakSet[MpvSubprocessBackend] = weakref.WeakSet()

# Windows: prioridad baja para mpv → menos competencia con Textual.
_WIN_CREATION_FLAGS = 0
if sys.platform == "win32":
    _WIN_CREATION_FLAGS = (
        subprocess.BELOW_NORMAL_PRIORITY_CLASS  # type: ignore[attr-defined]
        | getattr(subprocess, "CREATE_NO_WINDOW", 0)
    )


def _shutdown_active_backends() -> None:
    for backend in list(_ACTIVE_BACKENDS):
        try:
            backend.shutdown()
        except Exception:
            logger.exception("Error en atexit de mpv")


atexit.register(_shutdown_active_backends)


class MpvSubprocessBackend(AudioBackend):
    """Controla mpv como subproceso; IPC persistente por socket o named pipe."""

    def __init__(self, volume: int = 50) -> None:
        self._volume = max(0, min(100, volume))
        self._playing = False
        self._paused = False
        self._current_url: str | None = None
        self._process: subprocess.Popen[bytes] | None = None
        self._metadata_callbacks: list[MetadataCallback] = []
        self._last_title: str | None = None
        self._last_metadata_emit = 0.0
        self._ipc: MpvIpcClient | None = None
        self._ipc_endpoint = get_ipc_endpoint()
        self._mpv_binary = find_mpv_binary()
        self._shut_down = False
        self._mpv_pid: int | None = None
        if self._mpv_binary is None:
            raise RuntimeError("mpv binary missing")
        logger.info("Motor de audio: %s", self._mpv_binary)
        _ACTIVE_BACKENDS.add(self)
        self._metadata_poller_thread: threading.Thread | None = None

    def play(self, url: str) -> None:
        if self._process is not None and self._process.poll() is None:
            if url != self._current_url and sys.platform == "win32":
                if not self._try_loadfile(url):
                    logger.info("loadfile falló; reiniciando mpv para %s", url)
                    self._spawn(url)
                    return
            else:
                self._ipc_command(["loadfile", url, "replace"])
            self._current_url = url
            self._playing = True
            self._paused = False
            return
        self._spawn(url)

    def stop(self) -> None:
        if self._process is None or self._process.poll() is not None:
            self._playing = False
            self._paused = False
            self._current_url = None
            return
        self._ipc_command(["stop"])
        self._playing = False
        self._paused = False
        self._current_url = None

    def pause(self) -> None:
        if not self._process or self._process.poll() is not None:
            return
        self._ipc_command(["set_property", "pause", True])
        self._paused = True

    def resume(self) -> None:
        if not self._process or self._process.poll() is not None:
            return
        self._ipc_command(["set_property", "pause", False])
        self._paused = False

    def set_volume(self, level: int) -> None:
        self._volume = max(0, min(100, level))
        if self._process and self._process.poll() is None:
            self._ipc_command(["set_property", "volume", self._volume])

    def get_volume(self) -> int:
        return self._volume

    @property
    def is_playing(self) -> bool:
        return self._playing and not self._paused

    def on_metadata(self, callback: MetadataCallback) -> None:
        self._metadata_callbacks.append(callback)

    def shutdown(self) -> None:
        if self._shut_down:
            return
        self._shut_down = True

        process = self._process
        pid = self._mpv_pid
        self._process = None
        self._mpv_pid = None

        if self._ipc is not None:
            self._ipc.close()
            self._ipc = None

        self._force_kill(process, pid)
        self._clear_pid_file()
        self._playing = False
        self._paused = False
        self._cleanup_ipc_endpoint()

    def _spawn(self, url: str) -> None:
        self.shutdown()
        self._shut_down = False
        self._cleanup_ipc_endpoint()

        args = [
            self._mpv_binary,
            *get_mpv_stream_cli_args(),
            "--really-quiet",
            f"--input-ipc-server={self._ipc_endpoint}",
            f"--volume={self._volume}",
            url,
        ]
        stderr_target = subprocess.DEVNULL
        if perf.enabled:
            stderr_target = perf.mpv_stderr_target()
        popen_kwargs: dict = {
            "stdout": subprocess.DEVNULL,
            "stderr": stderr_target,
        }
        if _WIN_CREATION_FLAGS:
            popen_kwargs["creationflags"] = _WIN_CREATION_FLAGS
        self._process = subprocess.Popen(args, **popen_kwargs)
        self._mpv_pid = self._process.pid
        self._write_pid_file(self._mpv_pid)
        self._current_url = url
        self._playing = True
        self._paused = False

        if sys.platform == "win32":
            # El stream ya va en argv; no bloquear el hilo de audio esperando IPC.
            self._start_metadata_poller()
            return

        if not self._wait_for_ipc():
            self._playing = False
            raise RuntimeError("No se pudo conectar al IPC de mpv")

        assert self._ipc is not None
        self._ipc.on_property_change(self._on_mpv_property_change)
        self._ipc.observe_property("media-title", _MEDIA_TITLE_OBSERVE_ID)

    def _wait_for_ipc(self) -> bool:
        if sys.platform == "win32":
            for _ in range(_IPC_CONNECT_RETRIES):
                if self._process and self._process.poll() is not None:
                    return False
                response = send_command(
                    self._ipc_endpoint,
                    ["get_property", "idle-active"],
                    timeout=1.5,
                )
                if response is not None:
                    return True
                time.sleep(_IPC_CONNECT_DELAY)
            return False

        self._ipc = MpvIpcClient(self._ipc_endpoint)
        for _ in range(_IPC_CONNECT_RETRIES):
            if self._process and self._process.poll() is not None:
                self._ipc.close()
                self._ipc = None
                return False
            if self._ipc.connect():
                response = self._ipc._command_sync(
                    ["get_property", "idle-active"],
                    timeout=1.0,
                )
                if response is not None:
                    return True
                self._ipc.close()
            time.sleep(_IPC_CONNECT_DELAY)
        self._ipc = None
        return False

    def _start_metadata_poller(self) -> None:
        if self._metadata_poller_thread and self._metadata_poller_thread.is_alive():
            return
        self._metadata_poller_thread = threading.Thread(
            target=self._metadata_poll_loop,
            name="mpv-metadata-poll",
            daemon=True,
        )
        self._metadata_poller_thread.start()

    def _metadata_poll_loop(self) -> None:
        while not self._shut_down:
            if self._process is None or self._process.poll() is not None:
                time.sleep(0.5)
                continue
            response = send_command(
                self._ipc_endpoint,
                ["get_property", "media-title"],
                timeout=1.5,
                lock_timeout=0.05,
            )
            if response is not None and "data" in response:
                self._emit_metadata("media-title", response["data"])
            time.sleep(_METADATA_MIN_INTERVAL)

    def _on_mpv_property_change(self, name: str, data: Any) -> None:
        self._emit_metadata(name, data)

    def _emit_metadata(self, name: str, data: Any) -> None:
        if name != "media-title":
            return
        perf.count("ipc.property_change")
        title = str(data) if data else None
        if title == self._last_title:
            return
        now = time.monotonic()
        if now - self._last_metadata_emit < _METADATA_MIN_INTERVAL:
            self._last_title = title
            return
        self._last_title = title
        self._last_metadata_emit = now
        for callback in self._metadata_callbacks:
            try:
                callback(title)
            except Exception:
                logger.exception("Error en callback de metadata")

    def _try_loadfile(self, url: str) -> bool:
        response = send_command(
            self._ipc_endpoint,
            ["loadfile", url, "replace"],
            timeout=8.0,
        )
        return self._ipc_response_ok(response)

    def _ipc_command(self, command: list) -> None:
        """Envía comando IPC desde el hilo player-audio (no bloquea la TUI)."""
        if self._shut_down:
            return
        cmd = command[0] if command else ""
        timeout = 8.0 if cmd == "loadfile" else 2.0

        if sys.platform == "win32":
            response = send_command(
                self._ipc_endpoint,
                command,
                timeout=timeout,
                wait_response=True,
            )
            if not self._ipc_response_ok(response):
                logger.warning("Comando mpv falló: %s → %s", command, response)
            return

        if self._ipc is not None and self._ipc.is_connected:
            response = self._ipc.command(command, timeout=timeout)
            if not self._ipc_response_ok(response):
                logger.warning("Comando mpv falló: %s → %s", command, response)

    @staticmethod
    def _ipc_response_ok(response: dict | None) -> bool:
        if response is None:
            return False
        error = response.get("error")
        return error in (None, "success")

    @staticmethod
    def _pid_file_path() -> Path:
        from terminal_radio.platform.detect import get_config_dir

        return get_config_dir() / "mpv.pid"

    def _write_pid_file(self, pid: int) -> None:
        try:
            path = self._pid_file_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(str(pid), encoding="utf-8")
        except OSError:
            pass

    def _clear_pid_file(self) -> None:
        try:
            self._pid_file_path().unlink(missing_ok=True)
        except OSError:
            pass

    @classmethod
    def cleanup_stale_process(cls) -> None:
        """Mata mpv huérfano de una sesión anterior (p. ej. terminal cerrada a la fuerza)."""
        path = cls._pid_file_path()
        if not path.is_file():
            return
        try:
            pid = int(path.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            path.unlink(missing_ok=True)
            return
        cls._force_kill(None, pid)
        path.unlink(missing_ok=True)

    @classmethod
    def force_kill_tracked(cls) -> None:
        """Mata mpv registrado (pid file + backends activos)."""
        for backend in list(_ACTIVE_BACKENDS):
            try:
                backend.shutdown()
            except Exception:
                logger.exception("Error al cerrar backend activo")
        cls.cleanup_stale_process()

    @staticmethod
    def _force_kill(
        process: subprocess.Popen[bytes] | None,
        pid: int | None,
    ) -> None:
        if process is not None and process.poll() is None:
            try:
                process.kill()
                process.wait(timeout=0.5)
            except (OSError, subprocess.TimeoutExpired):
                logger.debug("mpv no respondió a kill()")
        if pid is not None and sys.platform == "win32":
            MpvSubprocessBackend._taskkill_pid(pid)

    @staticmethod
    def _taskkill_pid(pid: int) -> None:
        try:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/F", "/T"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2.0,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.TimeoutExpired):
            pass

    def _cleanup_ipc_endpoint(self) -> None:
        if sys.platform == "win32":
            return
        try:
            if os.path.exists(self._ipc_endpoint):
                os.remove(self._ipc_endpoint)
        except OSError:
            pass
