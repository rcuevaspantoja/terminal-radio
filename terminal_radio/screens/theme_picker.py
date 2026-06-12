"""Selector de temas compacto con preview del fondo visible."""

from __future__ import annotations

from textual.command import CommandPalette


class ThemePickerScreen(CommandPalette):
    """Command palette reducido para previsualizar temas en la UI detrás."""

    DEFAULT_CSS = """
    ThemePickerScreen {
        align: center top;
        background: transparent;
    }

    ThemePickerScreen #--container {
        margin-top: 1;
        width: 56;
        height: auto;
        max-height: 45%;
        background: $surface 70%;
        &:dark { background: $panel 70%; }
    }

    ThemePickerScreen #--input {
        background: $surface 85%;
        &:dark { background: $panel 85%; }
    }

    ThemePickerScreen CommandList {
        max-height: 10;
        scrollbar-size-vertical: 1;
        scrollbar-background: transparent;
    }
    """
