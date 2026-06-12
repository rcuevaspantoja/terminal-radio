"""Tests del launcher global."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from terminal_radio.platform import launcher


def test_save_and_load_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(launcher, "get_config_dir", lambda: tmp_path)
    python = tmp_path / "venv" / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.write_bytes(b"")

    launcher.save_runtime(python, tmp_path / "venv")
    loaded = launcher.load_runtime_python()
    assert loaded == python.resolve()

    data = json.loads((tmp_path / "runtime.json").read_text(encoding="utf-8"))
    assert data["python"] == str(python.resolve())


def test_install_cli_shims_unix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(launcher, "get_config_dir", lambda: tmp_path / "config")
    monkeypatch.setattr(launcher, "get_local_bin_dir", lambda: tmp_path / "bin")
    monkeypatch.setattr(launcher, "ensure_local_bin_on_path", lambda: False)

    python = tmp_path / "venv" / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.write_bytes(b"")

    created, path_modified = launcher.install_cli_shims(python, tmp_path / "venv")
    assert (tmp_path / "bin" / "radio").is_file()
    assert (tmp_path / "bin" / "terminal-radio").is_file()
    assert 'exec "' in (tmp_path / "bin" / "radio").read_text(encoding="utf-8")
    assert len(created) == 2
    assert path_modified is False


def test_install_cli_shims_windows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(launcher, "get_config_dir", lambda: tmp_path / "config")
    monkeypatch.setattr(launcher, "get_local_bin_dir", lambda: tmp_path / "bin")
    monkeypatch.setattr(launcher, "ensure_local_bin_on_path", lambda: True)

    python = tmp_path / "python.exe"
    python.write_bytes(b"")

    created, path_modified = launcher.install_cli_shims(python)
    assert (tmp_path / "bin" / "radio.cmd").is_file()
    assert (tmp_path / "bin" / "terminal-radio.cmd").is_file()
    assert "@echo off" in (tmp_path / "bin" / "radio.cmd").read_text(encoding="utf-8")
    assert path_modified is True


def test_ensure_local_bin_on_path_windows_adds_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    bin_dir = tmp_path / "bin"
    monkeypatch.setattr(launcher, "get_local_bin_dir", lambda: bin_dir)
    monkeypatch.setattr(launcher, "_user_path_entries_windows", lambda: ["C:\\Windows"])

    mock_key = MagicMock()
    mock_winreg = MagicMock()
    mock_winreg.HKEY_CURRENT_USER = 1
    mock_winreg.KEY_READ = 2
    mock_winreg.KEY_WRITE = 4
    mock_winreg.REG_EXPAND_SZ = 5
    mock_winreg.OpenKey.return_value.__enter__.return_value = mock_key
    mock_winreg.QueryValueEx.return_value = ("C:\\Windows", 1)
    monkeypatch.setitem(sys.modules, "winreg", mock_winreg)

    assert launcher.ensure_local_bin_on_path() is True
    mock_winreg.SetValueEx.assert_called_once()
    new_path_value = mock_winreg.SetValueEx.call_args[0][4]
    assert str(bin_dir) in new_path_value


def test_ensure_local_bin_on_path_windows_skips_if_present(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    bin_dir = tmp_path / "bin"
    monkeypatch.setattr(launcher, "get_local_bin_dir", lambda: bin_dir)
    monkeypatch.setattr(launcher, "_user_path_entries_windows", lambda: [str(bin_dir)])

    assert launcher.ensure_local_bin_on_path() is False


def test_discover_python_from_runtime(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(launcher, "get_config_dir", lambda: tmp_path)
    python = tmp_path / "python"
    python.write_bytes(b"")
    launcher.save_runtime(python)
    assert launcher.discover_python() == python.resolve()
