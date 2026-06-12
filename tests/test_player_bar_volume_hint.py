"""Tests del medidor de volumen transitorio."""

from __future__ import annotations

import asyncio

from textual.widgets import Static

from terminal_radio.app import TerminalRadioApp
from terminal_radio.config import AppSettings
from terminal_radio.widgets.player_bar import PlayerBar


def test_volume_hint_hidden_until_reveal() -> None:
    async def run() -> None:
        app = TerminalRadioApp(AppSettings())
        async with app.run_test(size=(100, 24)) as pilot:
            await pilot.pause()
            vol = app.screen.query_one("#player-volume-line", Static)
            assert vol.display is False
            app.screen.query_one("#player-bar", PlayerBar).reveal_volume()
            await pilot.pause()
            assert vol.display is True

    asyncio.run(run())
