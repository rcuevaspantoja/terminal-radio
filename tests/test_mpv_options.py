"""Tests de opciones mpv para streaming."""

from __future__ import annotations

from terminal_radio.audio.mpv_options import (
    MPV_STREAM_CLI_ARGS,
    MPV_STREAM_KWARGS,
    get_mpv_stream_cli_args,
    get_mpv_stream_kwargs,
)


def test_stream_cli_disables_autosync_and_buffers() -> None:
    assert "--autosync=0" in MPV_STREAM_CLI_ARGS
    assert "--cache-pause=yes" in MPV_STREAM_CLI_ARGS
    assert "--cache-secs=30" in MPV_STREAM_CLI_ARGS


def test_stream_kwargs_match_cli_intent() -> None:
    assert MPV_STREAM_KWARGS["autosync"] == 0
    assert MPV_STREAM_KWARGS["cache_pause"] == "yes"
    assert MPV_STREAM_KWARGS["cache_secs"] == 30


def test_windows_stream_args_include_wasapi(monkeypatch) -> None:
    monkeypatch.setattr("terminal_radio.audio.mpv_options.sys.platform", "win32")
    args = get_mpv_stream_cli_args()
    assert "--ao=wasapi" in args
    assert "--force-window=no" in args
    assert "--keep-open=no" in args
    assert get_mpv_stream_kwargs()["audio_exclusive"] == "no"
