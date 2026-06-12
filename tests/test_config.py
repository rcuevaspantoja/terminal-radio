"""Tests de configuración persistida."""

from __future__ import annotations

import json

from terminal_radio.config import AppSettings, load_settings, save_settings


def test_app_settings_defaults() -> None:
    settings = AppSettings()
    assert settings.volume == 50
    assert settings.history_max == 50
    assert settings.autoplay_last is False


def test_save_and_load_roundtrip(tmp_path, monkeypatch) -> None:
    config_dir = tmp_path / "terminal-radio"
    monkeypatch.setattr(
        "terminal_radio.config.get_config_dir",
        lambda: config_dir,
    )

    original = AppSettings(volume=72, autoplay_last=True, theme="nord")
    save_settings(original)

    config_file = config_dir / "config.json"
    assert config_file.is_file()
    on_disk = json.loads(config_file.read_text(encoding="utf-8"))
    assert on_disk["volume"] == 72
    assert on_disk["autoplay_last"] is True
    assert on_disk["theme"] == "nord"

    loaded = load_settings()
    assert loaded.volume == 72
    assert loaded.autoplay_last is True
    assert loaded.theme == "nord"


def test_env_override(monkeypatch) -> None:
    monkeypatch.setenv("TERMINAL_RADIO_VOLUME", "88")
    settings = AppSettings()
    assert settings.volume == 88
