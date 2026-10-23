"""DataUpdateCoordinator for Roon Now Playing."""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib.parse import urlparse

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .identity import device_id, prepare_identity

_LOGGER = logging.getLogger(__name__)

RECONNECT_INTERVAL = 5  # seconds


class RoonNowPlayingCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage WebSocket connection and data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
        )
        self.entry = entry
        self.host: str = entry.data[CONF_HOST]
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._ws_task: asyncio.Task | None = None
        self._clients: dict[str, dict[str, Any]] = {}
        self._zones: list[dict[str, str]] = []
        self._connected = False
        self._has_snapshot = False

    @property
    def clients(self) -> dict[str, dict[str, Any]]:
        """Return named display sessions, excluding administrative clients."""
        return {
            client_id: client
            for client_id, client in self._clients.items()
            if client.get("friendlyName") and not client.get("isAdmin")
        }

    @property
    def displays(self) -> dict[str, dict[str, Any]]:
        """Return the server-selected session per stable display identity."""
        displays = {}
        for client in self.clients.values():
            screen_id = device_id(client)
            if screen_id is None:
                continue
            previous = displays.get(screen_id)
            if previous is None or not client.get("_disconnected", False):
                displays[screen_id] = client
        return displays

    def client_for_device(self, screen_id: str) -> dict[str, Any] | None:
        """Resolve a current session without using its mutable friendly name."""
        return self.displays.get(screen_id)

    @property
    def ready_displays(self) -> dict[str, dict[str, Any]]:
        """Prepare registries before either platform can create entities."""
        if not self._has_snapshot:
            return {}
        return {
            screen_id: client
            for screen_id, client in self.displays.items()
            if self.is_live(client)
            and prepare_identity(
                self.hass,
                self.entry,
                screen_id,
                client["friendlyName"],
                list(self._clients.values()),
            )
        }

    def is_live(self, client: dict[str, Any]) -> bool:
        """A cached client is not live when the server connection has gone away."""
        return (
            self._connected
            and self._has_snapshot
            and not client.get("_disconnected", False)
        )

    @property
    def can_check_removal(self) -> bool:
        """Require a complete, current server snapshot before deleting devices."""
        return self._connected and self._has_snapshot

    @property
    def zones(self) -> list[dict[str, str]]:
        """Return available zones."""
        return self._zones

    async def async_start(self) -> None:
        """Start the WebSocket connection."""
        self._ws_task = asyncio.create_task(self._ws_loop())

    async def async_stop(self) -> None:
        """Stop the WebSocket connection."""
        if self._ws_task:
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass
        if self._ws:
            await self._ws.close()

    async def _ws_loop(self) -> None:
        """Main WebSocket loop with reconnection."""
        session = async_get_clientsession(self.hass)

        while True:
            try:
                await self._connect_and_listen(session)
            except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                _LOGGER.warning("WebSocket connection failed: %s", err)
            except asyncio.CancelledError:
                break
            finally:
                self._connected = False
                self._has_snapshot = False
                self.async_set_updated_data(self._clients)

            _LOGGER.info("Reconnecting in %s seconds...", RECONNECT_INTERVAL)
            await asyncio.sleep(RECONNECT_INTERVAL)

    async def _connect_and_listen(self, session: aiohttp.ClientSession) -> None:
        """Connect to WebSocket and listen for messages."""
        parsed = urlparse(self.host)
        ws_scheme = "wss" if parsed.scheme == "https" else "ws"
        ws_url = f"{ws_scheme}://{parsed.netloc}/ws?admin=true"
        _LOGGER.info("Connecting to %s", ws_url)

        async with session.ws_connect(
            ws_url, timeout=aiohttp.ClientTimeout(total=30)
        ) as ws:
            self._ws = ws
            self._connected = True
            self._has_snapshot = False
            _LOGGER.info("WebSocket connected")

            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        await self._handle_message(msg.json())
                    except ValueError as err:
                        _LOGGER.warning("Failed to parse WebSocket message: %s", err)
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    _LOGGER.error("WebSocket error: %s", ws.exception())
                    break
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    _LOGGER.info("WebSocket closed")
                    break

    async def _handle_message(self, data: dict[str, Any]) -> None:
        """Handle incoming WebSocket message."""
        msg_type = data.get("type")

        if msg_type == "clients_list":
            # Full refresh of clients
            self._clients = {
                client["clientId"]: client for client in data.get("clients", [])
            }
            self._has_snapshot = True
            _LOGGER.debug("Received clients list: %d clients", len(self._clients))

        elif msg_type in ("client_connected", "client_updated"):
            # The server reports its representative session for this device.
            # It may switch back to an older session when a newer tab closes.
            client = data.get("client", {})
            client_id = client.get("clientId")
            if client_id:
                screen_id = device_id(client)
                if screen_id and not client.get("isAdmin"):
                    for previous in self._clients.values():
                        if (
                            not previous.get("isAdmin")
                            and device_id(previous) == screen_id
                        ):
                            previous["_disconnected"] = True
                self._clients[client_id] = client
                _LOGGER.debug("Client session updated: %s", client_id)

        elif msg_type == "client_disconnected":
            client_id = data.get("clientId")
            if client_id and client_id in self._clients:
                self._clients[client_id]["_disconnected"] = True
                _LOGGER.debug("Client disconnected: %s", client_id)

        elif msg_type == "zones":
            # Zone list updated
            self._zones = data.get("zones", [])
            _LOGGER.debug("Received zones: %d zones", len(self._zones))

        # Notify entities of update
        self.async_set_updated_data(self._clients)

    async def async_push_settings(
        self,
        client_id: str,
        layout: str | None = None,
        font: str | None = None,
        background: str | None = None,
        zone_id: str | None = None,
    ) -> bool:
        """Push settings to a client via REST API."""
        session = async_get_clientsession(self.hass)
        url = f"{self.host}/api/admin/clients/{client_id}/push"

        payload: dict[str, Any] = {}
        if layout is not None:
            payload["layout"] = layout
        if font is not None:
            payload["font"] = font
        if background is not None:
            payload["background"] = background
        if zone_id is not None:
            payload["zoneId"] = zone_id

        try:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    _LOGGER.debug("Pushed settings to %s: %s", client_id, payload)
                    return True
                _LOGGER.error("Failed to push settings: %s", response.status)
                return False
        except aiohttp.ClientError as err:
            _LOGGER.error("Error pushing settings: %s", err)
            return False

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data - not used since we use WebSocket push."""
        return self._clients
