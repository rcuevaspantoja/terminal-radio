"""Cliente IPC JSON persistente para mpv (evita abrir pipe/socket por comando)."""

from __future__ import annotations

import json
import logging
import queue
import socket
import sys
import threading
import time
from collections.abc import Callable
from typing import Any, BinaryIO

from terminal_radio.debug.perf import perf

logger = logging.getLogger(__name__)

PropertyHandler = Callable[[str, Any], None]

# Windows: mpv acepta un cliente IPC a la vez; serializar conexiones cortas.
_ENDPOINT_LOCKS: dict[str, threading.Lock] = {}
_ENDPOINT_LOCKS_GUARD = threading.Lock()


def _endpoint_lock(endpoint: str) -> threading.Lock:
    with _ENDPOINT_LOCKS_GUARD:
        lock = _ENDPOINT_LOCKS.get(endpoint)
        if lock is None:
            lock = threading.Lock()
            _ENDPOINT_LOCKS[endpoint] = lock
        return lock


class MpvIpcClient:
    """Una conexión persistente: comandos + eventos property-change."""

    def __init__(self, endpoint: str) -> None:
        self._endpoint = endpoint
        self._stream: BinaryIO | None = None
        self._socket: socket.socket | None = None
        self._send_lock = threading.Lock()
        self._request_id = 0
        self._pending: dict[int, queue.Queue[dict | None]] = {}
        self._reader_thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._property_handlers: list[PropertyHandler] = []

    def on_property_change(self, handler: PropertyHandler) -> None:
        self._property_handlers.append(handler)

    def connect(self) -> bool:
        """Abre la conexión e inicia el hilo lector."""
        self.close()
        try:
            if sys.platform == "win32":
                self._stream = open(self._endpoint, "r+b", buffering=0)  # noqa: SIM115
            else:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.settimeout(5.0)
                sock.connect(self._endpoint)
                self._socket = sock
                self._stream = sock.makefile("rwb", buffering=0)
        except OSError as exc:
            logger.debug("No se pudo conectar IPC mpv: %s", exc)
            self.close()
            return False

        if sys.platform != "win32":
            self._stop.clear()
            self._reader_thread = threading.Thread(
                target=self._read_loop,
                name="mpv-ipc-reader",
                daemon=True,
            )
            self._reader_thread.start()
        return True

    def close(self) -> None:
        self._stop.set()
        stream = self._stream
        sock = self._socket
        self._stream = None
        self._socket = None
        if stream is not None:
            try:
                stream.close()
            except OSError:
                pass
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass
        for pending in self._pending.values():
            pending.put(None)
        self._pending.clear()
        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=0.3)
        self._reader_thread = None

    @property
    def is_connected(self) -> bool:
        return self._stream is not None

    def command(self, cmd: list[Any], *, timeout: float = 2.0) -> dict | None:
        """Envía comando y espera respuesta."""
        if sys.platform == "win32":
            return self._command_inline(cmd, timeout=timeout)
        return self._command_sync(cmd, timeout=timeout)

    def command_async(self, cmd: list[Any]) -> None:
        """Fire-and-forget: no bloquea esperando respuesta (crítico en Windows)."""
        if not self.is_connected:
            return
        cmd_name = str(cmd[0]) if cmd else "unknown"
        perf.count(f"ipc.async.{cmd_name}")
        with self._send_lock:
            if self._stream is None:
                return
            payload = json.dumps({"command": cmd}) + "\n"
            try:
                self._stream.write(payload.encode("utf-8"))
                self._stream.flush()
            except OSError as exc:
                logger.debug("Envío IPC async falló: %s", exc)

    def observe_property(self, name: str, reply_id: int) -> None:
        self._command_sync(["observe_property", reply_id, name])

    def _command_inline(self, cmd: list[Any], *, timeout: float = 2.0) -> dict | None:
        """Windows: lectura síncrona (readline en hilo aparte no es fiable en pipes)."""
        stream = self._stream
        if stream is None:
            return None
        cmd_name = str(cmd[0]) if cmd else "unknown"
        started = time.perf_counter() if perf.enabled else 0.0
        with self._send_lock:
            if self._stream is None:
                return None
            self._request_id += 1
            request_id = self._request_id
            payload = json.dumps({"command": cmd, "request_id": request_id}) + "\n"
            try:
                stream.write(payload.encode("utf-8"))
                stream.flush()
            except OSError as exc:
                logger.debug("Envío IPC mpv falló: %s", exc)
                return None
        deadline = time.monotonic() + timeout
        buffer = b""
        while time.monotonic() < deadline:
            try:
                chunk = stream.read(1)
            except (OSError, ValueError):
                break
            if not chunk:
                time.sleep(0.005)
                continue
            buffer += chunk
            if chunk != b"\n":
                continue
            try:
                message = json.loads(buffer.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                buffer = b""
                continue
            buffer = b""
            if message.get("request_id") == request_id:
                if perf.enabled:
                    perf.record_ms(
                        f"ipc.{cmd_name}",
                        (time.perf_counter() - started) * 1000,
                    )
                    perf.count("ipc.command")
                return message
        if perf.enabled:
            perf.record_ms(f"ipc.{cmd_name}", (time.perf_counter() - started) * 1000)
            perf.count("ipc.timeout")
        return None

    def _command_sync(self, cmd: list[Any], *, timeout: float = 2.0) -> dict | None:
        if not self.is_connected:
            return None
        cmd_name = str(cmd[0]) if cmd else "unknown"
        started = time.perf_counter() if perf.enabled else 0.0
        with self._send_lock:
            if self._stream is None:
                return None
            self._request_id += 1
            request_id = self._request_id
            response_queue: queue.Queue[dict | None] = queue.Queue(maxsize=1)
            self._pending[request_id] = response_queue
            payload = json.dumps({"command": cmd, "request_id": request_id}) + "\n"
            try:
                self._stream.write(payload.encode("utf-8"))
                self._stream.flush()
            except OSError as exc:
                logger.debug("Envío IPC mpv falló: %s", exc)
                self._pending.pop(request_id, None)
                return None
        try:
            message = response_queue.get(timeout=timeout)
        except queue.Empty:
            self._pending.pop(request_id, None)
            if perf.enabled:
                perf.record_ms(f"ipc.{cmd_name}", (time.perf_counter() - started) * 1000)
                perf.count("ipc.timeout")
            return None
        if perf.enabled:
            perf.record_ms(f"ipc.{cmd_name}", (time.perf_counter() - started) * 1000)
            perf.count("ipc.command")
        return message

    def _read_loop(self) -> None:
        stream = self._stream
        if stream is None:
            return
        while not self._stop.is_set():
            try:
                line = stream.readline()
            except (OSError, ValueError):
                break
            if not line:
                break
            try:
                message = json.loads(line.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue

            event = message.get("event")
            if event == "property-change":
                prop_name = message.get("name")
                if prop_name:
                    data = message.get("data")
                    for handler in self._property_handlers:
                        try:
                            handler(prop_name, data)
                        except Exception:
                            logger.exception("Error en handler de propiedad mpv")
                continue

            request_id = message.get("request_id")
            if request_id is not None:
                pending = self._pending.pop(request_id, None)
                if pending is not None:
                    pending.put(message)


def send_command(
    endpoint: str,
    cmd: list[Any],
    *,
    timeout: float = 2.0,
    wait_response: bool = True,
    lock_timeout: float | None = None,
) -> dict | None:
    """Conexión corta al IPC de mpv (más fiable que persistente en Windows)."""
    lock = _endpoint_lock(endpoint) if sys.platform == "win32" else None
    if lock is not None:
        acquired = lock.acquire(timeout=lock_timeout if lock_timeout is not None else timeout + 2.0)
        if not acquired:
            perf.count("ipc.lock_timeout")
            return None
    try:
        client = MpvIpcClient(endpoint)
        if not client.connect():
            perf.count("ipc.connect_failed")
            return None
        try:
            if wait_response:
                return client.command(cmd, timeout=timeout)
            client.command_async(cmd)
            return {"error": "success"}
        finally:
            client.close()
    finally:
        if lock is not None:
            lock.release()
