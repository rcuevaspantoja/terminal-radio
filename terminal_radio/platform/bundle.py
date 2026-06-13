"""Rutas para builds empaquetados (PyInstaller, instalador)."""

from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    """True cuando la app corre como ejecutable empaquetado."""
    return bool(getattr(sys, "frozen", False))


def install_dir() -> Path | None:
    """Directorio que contiene radio.exe (builds frozen)."""
    if not is_frozen():
        return None
    return Path(sys.executable).resolve().parent


def bundled_mpv_windows() -> Path | None:
    """
    mpv incluido junto al exe: ``<install_dir>/mpv/mpv.exe``.

    Usado en releases Windows; no requiere Scoop ni PATH.
    """
    if sys.platform != "win32":
        return None
    base = install_dir()
    if base is None:
        return None
    candidate = base / "mpv" / "mpv.exe"
    return candidate if candidate.is_file() else None
