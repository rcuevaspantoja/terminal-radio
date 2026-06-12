"""Pantalla principal: búsqueda, catálogo y reproducción."""

from __future__ import annotations

import dataclasses
import threading

from textual import events, on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.dom import DOMNode
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, ListView, Static, TabbedContent, TabPane

from terminal_radio.models.station import Station

from terminal_radio.api.radio_browser import RadioBrowserClient, RadioBrowserError
from terminal_radio.debug.perf import perf
from terminal_radio.audio import MpvNotFoundError
from terminal_radio.config import AppSettings
from terminal_radio.models.player import PlayerState
from terminal_radio.services.player import PlayerService
from terminal_radio.services.station_catalog import StationCatalogService
from terminal_radio.screens.rename_modal import RenameModal
from terminal_radio.screens.screensaver import ScreensaverScreen
from terminal_radio.screens.theme_picker import ThemePickerScreen
from terminal_radio.services.metadata import MetadataService
from terminal_radio.widgets.player_bar import PlayerBar
from terminal_radio.widgets.station_list import StationList

class MainScreen(Screen):
    """Tabs Buscar / Favoritos / Historial con lista y barra de player."""

    _STATUS_AUTO_HIDE_SECONDS = 4.0

    DEFAULT_CSS = """
    MainScreen {
        layout: vertical;
    }
    #status-line {
        height: 1;
        display: none;
        padding: 0 1;
    }
    #search-input {
        margin: 0 1;
    }
    TabbedContent {
        height: 1fr;
    }
    StationList {
        scrollbar-size-vertical: 1;
    }
    StationList > ListItem {
        height: 1;
    }
    """

    BINDINGS = [
        Binding("/", "focus_search", "Search", priority=True),
        Binding("escape", "cancel_search", "Cancel", priority=True),
        Binding("q", "exit_application", "Quit", priority=True),
        Binding("enter", "play_selected", "Play", show=False),
        Binding("p", "play_selected", "Play", show=False),
        ("space", "toggle_pause", "Pause"),
        ("+", "volume_up", "Vol+"),
        ("=", "volume_up", "Vol+"),
        ("-", "volume_down", "Vol-"),
        ("f", "toggle_favorite", "Favorite"),
        ("r", "rename_favorite", "Rename"),
        ("l", "screensaver", "Lock"),
        ("f12", "dump_perf", "Perf"),
    ]

    _STATION_LIST_IDS = ("station-list", "favorites-list", "history-list")
    _TAB_TO_LIST = {
        "tab-search": "station-list",
        "tab-favorites": "favorites-list",
        "tab-history": "history-list",
    }

    def __init__(self, settings: AppSettings) -> None:
        super().__init__()
        self.settings = settings
        self.player: PlayerService | None = None
        self.api = RadioBrowserClient()
        self.catalog = StationCatalogService(settings)
        self._metadata = MetadataService()
        self._metadata_fetch_token = 0
        self._last_fetched_title: str | None = None
        self._idle_timer = None
        self._mpv_error: str | None = None
        self._status_message: str | None = None
        self._search_open = False
        self._perf_timer = None
        self._status_timer = None
        self._status_generation = 0

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("", id="status-line")
        yield Input(placeholder="Search stations…", id="search-input")
        with TabbedContent():
            with TabPane("Search", id="tab-search"):
                yield StationList(id="station-list")
            with TabPane("Favorites", id="tab-favorites"):
                yield StationList(id="favorites-list")
            with TabPane("History", id="tab-history"):
                yield StationList(id="history-list")
        yield PlayerBar(id="player-bar")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#search-input", Input).display = False
        self._init_player()
        self._sync_catalog_lists()
        self._load_catalog()
        self.call_after_refresh(self._focus_active_station_list)
        self.call_after_refresh(self._sync_global_footer_hints)
        self._reset_idle_timer()
        if perf.enabled:
            log_path = perf._log_path
            hint = str(log_path) if log_path else "perf.log"
            self._set_status(f"[dim]Diagnostic mode — F12 saves report · {hint}[/dim]")
            self._perf_timer = self.set_interval(
                15.0,
                self._perf_interval_snapshot,
                name="perf-snapshot",
            )

    def _is_catalog_tab(self) -> bool:
        """Favorites and History omit global Search/Quit footer hints."""
        try:
            tabbed = self.query_one(TabbedContent)
        except Exception:
            return False
        return str(tabbed.active) in ("tab-favorites", "tab-history")

    @staticmethod
    def _patch_binding_show(node: DOMNode, action: str, *, show: bool) -> None:
        bindings_map = node._bindings
        for key, binding_list in bindings_map.key_to_bindings.items():
            bindings_map.key_to_bindings[key] = [
                dataclasses.replace(b, show=show and bool(b.description))
                if b.action == action
                else b
                for b in binding_list
            ]

    def _sync_global_footer_hints(self) -> None:
        """Hide Search/Quit in footer on Favorites/History; keys still work."""
        show = not self._is_catalog_tab()
        for action in ("focus_search", "exit_application"):
            self._patch_binding_show(self, action, show=show)
        self.refresh_bindings()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if action == "dump_perf":
            return perf.enabled
        if action == "cancel_search":
            return self._search_open
        if self._search_open and action in {"play_selected", "focus_search"}:
            return False
        if action == "rename_favorite":
            station = self._target_station()
            return station is not None and self.catalog.is_favorite(station.stationuuid)
        if action == "screensaver":
            return not self._search_open and self._mpv_error is None
        return True

    @on(TabbedContent.TabActivated)
    def _on_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        self._sync_global_footer_hints()

    def _all_station_lists(self) -> list[StationList]:
        return [self.query_one(f"#{list_id}", StationList) for list_id in self._STATION_LIST_IDS]

    def _active_station_list(self) -> StationList | None:
        tabbed = self.query_one(TabbedContent)
        list_id = self._TAB_TO_LIST.get(str(tabbed.active))
        if list_id is None:
            return None
        return self.query_one(f"#{list_id}", StationList)

    def _focus_active_station_list(self) -> None:
        if self._search_open:
            return
        station_list = self._active_station_list()
        if station_list is None:
            return
        station_list.focus(scroll_visible=False)
        station_list.call_after_refresh(station_list.select_first)

    def _apply_favorite_markers(self, *list_ids: str) -> None:
        uuids = self.catalog.favorite_uuids()
        names = self.catalog.favorite_display_names()
        targets = list_ids or self._STATION_LIST_IDS
        for list_id in targets:
            station_list = self.query_one(f"#{list_id}", StationList)
            station_list.set_favorite_uuids(uuids)
            if list_id == "favorites-list":
                station_list.set_display_names(names)

    def _sync_catalog_lists(self) -> None:
        favorites = self.query_one("#favorites-list", StationList)
        favorites.set_stations([f.station for f in self.catalog.list_favorites()])
        history = self.query_one("#history-list", StationList)
        history.set_stations(self.catalog.history_stations())
        self._apply_favorite_markers()

    def _target_station(self) -> Station | None:
        active = self._active_station_list()
        if active is not None:
            selected = active.selected_station()
            if selected is not None:
                return selected
        if self.player and self.player.state.station_uuid and self.player.state.station_name:
            uuid = self.player.state.station_uuid
            for station_list in self._all_station_lists():
                for station in station_list.stations:
                    if station.stationuuid == uuid:
                        return station
            url = self.player.state.stream_url or ""
            return Station(
                stationuuid=uuid,
                name=self.player.state.station_name,
                url=url,
                url_resolved=url,
            )
        return None

    def shutdown(self) -> None:
        """Libera audio, timers y cliente HTTP (idempotente)."""
        if self._perf_timer is not None:
            self._perf_timer.stop()
            self._perf_timer = None
        if self._status_timer is not None:
            self._status_timer.stop()
            self._status_timer = None
        if self._idle_timer is not None:
            self._idle_timer.stop()
            self._idle_timer = None
        if self.player is not None:
            self.player.shutdown()
            self.player = None

    def on_unmount(self) -> None:
        self.shutdown()

    def action_exit_application(self) -> None:
        self.app.action_quit()

    def _init_player(self) -> None:
        try:
            from terminal_radio.platform.deps import find_mpv_binary, find_rejected_mpv_installs

            rejected = find_rejected_mpv_installs()
            if rejected:
                self._set_status(
                    "[dim]Note: MPV Player (GUI) is installed; "
                    "use Scoop: scoop install mpv[/dim]",
                )
            mpv_path = find_mpv_binary()
            self.player = PlayerService(self.settings)
            self.player.on_state_change(self._on_player_state)
            self._render_player_state(self.player.state)
            if mpv_path and perf.enabled:
                self._set_status(f"[dim]mpv: {mpv_path}[/dim]")
        except MpvNotFoundError as exc:
            self._mpv_error = str(exc)
            self._set_status(str(exc), error=True)

    def _on_player_state(self, state: PlayerState) -> None:
        perf.count("ui.player_state_event")
        if state.track_title:
            self._maybe_fetch_metadata(state.track_title)
        else:
            self._last_fetched_title = None
        self._schedule_player_ui_update(state)

    def _maybe_fetch_metadata(self, track_title: str) -> None:
        if track_title == self._last_fetched_title:
            return
        self._last_fetched_title = track_title
        self._metadata_fetch_token += 1
        self._fetch_track_metadata(track_title, self._metadata_fetch_token)

    @work(exclusive=True)
    async def _fetch_track_metadata(self, track_title: str, token: int) -> None:
        meta = await self._metadata.fetch(track_title)
        if token != self._metadata_fetch_token:
            return
        if not self.player or self.player.state.track_title != track_title:
            return
        self.player.set_track_meta(meta)
        self._render_player_state(self.player.state)

    def _modal_blocks_idle(self) -> bool:
        return isinstance(
            self.app.screen,
            (ScreensaverScreen, ThemePickerScreen, RenameModal),
        )

    def _reset_idle_timer(self) -> None:
        if self._idle_timer is not None:
            self._idle_timer.stop()
            self._idle_timer = None
        if self.settings.screensaver_idle_seconds <= 0:
            return
        if self._search_open or self._modal_blocks_idle():
            return
        self._idle_timer = self.set_timer(
            self.settings.screensaver_idle_seconds,
            self._activate_screensaver_idle,
            name="screensaver-idle",
        )

    def _activate_screensaver_idle(self) -> None:
        self._idle_timer = None
        if self._search_open or self._modal_blocks_idle():
            return
        self.action_screensaver()

    def action_screensaver(self) -> None:
        if self._mpv_error or self._search_open:
            return
        if isinstance(self.app.screen, ScreensaverScreen):
            return
        state = self.player.state if self.player else PlayerState()
        if self._idle_timer is not None:
            self._idle_timer.stop()
            self._idle_timer = None
        self.app.push_screen(ScreensaverScreen(state), self._on_screensaver_closed)

    def _on_screensaver_closed(self, _result: None) -> None:
        self._reset_idle_timer()

    def _schedule_player_ui_update(self, state: PlayerState) -> None:
        """Actualiza la barra; en el hilo UI refresco directo (vol/pausa)."""
        snapshot = state

        def apply() -> None:
            self._render_player_state(snapshot)

        if threading.current_thread() is threading.main_thread():
            self.call_after_refresh(apply)
        else:
            self.app.call_from_thread(self.call_after_refresh, apply)

    def on_key(self, event: events.Key) -> None:
        if perf.enabled and event.key in ("up", "down"):
            perf.mark("arrow_key")
            perf.count("ui.arrow_key")
        if not isinstance(self.app.screen, ScreensaverScreen):
            self._reset_idle_timer()

    def on_mouse_down(self, event: events.MouseDown) -> None:
        if not isinstance(self.app.screen, ScreensaverScreen):
            self._reset_idle_timer()

    @on(ListView.Highlighted, "#station-list")
    def _on_station_highlighted(self, event: ListView.Highlighted) -> None:
        perf.record_since_mark("arrow_key", "ui.arrow_to_highlight_ms")

    def _perf_interval_snapshot(self) -> None:
        perf.append_snapshot("interval")

    def action_dump_perf(self) -> None:
        path = perf.write_report()
        if path is not None:
            self._set_status(f"Performance report saved to {path}")

    def _render_player_state(
        self,
        state: PlayerState,
        *,
        reveal_volume: bool = False,
    ) -> None:
        with perf.measure("ui.player_bar_flush"):
            bar = self.query_one("#player-bar", PlayerBar)
            bar.update_state(state)
            if reveal_volume:
                bar.reveal_volume()
            bar.refresh()
            for station_list in self._all_station_lists():
                station_list.set_playback(
                    state.station_uuid,
                    is_playing=state.is_playing,
                )
            saver = self.app.screen
            if isinstance(saver, ScreensaverScreen):
                saver.update_state(state)

    def _set_status(
        self,
        message: str | None,
        *,
        error: bool = False,
        temporary: bool = False,
    ) -> None:
        if self._status_timer is not None:
            self._status_timer.stop()
            self._status_timer = None
        self._status_message = message
        self._status_generation += 1
        generation = self._status_generation
        widget = self.query_one("#status-line", Static)
        if not message:
            widget.update("")
            widget.display = False
            return
        widget.display = True
        widget.update(f"[red]{message}[/red]" if error else message)
        if temporary:
            self._status_timer = self.set_timer(
                self._STATUS_AUTO_HIDE_SECONDS,
                lambda: self._hide_status_if_current(generation),
                name="status-auto-hide",
            )

    def _hide_status_if_current(self, generation: int) -> None:
        self._status_timer = None
        if generation != self._status_generation:
            return
        self._set_status(None)

    @work(exclusive=True)
    async def _load_catalog(self) -> None:
        if self._mpv_error:
            return
        self._set_status("Loading popular stations…")
        try:
            stations = await self.api.top_voted()
            self.query_one("#station-list", StationList).set_stations(stations)
            self._apply_favorite_markers("station-list")
            self._set_status(None)
            self.call_after_refresh(self._focus_active_station_list)
        except RadioBrowserError as exc:
            self._set_status(str(exc), error=True)

    @work(exclusive=True)
    async def _run_search(self, query: str) -> None:
        self._set_status("Searching…")
        try:
            if query.strip():
                stations = await self.api.search(query)
            else:
                stations = await self.api.top_voted()
            self.query_one("#station-list", StationList).set_stations(stations)
            self._apply_favorite_markers("station-list")
            if not stations:
                self._set_status("No results.")
            else:
                self._set_status(None)
            self.call_after_refresh(self._focus_active_station_list)
        except RadioBrowserError as exc:
            self._set_status(str(exc), error=True)

    @work
    async def _register_click(self, stationuuid: str) -> None:
        await self.api.click(stationuuid)

    def action_focus_search(self) -> None:
        search = self.query_one("#search-input", Input)
        search.display = True
        search.value = ""
        self._search_open = True
        self.refresh_bindings()
        self.call_after_refresh(search.focus)

    def action_cancel_search(self) -> None:
        if not self._search_open:
            return
        self._close_search()

    def _close_search(self) -> None:
        search = self.query_one("#search-input", Input)
        search.display = False
        search.value = ""
        search.blur()
        self._search_open = False
        self.refresh_bindings()
        self.call_after_refresh(self._focus_active_station_list)

    def action_toggle_favorite(self) -> None:
        station = self._target_station()
        if station is None:
            self._set_status("[dim]Select or play a station first[/dim]")
            return
        added = self.catalog.toggle_favorite(station)
        message = "Added to favorites" if added else "Removed from favorites"
        self._set_status(message, temporary=True)
        self._sync_catalog_lists()
        self._apply_favorite_markers("station-list")

    def action_rename_favorite(self) -> None:
        station = self._target_station()
        if station is None:
            self._set_status("[dim]Select a favorite[/dim]")
            return
        favorite = self.catalog.find_favorite(station.stationuuid)
        if favorite is None:
            self._set_status("[dim]Favorites only — press f first[/dim]")
            return
        station_uuid = station.stationuuid
        self.app.push_screen(
            RenameModal(favorite.station.name, current_name=favorite.display_name),
            lambda result: self._finish_rename(station_uuid, result),
        )

    def _finish_rename(self, station_uuid: str, result: str | None) -> None:
        if result is None:
            return
        self.catalog.rename_favorite(station_uuid, result)
        self._sync_catalog_lists()
        self._set_status(f"Favorite renamed: {result}", temporary=True)

    def action_play_selected(self) -> None:
        station_list = self._active_station_list()
        if station_list is None:
            return
        station = station_list.selected_station()
        if station is not None:
            self._play_station(station)

    @on(StationList.PlayRequested)
    def _on_station_play_requested(self, event: StationList.PlayRequested) -> None:
        station = event.list_view.station_at(event.index)
        if station is not None:
            self._play_station(station)

    def _play_station(self, station: Station) -> None:
        if not self.player or self._mpv_error:
            return
        self.player.play_station(station)
        self.catalog.record_play(station)
        self._refresh_history_list()
        self._render_player_state(self.player.state)
        self._register_click(station.stationuuid)

    def _refresh_history_list(self) -> None:
        history = self.query_one("#history-list", StationList)
        history.set_stations(self.catalog.history_stations())
        self._apply_favorite_markers("history-list")

    @on(ListView.Selected, "#station-list")
    @on(ListView.Selected, "#favorites-list")
    @on(ListView.Selected, "#history-list")
    def _on_station_list_selected(self, event: ListView.Selected) -> None:
        """Enter en la lista (ListView captura Enter antes que la pantalla)."""
        if event.index is None:
            return
        list_id = event.list_view.id
        if list_id is None:
            return
        station_list = self.query_one(f"#{list_id}", StationList)
        station = station_list.station_at(event.index)
        if station is not None:
            self._play_station(station)

    def action_toggle_pause(self) -> None:
        if self.player:
            self.player.toggle_pause()
            self._render_player_state(self.player.state)

    def action_volume_up(self) -> None:
        if self.player:
            self.player.adjust_volume(self.settings.volume_step)
            self._render_player_state(self.player.state, reveal_volume=True)

    def action_volume_down(self) -> None:
        if self.player:
            self.player.adjust_volume(-self.settings.volume_step)
            self._render_player_state(self.player.state, reveal_volume=True)

    @on(Input.Submitted, "#search-input")
    def _on_search_submitted(self, event: Input.Submitted) -> None:
        query = event.value
        search = event.input
        search.display = False
        search.blur()
        self._search_open = False
        self.refresh_bindings()
        self._run_search(query)
        self.call_after_refresh(self._focus_active_station_list)
