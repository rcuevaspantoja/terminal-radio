"""Barra de estado del reproductor."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static

from terminal_radio.debug.perf import perf
from terminal_radio.models.player import PlayerState

_VOLUME_BAR_WIDTH = 14
_TRACK_MAX_LEN = 36
_VOLUME_HIDE_SECONDS = 2.5


def format_volume_meter(volume: int, *, width: int = _VOLUME_BAR_WIDTH) -> str:
    """Barra ASCII + porcentaje, p. ej. [######--------]  65%."""
    level = max(0, min(100, volume))
    filled = round(level / 100 * width)
    bar = "#" * filled + "-" * (width - filled)
    return f"[{bar}] {level:>3}%"


def _truncate_track(title: str | None, *, max_len: int = _TRACK_MAX_LEN) -> str:
    text = title or "-"
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


class PlayerBar(Horizontal):
    """Una fila: emisora a la izquierda, volumen pegado a la derecha."""

    DEFAULT_CSS = """
    PlayerBar {
        dock: bottom;
        height: 1;
        width: 1fr;
        margin-bottom: 1;
        background: $surface;
        padding: 0 1;
    }
    #player-station-line {
        width: 1fr;
        min-width: 0;
    }
    #player-volume-line {
        width: auto;
        min-width: 22;
        content-align: right middle;
    }
    PlayerBar.-playing #player-station-line {
        color: $success;
    }
    PlayerBar.-paused #player-station-line {
        color: $warning;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("", id="player-station-line", markup=True)
        yield Static("", id="player-volume-line", markup=True)

    def on_mount(self) -> None:
        self._volume_visible = False
        self._hide_volume_timer = None
        self._apply_text(*self._format_lines(PlayerState()))
        self._set_volume_visible(False)

    def on_unmount(self) -> None:
        if self._hide_volume_timer is not None:
            self._hide_volume_timer.stop()
            self._hide_volume_timer = None

    @staticmethod
    def format_track_line(state: PlayerState) -> str:
        if state.track_meta is not None:
            return state.track_meta.display_line()
        return _truncate_track(state.track_title)

    @staticmethod
    def _format_lines(state: PlayerState) -> tuple[str, str]:
        vol = format_volume_meter(state.volume)
        volume_line = f"VOL {vol}"
        if state.error:
            return f"[red]{state.error}[/red]", volume_line
        if state.station_name:
            icon = ">" if state.is_playing else "||"
            track = PlayerBar.format_track_line(state)
            station_line = f"{icon} [bold]{state.station_name}[/]  |  {track}"
            return station_line, volume_line
        return (
            "Not playing — select a station (Enter / p).",
            "VOL [--------------]   0%",
        )

    @staticmethod
    def format_state(state: PlayerState) -> str:
        """Texto completo (tests / perf)."""
        station, volume = PlayerBar._format_lines(state)
        return f"{station}  {volume}"

    def _apply_text(self, station_line: str, volume_line: str) -> None:
        self.query_one("#player-station-line", Static).update(station_line, layout=True)
        vol = self.query_one("#player-volume-line", Static)
        vol.update(volume_line, layout=True)
        if self._volume_visible:
            vol.refresh()

    def _set_volume_visible(self, visible: bool) -> None:
        self._volume_visible = visible
        self.query_one("#player-volume-line", Static).display = visible

    def reveal_volume(self) -> None:
        """Muestra el medidor unos segundos (al pulsar + / -)."""
        self._set_volume_visible(True)
        if self._hide_volume_timer is not None:
            self._hide_volume_timer.stop()
        self._hide_volume_timer = self.set_timer(
            _VOLUME_HIDE_SECONDS,
            self._hide_volume,
            name="hide-volume",
        )
        self.query_one("#player-volume-line", Static).refresh()

    def _hide_volume(self) -> None:
        self._hide_volume_timer = None
        self._set_volume_visible(False)

    def update_state(self, state: PlayerState) -> None:
        station_line, volume_line = self._format_lines(state)
        rendered = f"{station_line}|{volume_line}"
        if rendered == getattr(self, "_rendered_text", None):
            return
        self._rendered_text = rendered
        self.set_class(state.is_playing and state.station_name is not None, "-playing")
        self.set_class(
            not state.is_playing and state.station_name is not None,
            "-paused",
        )
        self._apply_text(station_line, volume_line)
        if perf.enabled:
            region = self.region
            perf.note("player_bar_last", f"{station_line} | {volume_line}"[:120])
            perf.note(
                "player_bar_region",
                f"x={region.x} y={region.y} w={region.width} h={region.height}",
            )
            perf.count("ui.player_bar_updated")
