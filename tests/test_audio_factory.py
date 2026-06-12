"""Tests de factory y selección de backend."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import terminal_radio.audio.backend as audio_backend
from terminal_radio.audio.backend import MpvNotFoundError, create_audio_backend
from terminal_radio.audio.mpv_subprocess import MpvSubprocessBackend


def test_find_mpv_binary_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(audio_backend, "find_mpv_binary", lambda: None)
    assert audio_backend.find_mpv_binary() is None


def test_create_backend_raises_without_mpv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("terminal_radio.audio.backend.find_mpv_binary", lambda: None)
    with pytest.raises(MpvNotFoundError, match="mpv not found"):
        create_audio_backend()


def test_create_backend_termux_uses_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("terminal_radio.audio.backend.find_mpv_binary", lambda: "/usr/bin/mpv")
    monkeypatch.setattr("terminal_radio.audio.backend.is_termux", lambda: True)

    backend = create_audio_backend(volume=40)
    assert isinstance(backend, MpvSubprocessBackend)
    assert backend.get_volume() == 40


def test_create_backend_fallback_to_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("terminal_radio.audio.backend.find_mpv_binary", lambda: "mpv")
    monkeypatch.setattr("terminal_radio.audio.backend.is_termux", lambda: False)

    with patch(
        "terminal_radio.audio.mpv_binding.MpvBindingBackend",
        side_effect=RuntimeError("sin libmpv"),
    ):
        backend = create_audio_backend(volume=55)

    assert isinstance(backend, MpvSubprocessBackend)
    assert backend.get_volume() == 55


def test_create_backend_prefers_binding_on_linux(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("terminal_radio.audio.backend.find_mpv_binary", lambda: "mpv")
    monkeypatch.setattr("terminal_radio.audio.backend.is_termux", lambda: False)
    monkeypatch.setattr("terminal_radio.audio.backend.sys.platform", "linux")

    mock_binding = MagicMock()
    with patch(
        "terminal_radio.audio.mpv_binding.MpvBindingBackend",
        return_value=mock_binding,
    ):
        backend = create_audio_backend()

    assert backend is mock_binding


def test_create_backend_windows_uses_subprocess(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("terminal_radio.audio.backend.find_mpv_binary", lambda: "mpv")
    monkeypatch.setattr("terminal_radio.audio.backend.is_termux", lambda: False)
    monkeypatch.setattr("terminal_radio.audio.backend.sys.platform", "win32")

    mock_binding = MagicMock()
    with patch(
        "terminal_radio.audio.mpv_binding.MpvBindingBackend",
        return_value=mock_binding,
    ) as binding_ctor:
        backend = create_audio_backend()

    binding_ctor.assert_not_called()
    assert isinstance(backend, MpvSubprocessBackend)
