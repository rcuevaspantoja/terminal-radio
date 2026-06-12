"""Launcher global: un comando `radio` sin activar venv ni recordar rutas."""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

from terminal_radio.platform.detect import get_config_dir

RUNTIME_FILENAME = "runtime.json"
CLI_NAMES = ("radio", "terminal-radio")


def get_local_bin_dir() -> Path:
    """Directorio de comandos del usuario (~/.local/bin o %USERPROFILE%\\.local\\bin)."""
    return Path.home() / ".local" / "bin"


def get_runtime_path() -> Path:
    return get_config_dir() / RUNTIME_FILENAME


def save_runtime(python: Path, venv_dir: Path | None = None) -> None:
    """Guarda que Python usar al ejecutar radio/terminal-radio."""
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "python": str(python.resolve()),
        "venv": str(venv_dir.resolve()) if venv_dir else None,
    }
    get_runtime_path().write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def load_runtime_python() -> Path | None:
    """Lee el Python registrado por el instalador."""
    path = get_runtime_path()
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        python = Path(data["python"])
    except (json.JSONDecodeError, KeyError, TypeError, OSError):
        return None
    return python if python.is_file() else None


def _user_path_entries_windows() -> list[str]:
    """Entradas del PATH de usuario en Windows (registro)."""
    if sys.platform != "win32":
        return []
    try:
        import winreg
    except ImportError:
        return []
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
            value, _ = winreg.QueryValueEx(key, "Path")
            return [entry for entry in str(value).split(os.pathsep) if entry]
    except OSError:
        return []


def _path_list_contains(path_entries: list[str], target: Path) -> bool:
    try:
        resolved = target.resolve()
    except OSError:
        return False
    for entry in path_entries:
        try:
            if Path(entry).resolve() == resolved:
                return True
        except OSError:
            continue
    return False


def ensure_local_bin_on_path() -> bool:
    """
    Anade %USERPROFILE%\\.local\\bin al PATH del usuario en Windows.

    Devuelve True si el registro se modifico.
    """
    if sys.platform != "win32":
        return False

    bin_dir = get_local_bin_dir()
    user_entries = _user_path_entries_windows()
    if _path_list_contains(user_entries, bin_dir):
        return False

    try:
        import winreg
    except ImportError:
        return False

    bin_str = str(bin_dir)
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Environment",
            0,
            winreg.KEY_READ | winreg.KEY_WRITE,
        ) as key:
            try:
                current, _ = winreg.QueryValueEx(key, "Path")
                current = str(current)
            except OSError:
                current = ""
            new_path = f"{current}{os.pathsep}{bin_str}" if current else bin_str
            winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
    except OSError:
        return False

    return True


def discover_python() -> Path | None:
    """Busca el Python del proyecto sin depender del launcher en PATH."""
    registered = load_runtime_python()
    if registered:
        return registered

    candidates = [
        Path.home() / ".local" / "share" / "terminal-radio" / "venv" / "bin" / "python",
        Path.home() / ".local" / "share" / "terminal-radio" / "venv" / "Scripts" / "python.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate

    on_path = shutil.which("terminal-radio")
    if on_path:
        return Path(on_path)

    return None


def run(argv: list[str] | None = None) -> int:
    """Ejecuta terminal_radio con el Python correcto."""
    import subprocess

    args = list(argv if argv is not None else sys.argv[1:])
    python = discover_python()

    if python is None:
        try:
            from terminal_radio.__main__ import main as app_main

            return app_main(args)
        except ImportError:
            print(
                "No se encontro una instalacion de Terminal Radio.\n"
                "Ejecuta primero: python scripts/install.py",
                file=sys.stderr,
            )
            return 1

    cmd = [str(python), "-m", "terminal_radio", *args]
    result = subprocess.run(cmd)
    return int(result.returncode)


def _unix_shim(python: Path) -> str:
    return f'#!/bin/sh\nexec "{python}" -m terminal_radio "$@"\n'


def _windows_cmd(python: Path) -> str:
    return f'@echo off\r\n"{python}" -m terminal_radio %*\r\n'


def _write_shim(target: Path, python: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":
        target.write_text(_windows_cmd(python), encoding="utf-8", newline="\r\n")
    else:
        target.write_text(_unix_shim(python), encoding="utf-8")
        target.chmod(0o755)


def install_cli_shims(python: Path, venv_dir: Path | None = None) -> tuple[list[Path], bool]:
    """
    Crea comandos `radio` y `terminal-radio` en ~/.local/bin.

    Devuelve (rutas creadas, path_usuario_modificado_en_windows).
    """
    save_runtime(python, venv_dir)
    bin_dir = get_local_bin_dir()
    created: list[Path] = []

    for name in CLI_NAMES:
        if sys.platform == "win32":
            target = bin_dir / f"{name}.cmd"
        else:
            target = bin_dir / name
        _write_shim(target, python)
        created.append(target)

    path_modified = ensure_local_bin_on_path()
    return created, path_modified


def local_bin_install_hint(bin_dir: Path, *, path_modified: bool = False) -> str:
    if _local_bin_on_path(bin_dir):
        return ""
    if sys.platform == "win32":
        if path_modified:
            return (
                "PATH de usuario actualizado. Cierra y reabre la terminal, luego ejecuta: radio\n"
                "  (En esta sesion usa install.ps1 o anade .local\\bin al PATH manualmente.)"
            )
        return (
            f"No se pudo actualizar el PATH automaticamente.\n"
            f"  Anade {bin_dir} en Configuracion > Variables de entorno > PATH del usuario"
        )
    return (
        f"Anade {bin_dir} al PATH si no esta ya:\n"
        f'  echo \'export PATH="$HOME/.local/bin:$PATH"\' >> ~/.bashrc && source ~/.bashrc'
    )


def _local_bin_on_path(bin_dir: Path) -> bool:
    path_entries = os.environ.get("PATH", "").split(os.pathsep)
    try:
        resolved = bin_dir.resolve()
    except OSError:
        return False
    for entry in path_entries:
        if not entry:
            continue
        try:
            if Path(entry).resolve() == resolved:
                return True
        except OSError:
            continue
    return False
