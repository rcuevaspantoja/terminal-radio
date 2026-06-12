"""Aplicación Textual raíz."""

from __future__ import annotations

from functools import partial

from textual import on
from textual.app import App
from textual.binding import Binding
from textual.command import Command, CommandPalette, DiscoveryHit, Hit
from textual.theme import ThemeProvider

from terminal_radio.config import AppSettings, save_settings
from terminal_radio.debug.perf import perf
from terminal_radio.screens.main_screen import MainScreen
from terminal_radio.screens.theme_picker import ThemePickerScreen


class TerminalRadioApp(App):
    """Orquesta la TUI; la pantalla principal gestiona búsqueda y reproducción."""

    TITLE = "Terminal Radio"
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [
        Binding("t", "change_theme", "Theme"),
    ]

    def __init__(self, settings: AppSettings) -> None:
        super().__init__()
        self.settings = settings
        self.main_screen: MainScreen | None = None
        self._theme_picker_open = False
        self._theme_before_picker: str | None = None

    def _hide_app_quit_footer_hint(self) -> None:
        """Keep Textual's default ctrl+q quit out of the footer (^q duplicate)."""
        MainScreen._patch_binding_show(self, "quit", show=False)
        self.refresh_bindings()

    def search_themes(self) -> None:
        """Theme picker with live preview while browsing."""
        self._theme_before_picker = self.theme
        self._theme_picker_open = True
        self.push_screen(
            ThemePickerScreen(
                providers=[ThemeProvider],
                placeholder="Search themes…",
                id="theme-picker",
            ),
        )

    @staticmethod
    def _theme_name_from_hit(hit: Hit | DiscoveryHit) -> str | None:
        command = hit.command
        if isinstance(command, partial) and command.args:
            return str(command.args[0])
        return hit.text

    @on(CommandPalette.OptionHighlighted)
    def _preview_theme_on_highlight(self, event: CommandPalette.OptionHighlighted) -> None:
        if not self._theme_picker_open:
            return
        option = event.highlighted_event.option
        if not isinstance(option, Command):
            return
        name = self._theme_name_from_hit(option.hit)
        if name and name in self.available_themes:
            self.theme = name

    @on(CommandPalette.Closed)
    def _on_theme_picker_closed(self, event: CommandPalette.Closed) -> None:
        if not self._theme_picker_open:
            return
        self._theme_picker_open = False
        if not event.option_selected and self._theme_before_picker is not None:
            self.theme = self._theme_before_picker
        self._theme_before_picker = None

    def on_mount(self) -> None:
        self.main_screen = MainScreen(self.settings)
        self.push_screen(self.main_screen)
        self._hide_app_quit_footer_hint()

    def action_quit(self) -> None:
        """Cierra audio y sale; mpv debe morir antes de destruir la TUI."""
        self.cleanup_resources()
        self.exit()

    def on_unmount(self) -> None:
        self.cleanup_resources()

    def cleanup_resources(self) -> None:
        """Libera audio y config. No usar el nombre _shutdown (reservado por Textual)."""
        if getattr(self, "_cleaned_up", False):
            return
        self._cleaned_up = True
        save_settings(self.settings)
        screen = self.main_screen
        if screen is None:
            try:
                top = self.screen
                if isinstance(top, MainScreen):
                    screen = top
            except Exception:
                screen = None
        if screen is not None:
            screen.shutdown()

        from terminal_radio.audio.mpv_subprocess import MpvSubprocessBackend

        MpvSubprocessBackend.force_kill_tracked()
        perf.close()
