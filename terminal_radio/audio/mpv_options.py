"""Opciones mpv para radio por internet (estables, sin drift de velocidad)."""

from __future__ import annotations

import sys

# autosync=0: evita que mpv acelere/frene el audio para “sincronizar”.
# cache-*: buffer generoso; cache-pause pausa en underrun en vez de glitch.
# demuxer-lavf-o reconnect: reintenta si el stream se corta.
_BASE_CLI_ARGS: tuple[str, ...] = (
    "--no-video",
    "--cache=yes",
    "--cache-secs=30",
    "--demuxer-readahead-secs=15",
    "--cache-pause=yes",
    "--autosync=0",
    "--network-timeout=60",
    "--demuxer-lavf-o=reconnect=1,reconnect_streamed=1,reconnect_delay_max=5",
)

_BASE_KWARGS: dict[str, object] = {
    "video": False,
    "cache": "yes",
    "cache_secs": 30,
    "demuxer_readahead_secs": 15,
    "cache_pause": "yes",
    "autosync": 0,
    "network_timeout": 60,
    "demuxer_lavf_o": "reconnect=1,reconnect_streamed=1,reconnect_delay_max=5",
}

_WINDOWS_CLI_EXTRA: tuple[str, ...] = (
    "--ao=wasapi",
    "--audio-exclusive=no",
    "--force-window=no",
    "--keep-open=no",
)

_WINDOWS_KWARGS_EXTRA: dict[str, object] = {
    "ao": "wasapi",
    "audio_exclusive": "no",
}

# Compat: imports existentes en tests.
MPV_STREAM_CLI_ARGS = _BASE_CLI_ARGS
MPV_STREAM_KWARGS = _BASE_KWARGS


def get_mpv_stream_cli_args() -> tuple[str, ...]:
    if sys.platform == "win32":
        return _BASE_CLI_ARGS + _WINDOWS_CLI_EXTRA
    return _BASE_CLI_ARGS


def get_mpv_stream_kwargs() -> dict[str, object]:
    if sys.platform == "win32":
        return {**_BASE_KWARGS, **_WINDOWS_KWARGS_EXTRA}
    return dict(_BASE_KWARGS)
