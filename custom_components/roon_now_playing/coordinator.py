"""DataUpdateCoordinator for Roon Now Playing."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN

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

    @property
    def clients(self) -> dict[str, dict[str, Any]]:
        """Return current clients (only named ones)."""
        return {
            client_id: client
            for client_id, client in self._clients.items()
            if client.get("friendlyName")
        }

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
                self._connected = False
                self.async_set_updated_data(self._clients)
            except asyncio.CancelledError:
                break

            _LOGGER.info("Reconnecting in %s seconds...", RECONNECT_INTERVAL)
            await asyncio.sleep(RECONNECT_INTERVAL)

    async def _connect_and_listen(self, session: aiohttp.ClientSession) -> None:
        """Connect to WebSocket and listen for messages."""
        ws_url = f"{self.host.replace('http', 'ws')}/ws?admin=true"
        _LOGGER.info("Connecting to %s", ws_url)

        async with session.ws_connect(ws_url) as ws:
            self._ws = ws
            self._connected = True
            _LOGGER.info("WebSocket connected")

            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    await self._handle_message(msg.json())
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
                client["clientId"]: client
                for client in data.get("clients", [])
            }
            _LOGGER.debug("Received clients list: %d clients", len(self._clients))

        elif msg_type == "client_connected":
            # New client connected
            client = data.get("client", {})
            client_id = client.get("clientId")
            if client_id:
                self._clients[client_id] = client
                _LOGGER.debug("Client connected: %s", client.get("friendlyName", client_id))

        elif msg_type == "client_disconnected":
            # Client disconnected
            client_id = data.get("clientId")
            if client_id and client_id in self._clients:
                # Mark as disconnected but keep in dict for entity updates
                self._clients[client_id]["_disconnected"] = True
                _LOGGER.debug("Client disconnected: %s", client_id)

        elif msg_type == "client_updated":
            # Client settings changed
            client = data.get("client", {})
            client_id = client.get("clientId")
            if client_id:
                self._clients[client_id] = client
                _LOGGER.debug("Client updated: %s", client.get("friendlyName", client_id))

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
