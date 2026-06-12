"""Tests del endpoint IPC de mpv."""

from __future__ import annotations

import os
import sys

from terminal_radio.audio.backend import get_ipc_endpoint, get_ipc_endpoint_for_pid


def test_windows_ipc_endpoint_is_unique_per_pid(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(os, "getpid", lambda: 4242)
    assert get_ipc_endpoint() == r"\\.\pipe\terminal-radio-mpv-4242"
    assert get_ipc_endpoint_for_pid(99) == r"\\.\pipe\terminal-radio-mpv-99"


def test_unix_ipc_endpoint_is_fixed(monkeypatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    assert get_ipc_endpoint() == "/tmp/terminal-radio-mpv.sock"
