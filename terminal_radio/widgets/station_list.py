"""Lista de estaciones en la TUI."""

from __future__ import annotations

from textual import events, on
from textual.message import Message
from textual.widgets import Label, ListItem, ListView

from terminal_radio.debug.perf import perf
from terminal_radio.models.station import Station


class StationList(ListView):
    """ListView con estaciones y selección por teclado."""

    class PlayRequested(Message):
        """Doble clic en una estación (equivalente a Enter / p)."""

        def __init__(self, list_view: StationList, index: int) -> None:
            super().__init__()
            self.list_view = list_view
            self.index = index

        @property
        def control(self) -> StationList:
            return self.list_view

    DEFAULT_CSS = """
    StationList {
        height: 1fr;
        border: solid $primary;
        scrollbar-size-vertical: 1;
    }
    StationList > ListItem {
        height: 1;
    }
    StationList > ListItem.-active > Label {
        color: $success;
        text-style: bold;
    }
    StationList > ListItem.-paused > Label {
        color: $warning;
        text-style: bold;
    }
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._stations: list[Station] = []
        self._favorite_uuids: set[str] = set()
        self._display_names: dict[str, str] = {}
        self._active_uuid: str | None = None
        self._active_playing = False

    @property
    def stations(self) -> list[Station]:
        return list(self._stations)

    def set_favorite_uuids(self, uuids: set[str]) -> None:
        self._favorite_uuids = set(uuids)
        if self._stations:
            self._refresh_all_rows()

    def set_display_names(self, names: dict[str, str]) -> None:
        self._display_names = dict(names)
        if self._stations:
            self._refresh_all_rows()

    def set_stations(self, stations: list[Station]) -> None:
        active_uuid = self._active_uuid
        active_playing = self._active_playing
        self._stations = list(stations)
        self.clear()
        if not stations:
            return
        items = [
            ListItem(Label(self._line_for_station(station), markup=True))
            for station in stations
        ]
        self.mount(*items)
        if active_uuid:
            self.call_after_refresh(
                lambda: self.set_playback(active_uuid, is_playing=active_playing)
            )
        self.call_after_refresh(self.select_first)

    def set_playback(self, station_uuid: str | None, *, is_playing: bool) -> None:
        """Marca la estación en reproducción (o en pausa) en la lista."""
        self._active_uuid = station_uuid
        self._active_playing = is_playing if station_uuid else False
        if not self._stations:
            return
        self.call_after_refresh(self._refresh_all_rows)

    def _line_for_station(self, station: Station) -> str:
        display_name = self._display_names.get(station.stationuuid)
        return station.format_list_line(
            favorite=station.stationuuid in self._favorite_uuids,
            active=station.stationuuid == self._active_uuid,
            playing=station.stationuuid == self._active_uuid and self._active_playing,
            display_name=display_name,
        )

    def _refresh_all_rows(self) -> None:
        count = min(len(self._stations), len(self._nodes))
        if perf.enabled:
            perf.count("ui.station_list_playback_refresh")
            perf.note("station_list_active_uuid", self._active_uuid or "(ninguna)")
            perf.note("station_list_active_playing", str(self._active_playing))
        for index in range(count):
            station = self._stations[index]
            list_item = self._nodes[index]
            label = list_item.query_one(Label)
            label.update(self._line_for_station(station))
            active = station.stationuuid == self._active_uuid
            list_item.set_class(active, "-active")
            list_item.set_class(active and not self._active_playing, "-paused")

    def select_first(self) -> None:
        """Resalta el primer ítem (tras mount async o al recuperar foco)."""
        if not self._stations:
            self.index = None
            return
        self.index = None
        self.index = 0

    def selected_station(self) -> Station | None:
        if not self._stations or self.index is None:
            return None
        if self.index < 0 or self.index >= len(self._stations):
            return None
        return self._stations[self.index]

    def station_at(self, index: int) -> Station | None:
        if index < 0 or index >= len(self._stations):
            return None
        return self._stations[index]

    @on(events.Click)
    def _on_double_click(self, event: events.Click) -> None:
        if event.chain != 2 or self.index is None:
            return
        self.post_message(self.PlayRequested(self, self.index))
