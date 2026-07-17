"""Detección de plataforma y rutas de datos por SO."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_CONFIG_DIR_NAME = "terminal-radio"


def get_config_dir() -> Path:
    """Directorio de configuración y datos persistentes."""
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
        return base / _CONFIG_DIR_NAME
    return Path.home() / ".config" / _CONFIG_DIR_NAME
