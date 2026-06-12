"""Cliente async para la API radio-browser."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from terminal_radio import __version__
from terminal_radio.models.station import Station

logger = logging.getLogger(__name__)

API_SERVERS = (
    "https://de1.api.radio-browser.info",
    "https://nl1.api.radio-browser.info",
    "https://at1.api.radio-browser.info",
)

USER_AGENT = f"TerminalRadio/{__version__}"
DEFAULT_TIMEOUT = 15.0
DEFAULT_LIMIT = 50


class RadioBrowserError(Exception):
    """Error de red o API con mensaje apto para mostrar en TUI."""


class RadioBrowserClient:
    """Cliente HTTP con rotación de servidores y reintentos."""

    def __init__(
        self,
        *,
        client: httpx.AsyncClient | None = None,
        servers: tuple[str, ...] = API_SERVERS,
    ) -> None:
        self._servers = servers
        self._server_index = 0
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT},
            timeout=DEFAULT_TIMEOUT,
            follow_redirects=True,
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    def _next_server(self) -> str:
        server = self._servers[self._server_index]
        self._server_index = (self._server_index + 1) % len(self._servers)
        return server

    async def _get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        last_error: Exception | None = None
        for _ in range(len(self._servers)):
            base = self._next_server()
            url = f"{base}{path}"
            try:
                response = await self._client.get(
                    url,
                    params=params,
                    headers={"User-Agent": USER_AGENT},
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as exc:
                last_error = exc
                logger.warning("Fallo en %s: %s", url, exc)
        raise RadioBrowserError(
            _friendly_network_message(last_error)
        ) from last_error

    async def _post(self, path: str) -> None:
        last_error: Exception | None = None
        for _ in range(len(self._servers)):
            base = self._next_server()
            url = f"{base}{path}"
            try:
                response = await self._client.post(
                    url,
                    headers={"User-Agent": USER_AGENT},
                )
                response.raise_for_status()
                return
            except httpx.HTTPError as exc:
                last_error = exc
                logger.warning("Fallo en %s: %s", url, exc)
        raise RadioBrowserError(
            _friendly_network_message(last_error)
        ) from last_error

    async def search(self, name: str, *, limit: int = DEFAULT_LIMIT) -> list[Station]:
        """Busca estaciones por nombre."""
        query = name.strip()
        if not query:
            return []
        data = await self._get_json(
            "/json/stations/search",
            {
                "name": query,
                "limit": limit,
                "hidebroken": "true",
                "order": "votes",
                "reverse": "true",
            },
        )
        return _parse_stations(data)

    async def top_voted(self, *, limit: int = DEFAULT_LIMIT) -> list[Station]:
        """Estaciones más votadas (catálogo inicial)."""
        data = await self._get_json(
            "/json/stations/topvote",
            {"limit": limit, "hidebroken": "true"},
        )
        return _parse_stations(data)

    async def click(self, stationuuid: str) -> None:
        """Registra un click al reproducir (buena práctica con la API)."""
        uuid = stationuuid.strip()
        if not uuid:
            return
        try:
            await self._post(f"/json/url/{uuid}")
        except RadioBrowserError:
            logger.warning("No se pudo registrar click para %s", uuid)


def _parse_stations(data: Any) -> list[Station]:
    if not isinstance(data, list):
        return []
    stations: list[Station] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            stations.append(Station.from_api(item))
        except Exception:
            logger.debug("Estación ignorada por datos inválidos", exc_info=True)
    return stations


def _friendly_network_message(exc: Exception | None) -> str:
    if exc is None:
        return "Could not connect to radio-browser."
    if isinstance(exc, httpx.TimeoutException):
        return "Timed out while fetching stations."
    if isinstance(exc, httpx.HTTPStatusError):
        return f"Server error ({exc.response.status_code})."
    return "Could not connect to radio-browser."
