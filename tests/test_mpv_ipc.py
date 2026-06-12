"""Tests del cliente IPC persistente de mpv."""

from __future__ import annotations

import json
import queue

from terminal_radio.audio.mpv_ipc import MpvIpcClient, send_command


def test_property_change_dispatches_to_handler() -> None:
  events = queue.Queue()

  lines = [
    json.dumps(
      {"event": "property-change", "name": "media-title", "data": "Track A"}
    ).encode("utf-8")
    + b"\n",
    b"",
  ]

  class Reader:
    def __init__(self) -> None:
      self._lines = list(lines)

    def readline(self) -> bytes:
      return self._lines.pop(0) if self._lines else b""

  client = MpvIpcClient("dummy")
  client.on_property_change(lambda name, data: events.put((name, data)))
  client._stream = Reader()  # type: ignore[assignment]
  client._stop.clear()
  client._read_loop()

  name, data = events.get(timeout=1.0)
  assert name == "media-title"
  assert data == "Track A"


def test_command_async_does_not_require_response() -> None:
  written: list[bytes] = []

  class Writer:
    def write(self, data: bytes) -> int:
      written.append(data)
      return len(data)

    def flush(self) -> None:
      pass

    def close(self) -> None:
      pass

    def readline(self) -> bytes:
      return b""

  client = MpvIpcClient("dummy")
  client._stream = Writer()  # type: ignore[assignment]
  client.command_async(["set_property", "volume", 50])
  assert written
  payload = json.loads(written[0].decode("utf-8").strip())
  assert payload["command"] == ["set_property", "volume", 50]
  assert "request_id" not in payload


def test_send_command_uses_ephemeral_client(monkeypatch) -> None:
  calls: list[tuple[str, list, bool]] = []

  class FakeClient:
    def __init__(self, endpoint: str) -> None:
      self.endpoint = endpoint

    def connect(self) -> bool:
      return True

    def command(self, cmd: list, *, timeout: float = 2.0) -> dict:
      calls.append((self.endpoint, cmd, True))
      return {"error": "success"}

    def close(self) -> None:
      pass

  monkeypatch.setattr("terminal_radio.audio.mpv_ipc.MpvIpcClient", FakeClient)
  result = send_command("pipe", ["loadfile", "http://x", "replace"], timeout=3.0)
  assert result == {"error": "success"}
  assert calls == [("pipe", ["loadfile", "http://x", "replace"], True)]
