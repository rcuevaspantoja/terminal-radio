"""Modal para renombrar un favorito."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label


class RenameModal(ModalScreen[str | None]):
    """Enter confirma, Esc cancela."""

    DEFAULT_CSS = """
    RenameModal {
        align: center middle;
    }
    #rename-dialog {
        width: 60;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }
    #rename-input {
        margin-top: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", priority=True),
    ]

    def __init__(self, station_name: str, *, current_name: str | None = None) -> None:
        super().__init__()
        self._station_name = station_name
        self._initial = current_name or station_name

    def compose(self) -> ComposeResult:
        with Vertical(id="rename-dialog"):
            yield Label(f"Rename: [bold]{self._station_name}[/]", markup=True)
            yield Input(value=self._initial, placeholder="Display name…", id="rename-input")
        yield Label("[dim]Enter saves · Esc cancels[/dim]", markup=True)

    def on_mount(self) -> None:
        self.query_one("#rename-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "rename-input":
            return
        value = event.value.strip()
        self.dismiss(value if value else None)

    def action_cancel(self) -> None:
        self.dismiss(None)
