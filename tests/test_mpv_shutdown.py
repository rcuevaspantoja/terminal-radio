"""Tests de cierre de mpv y prevención de procesos huérfanos."""

from __future__ import annotations

import subprocess
import sys
from unittest.mock import MagicMock

import pytest

from terminal_radio.audio import mpv_subprocess


def test_spawn_skipped_after_shutdown(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mpv_subprocess, "find_mpv_binary", lambda: r"C:\mpv\mpv.exe")
    popen = MagicMock()
    monkeypatch.setattr(subprocess, "Popen", popen)

    backend = mpv_subprocess.MpvSubprocessBackend(volume=50)
    backend.shutdown()
    backend.play("https://example.com/stream.mp3")

    popen.assert_not_called()


def test_shutdown_kills_tracked_process(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mpv_subprocess, "find_mpv_binary", lambda: r"C:\mpv\mpv.exe")
    proc = MagicMock()
    proc.poll.return_value = None
    proc.pid = 4242

    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: proc)
    taskkill = MagicMock()
    monkeypatch.setattr(mpv_subprocess.MpvSubprocessBackend, "_taskkill_pid", taskkill)

    backend = mpv_subprocess.MpvSubprocessBackend(volume=50)
    backend.play("https://example.com/stream.mp3")
    backend.shutdown()

    proc.kill.assert_called_once()
    if sys.platform == "win32":
        taskkill.assert_called_with(4242)
