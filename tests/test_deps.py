"""Tests de detección de dependencias e instalación de mpv."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from terminal_radio.platform import deps


def test_mpv_available_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(deps, "find_mpv_binary", lambda: r"C:\tools\mpv.exe")
    assert deps.mpv_available() is True


def test_find_mpv_binary_windows_scoop_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(deps.shutil, "which", lambda _: None)
    scoop_mpv = tmp_path / "scoop" / "shims" / "mpv.exe"
    scoop_mpv.parent.mkdir(parents=True)
    scoop_mpv.write_bytes(b"")

    monkeypatch.setattr(deps.Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.setattr(deps, "_verify_mpv_cli", lambda path: path.is_file())
    assert deps.find_mpv_binary() == str(scoop_mpv.resolve())


def test_mpv_install_steps_termux(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(deps, "is_termux", lambda: True)
    steps = deps.mpv_install_steps()
    assert len(steps) == 1
    assert steps[0].command[:3] == ["pkg", "install", "-y"]


def test_mpv_install_steps_windows_prefers_scoop(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(deps, "is_termux", lambda: False)

    def which(cmd: str):
        if cmd in ("scoop", "winget"):
            return f"/usr/bin/{cmd}"
        return None

    monkeypatch.setattr(deps.shutil, "which", which)
    steps = deps.mpv_install_steps()
    assert steps[0].command[0] == "scoop"
    assert steps[1].command[:2] == ["scoop", "install"]
    assert not any("shinchiro.mpv" in " ".join(s.command) for s in steps)


def test_mpv_install_steps_linux_debian(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(deps, "is_termux", lambda: False)
    monkeypatch.setattr(deps, "detect_linux_family", lambda: deps.LinuxFamily.DEBIAN)
    monkeypatch.setattr(deps.shutil, "which", lambda cmd: "/usr/bin/snap" if cmd == "snap" else None)
    steps = deps.mpv_install_steps()
    assert steps[0].command[1] == "apt-get"
    assert steps[0].command[2] == "update"
    assert any("snap" in s.command for s in steps)


def test_find_mpv_binary_linux_snap_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(deps.shutil, "which", lambda _: None)
    snap_mpv = tmp_path / "mpv"
    snap_mpv.write_bytes(b"")

    def fake_path(path_str: str):
        if path_str == "/snap/bin/mpv":
            return snap_mpv
        return Path(path_str)

    original_path = deps.Path

    class PatchedPath(type(original_path)):
        def __new__(cls, *args, **kwargs):
            if args and args[0] == "/snap/bin/mpv":
                return snap_mpv
            return original_path(*args, **kwargs)

    # Simpler: patch _linux_known_paths
    monkeypatch.setattr(deps, "_linux_known_paths", lambda: [snap_mpv])
    monkeypatch.setattr(deps, "_verify_mpv_cli", lambda path: path.is_file())
    assert deps.find_mpv_binary() == str(snap_mpv.resolve())


def test_find_mpv_binary_rejects_mpv_player_gui(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(deps.shutil, "which", lambda _: None)
    gui = tmp_path / "MPV Player" / "mpv.exe"
    gui.parent.mkdir(parents=True)
    gui.write_bytes(b"")
    scoop = tmp_path / "scoop" / "apps" / "mpv" / "current" / "mpv.exe"
    scoop.parent.mkdir(parents=True)
    scoop.write_bytes(b"")

    monkeypatch.setattr(deps.Path, "home", staticmethod(lambda: tmp_path))

    def verify(path: Path) -> bool:
        return "mpv player" not in str(path).lower() and path.is_file()

    monkeypatch.setattr(deps, "_verify_mpv_cli", verify)
    assert deps.find_mpv_binary() == str(scoop.resolve())


def test_check_report_shows_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(deps, "find_mpv_binary", lambda: r"C:\scoop\shims\mpv.exe")
    monkeypatch.setattr(deps, "mpv_available", lambda: True)
    report = deps.check_report()
    assert "ruta:" in report
    assert "mpv.exe" in report


def test_default_venv_dir_on_wsl_mount(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    repo = Path("/mnt/c/Users/test/terminal-radio")
    monkeypatch.setattr(deps, "is_repo_on_windows_mount", lambda p: True)
    venv = deps.default_venv_dir(repo)
    assert venv == Path.home() / ".local" / "share" / "terminal-radio" / "venv"


def test_default_venv_dir_native_linux(tmp_path: Path) -> None:
    repo = tmp_path / "terminal-radio"
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(deps, "is_repo_on_windows_mount", lambda p: False)
    try:
        assert deps.default_venv_dir(repo) == repo / ".venv"
    finally:
        monkeypatch.undo()


def test_is_externally_managed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    marker = tmp_path / "EXTERNALLY-MANAGED"
    marker.write_text("[externally-managed]\n", encoding="utf-8")
    monkeypatch.setattr(deps.sysconfig, "get_path", lambda _name: str(tmp_path))
    assert deps.is_externally_managed() is True


def test_pip_install_steps_debian(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(deps, "is_termux", lambda: False)
    monkeypatch.setattr(deps, "detect_linux_family", lambda: deps.LinuxFamily.DEBIAN)
    steps = deps.pip_install_steps()
    assert steps[0].command[-1] == "python3-pip"


def test_check_report_mentions_mpv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(deps, "find_mpv_binary", lambda: None)
    monkeypatch.setattr(deps, "mpv_available", lambda: False)
    monkeypatch.setattr(deps, "mpv_install_steps", lambda: [])
    report = deps.check_report()
    assert "mpv" in report
    assert "no encontrado" in report
    assert "[FALTA]" in report
