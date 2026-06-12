"""Comprueba que la barra del reproductor queda visible en pantalla."""

from __future__ import annotations

import asyncio

from terminal_radio.app import TerminalRadioApp
from terminal_radio.config import AppSettings
from textual.widgets import Static

from terminal_radio.widgets.player_bar import PlayerBar


def test_player_bar_is_on_screen() -> None:
    async def run() -> None:
        app = TerminalRadioApp(AppSettings())
        async with app.run_test(size=(100, 24)) as pilot:
            await pilot.pause()
            bar = app.screen.query_one("#player-bar", PlayerBar)
            footer = app.screen.query_one("Footer")
            height = app.size.height
            assert bar.region.height >= 1
            station_line = app.screen.query_one("#player-station-line", Static)
            vol_line = app.screen.query_one("#player-volume-line", Static)
            assert not vol_line.display
            bar.reveal_volume()
            await pilot.pause()
            assert vol_line.display
            assert "VOL" in str(vol_line.render())
            assert vol_line.region.x > station_line.region.x
            assert bar.region.y + bar.region.height <= footer.region.y
            assert footer.region.y + footer.region.height <= height

    asyncio.run(run())
