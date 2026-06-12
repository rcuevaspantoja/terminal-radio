"""Pantalla screensaver: estación y pista actual."""

from __future__ import annotations

from rich.align import Align
from rich.text import Text
from textual import events, on
from textual.app import ComposeResult
from textual.containers import Center, Middle, Vertical
from textual.screen import ModalScreen
from textual.widgets import Static

from terminal_radio.models.player import PlayerState
from terminal_radio.widgets.player_bar import PlayerBar


class ScreensaverScreen(ModalScreen[None]):
    """Overlay a pantalla completa; cualquier tecla cierra. El audio sigue."""

    DEFAULT_CSS = """
    ScreensaverScreen {
        background: $background 90%;
    }
    #screensaver-middle {
        width: 100%;
        height: 100%;
    }
    #screensaver-panel {
        width: auto;
        height: auto;
        align: center middle;
    }
    #screensaver-station {
        width: auto;
        content-align: center middle;
        text-style: dim;
    }
    #screensaver-track {
        width: auto;
        content-align: center middle;
        margin-top: 1;
        color: $primary;
        text-style: bold;
    }
    #screensaver-hint {
        width: auto;
        content-align: center middle;
        margin-top: 3;
        text-style: dim;
    }
    """

    BINDINGS = []

    def __init__(self, state: PlayerState) -> None:
        super().__init__()
        self._state = state

    def compose(self) -> ComposeResult:
        with Middle(id="screensaver-middle"):
            with Center():
                with Vertical(id="screensaver-panel"):
                    yield Static("", id="screensaver-station")
                    yield Static("", id="screensaver-track")
                    yield Static(
                        "[dim]Press any key to return[/dim]",
                        id="screensaver-hint",
                        markup=True,
                    )

    def on_mount(self) -> None:
        self._refresh_content()

    def update_state(self, state: PlayerState) -> None:
        self._state = state
        self._refresh_content()

    def _refresh_content(self) -> None:
        station = self._state.station_name or "Terminal Radio"
        self.query_one("#screensaver-station", Static).update(
            Align.center(Text(station)),
        )
        track_line = PlayerBar.format_track_line(self._state)
        self.query_one("#screensaver-track", Static).update(
            Align.center(Text(track_line, style="bold")),
        )

    @on(events.Key)
    def _dismiss_on_key(self, event: events.Key) -> None:
        event.stop()
        self.dismiss()
