"""Tests for bundled / frozen install paths."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from terminal_radio.platform import bundle


def test_is_frozen_false_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert bundle.is_frozen() is False
    assert bundle.install_dir() is None


def test_bundled_mpv_windows_when_frozen(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    exe = tmp_path / "radio.exe"
    exe.write_bytes(b"")
    monkeypatch.setattr(sys, "executable", str(exe), raising=False)

    mpv = tmp_path / "mpv" / "mpv.exe"
    mpv.parent.mkdir(parents=True)
    mpv.write_bytes(b"")

    assert bundle.bundled_mpv_windows() == mpv.resolve()


def test_find_mpv_prefers_bundled_on_windows(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    from terminal_radio.platform import deps

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    exe = tmp_path / "radio.exe"
    exe.write_bytes(b"")
    monkeypatch.setattr(sys, "executable", str(exe), raising=False)

    mpv = tmp_path / "mpv" / "mpv.exe"
    mpv.parent.mkdir(parents=True)
    mpv.write_bytes(b"")

    monkeypatch.setattr(deps, "_verify_mpv_cli", lambda path: path.is_file())
    monkeypatch.setattr(deps, "_windows_mpv_search_paths", lambda: [])
    assert deps.find_mpv_binary() == str(mpv.resolve())
