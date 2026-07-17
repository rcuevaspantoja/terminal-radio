"""Tests de detección de plataforma."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from terminal_radio.platform import detect


def test_get_config_dir_linux(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(Path, "home", staticmethod(lambda: Path("/home/testuser")))
    assert detect.get_config_dir() == Path("/home/testuser/.config/terminal-radio")


def test_get_config_dir_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", r"C:\Users\test\AppData\Roaming")
    assert detect.get_config_dir() == Path(r"C:\Users\test\AppData\Roaming\terminal-radio")
