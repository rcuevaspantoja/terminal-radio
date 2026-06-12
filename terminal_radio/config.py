"""Configuración de usuario: carga/guardado JSON y overrides por entorno."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from terminal_radio.platform.detect import get_config_dir

CONFIG_FILENAME = "config.json"


class AppSettings(BaseSettings):
    """Preferencias persistidas y valores por defecto de la aplicación."""

    model_config = SettingsConfigDict(
        env_prefix="TERMINAL_RADIO_",
        env_file=None,
        extra="ignore",
    )

    volume: int = Field(default=50, ge=0, le=100)
    volume_step: int = Field(default=5, ge=1, le=20)
    history_max: int = Field(default=50, ge=1, le=500)
    screensaver_idle_seconds: int = Field(default=120, ge=0)
    autoplay_last: bool = False
    media_keys_enabled: bool = True
    show_system_tray: bool = True
    last_station_uuid: str | None = None


def get_config_path() -> Path:
    return get_config_dir() / CONFIG_FILENAME


def load_settings() -> AppSettings:
    """Carga config desde disco; variables TERMINAL_RADIO_* tienen prioridad."""
    path = get_config_path()
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
        return AppSettings(**data)
    return AppSettings()


def save_settings(settings: AppSettings) -> None:
    """Persiste la configuración actual en JSON."""
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(settings.model_dump(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
