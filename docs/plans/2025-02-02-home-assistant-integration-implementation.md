# Home Assistant Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Home Assistant custom integration that exposes roon-now-playing screens as controllable entities.

**Architecture:** WebSocket-based coordinator pattern with select entities for layout/font/background/zone and binary sensor for connection status. Only named screens become HA entities.

**Tech Stack:** Python 3.11+, Home Assistant Core, aiohttp (async HTTP/WebSocket)

---

## Task 1: Repository Setup & Manifest

**Files:**
- Create: `custom_components/roon_now_playing/__init__.py`
- Create: `custom_components/roon_now_playing/manifest.json`
- Create: `custom_components/roon_now_playing/const.py`
- Create: `hacs.json`
- Create: `README.md`
- Create: `LICENSE`

**Step 1: Create directory structure**

```bash
mkdir -p custom_components/roon_now_playing/translations
```

**Step 2: Create manifest.json**

Create `custom_components/roon_now_playing/manifest.json`:

```json
{
  "domain": "roon_now_playing",
  "name": "Roon Now Playing",
  "codeowners": ["@arthursoares"],
  "config_flow": true,
  "dependencies": [],
  "documentation": "https://github.com/arthursoares/roon-now-playing-hass",
  "iot_class": "local_push",
  "issue_tracker": "https://github.com/arthursoares/roon-now-playing-hass/issues",
  "requirements": ["aiohttp>=3.8.0"],
  "version": "1.0.0"
}
```

**Step 3: Create const.py**

Create `custom_components/roon_now_playing/const.py`:

```python
"""Constants for the Roon Now Playing integration."""
from typing import Final

DOMAIN: Final = "roon_now_playing"

# Platforms
PLATFORMS: Final = ["select", "binary_sensor"]

# Configuration
CONF_HOST: Final = "host"

# Defaults
DEFAULT_PORT: Final = 3000

# Options for select entities (mirrored from roon-now-playing server)
LAYOUTS: Final = [
    "detailed",
    "minimal",
    "fullscreen",
    "ambient",
    "cover",
    "facts-columns",
    "facts-overlay",
    "facts-carousel",
    "basic",
]

FONTS: Final = [
    "system",
    "patua-one",
    "comfortaa",
    "noto-sans-display",
    "coda",
    "bellota-text",
    "big-shoulders",
    "inter",
    "roboto",
    "open-sans",
    "lato",
    "montserrat",
    "poppins",
    "source-sans-3",
    "nunito",
    "raleway",
    "work-sans",
]

BACKGROUNDS: Final = [
    "black",
    "white",
    "dominant",
    "gradient-radial",
    "gradient-linear",
    "gradient-linear-multi",
    "gradient-radial-corner",
    "gradient-mesh",
    "blur-subtle",
    "blur-heavy",
    "duotone",
    "posterized",
    "gradient-noise",
    "blur-grain",
]
```

**Step 4: Create minimal __init__.py**

Create `custom_components/roon_now_playing/__init__.py`:

```python
"""The Roon Now Playing integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Roon Now Playing from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    # Coordinator will be added in Task 3
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
```

**Step 5: Create hacs.json**

Create `hacs.json`:

```json
{
  "name": "Roon Now Playing",
  "render_readme": true
}
```

**Step 6: Create LICENSE**

Create `LICENSE`:

```
MIT License

Copyright (c) 2025 Arthur Soares

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

**Step 7: Create README.md**

Create `README.md`:

```markdown
# Roon Now Playing - Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Control your [Roon Now Playing](https://github.com/arthursoares/roon-now-playing) display screens from Home Assistant.

## Features

- Auto-discovers named screens from your Roon Now Playing server
- Control layout, font, background, and zone for each screen
- Real-time connection status
- WebSocket-based updates (no polling)

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three dots menu → Custom repositories
3. Add `https://github.com/arthursoares/roon-now-playing-hass` as an Integration
4. Search for "Roon Now Playing" and install
5. Restart Home Assistant

### Manual

1. Copy `custom_components/roon_now_playing` to your `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Go to Settings → Integrations → Add Integration
2. Search for "Roon Now Playing"
3. Enter your server URL (e.g., `http://192.168.1.50:3000`)

## Entities

For each **named** screen (screens with a friendly name set in the admin panel), you get:

| Entity | Type | Description |
|--------|------|-------------|
| `select.<name>_layout` | Select | Display layout |
| `select.<name>_font` | Select | Font family |
| `select.<name>_background` | Select | Background style |
| `select.<name>_zone` | Select | Roon zone |
| `binary_sensor.<name>_connected` | Binary Sensor | Connection status |

## Automation Examples

```yaml
# Switch to minimal layout at night
automation:
  trigger:
    - platform: time
      at: "22:00:00"
  action:
    - service: select.select_option
      target:
        entity_id: select.bedroom_display_layout
      data:
        option: "minimal"
```

## Requirements

- Roon Now Playing server v1.5.0+
- Home Assistant 2024.1.0+
```

**Step 8: Commit**

```bash
git add .
git commit -m "feat: initial repository setup with manifest and constants"
```

---

## Task 2: Config Flow (Setup UI)

**Files:**
- Create: `custom_components/roon_now_playing/config_flow.py`
- Create: `custom_components/roon_now_playing/strings.json`
- Create: `custom_components/roon_now_playing/translations/en.json`

**Step 1: Create config_flow.py**

Create `custom_components/roon_now_playing/config_flow.py`:

```python
"""Config flow for Roon Now Playing integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default="http://localhost:3000"): str,
    }
)


class RoonNowPlayingConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Roon Now Playing."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].rstrip("/")

            # Check if already configured
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            # Test connection
            try:
                await self._test_connection(host)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title="Roon Now Playing",
                    data={CONF_HOST: host},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def _test_connection(self, host: str) -> None:
        """Test if we can connect to the server."""
        session = async_get_clientsession(self.hass)
        try:
            async with session.get(
                f"{host}/api/health", timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status != 200:
                    raise CannotConnect
        except (aiohttp.ClientError, TimeoutError) as err:
            raise CannotConnect from err


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""
```

**Step 2: Create strings.json**

Create `custom_components/roon_now_playing/strings.json`:

```json
{
  "config": {
    "step": {
      "user": {
        "title": "Connect to Roon Now Playing",
        "description": "Enter the URL of your Roon Now Playing server.",
        "data": {
          "host": "Server URL"
        }
      }
    },
    "error": {
      "cannot_connect": "Failed to connect to server. Please check the URL and ensure the server is running.",
      "unknown": "Unexpected error occurred."
    },
    "abort": {
      "already_configured": "This server is already configured."
    }
  }
}
```

**Step 3: Create translations/en.json**

Create `custom_components/roon_now_playing/translations/en.json`:

```json
{
  "config": {
    "step": {
      "user": {
        "title": "Connect to Roon Now Playing",
        "description": "Enter the URL of your Roon Now Playing server.",
        "data": {
          "host": "Server URL"
        }
      }
    },
    "error": {
      "cannot_connect": "Failed to connect to server. Please check the URL and ensure the server is running.",
      "unknown": "Unexpected error occurred."
    },
    "abort": {
      "already_configured": "This server is already configured."
    }
  }
}
```

**Step 4: Commit**

```bash
git add .
git commit -m "feat: add config flow for server URL setup"
```

---

## Task 3: WebSocket Coordinator

**Files:**
- Create: `custom_components/roon_now_playing/coordinator.py`
- Modify: `custom_components/roon_now_playing/__init__.py`

**Step 1: Create coordinator.py**

Create `custom_components/roon_now_playing/coordinator.py`:

```python
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
```

**Step 2: Update __init__.py to use coordinator**

Replace `custom_components/roon_now_playing/__init__.py`:

```python
"""The Roon Now Playing integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .coordinator import RoonNowPlayingCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Roon Now Playing from a config entry."""
    coordinator = RoonNowPlayingCoordinator(hass, entry)

    # Start WebSocket connection
    await coordinator.async_start()

    # Wait briefly for initial data
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator: RoonNowPlayingCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Stop WebSocket connection
    await coordinator.async_stop()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
```

**Step 3: Commit**

```bash
git add .
git commit -m "feat: add WebSocket coordinator for real-time updates"
```

---

## Task 4: Binary Sensor Entity (Connected Status)

**Files:**
- Create: `custom_components/roon_now_playing/binary_sensor.py`

**Step 1: Create binary_sensor.py**

Create `custom_components/roon_now_playing/binary_sensor.py`:

```python
"""Binary sensor platform for Roon Now Playing."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import RoonNowPlayingCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensors from a config entry."""
    coordinator: RoonNowPlayingCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Track which clients we've added entities for
    tracked_clients: set[str] = set()

    @callback
    def async_add_new_entities() -> None:
        """Add entities for new named clients."""
        new_entities = []

        for client_id, client in coordinator.clients.items():
            if client_id not in tracked_clients:
                tracked_clients.add(client_id)
                new_entities.append(
                    RoonNowPlayingConnectedSensor(coordinator, client_id)
                )

        if new_entities:
            async_add_entities(new_entities)

    # Add initial entities
    async_add_new_entities()

    # Listen for new clients
    entry.async_on_unload(
        coordinator.async_add_listener(async_add_new_entities)
    )


class RoonNowPlayingConnectedSensor(
    CoordinatorEntity[RoonNowPlayingCoordinator], BinarySensorEntity
):
    """Binary sensor for screen connection status."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_has_entity_name = True
    _attr_name = "Connected"

    def __init__(
        self,
        coordinator: RoonNowPlayingCoordinator,
        client_id: str,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._client_id = client_id
        self._attr_unique_id = f"{client_id}_connected"

    @property
    def _client(self) -> dict | None:
        """Return the client data."""
        return self.coordinator._clients.get(self._client_id)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        client = self._client or {}
        return DeviceInfo(
            identifiers={(DOMAIN, self._client_id)},
            name=client.get("friendlyName", f"Display {self._client_id[:8]}"),
            manufacturer="Roon Now Playing",
            model="Display Screen",
        )

    @property
    def is_on(self) -> bool:
        """Return true if connected."""
        client = self._client
        if not client:
            return False
        return not client.get("_disconnected", False)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self._client is not None
```

**Step 2: Commit**

```bash
git add .
git commit -m "feat: add binary sensor for connection status"
```

---

## Task 5: Select Entities (Layout, Font, Background, Zone)

**Files:**
- Create: `custom_components/roon_now_playing/select.py`

**Step 1: Create select.py**

Create `custom_components/roon_now_playing/select.py`:

```python
"""Select platform for Roon Now Playing."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import BACKGROUNDS, DOMAIN, FONTS, LAYOUTS
from .coordinator import RoonNowPlayingCoordinator


@dataclass(frozen=True)
class RoonNowPlayingSelectDescription(SelectEntityDescription):
    """Describe a Roon Now Playing select entity."""

    options_key: str | None = None  # For dynamic options (zones)
    static_options: list[str] | None = None  # For static options


SELECT_TYPES: tuple[RoonNowPlayingSelectDescription, ...] = (
    RoonNowPlayingSelectDescription(
        key="layout",
        name="Layout",
        icon="mdi:page-layout-body",
        static_options=LAYOUTS,
    ),
    RoonNowPlayingSelectDescription(
        key="font",
        name="Font",
        icon="mdi:format-font",
        static_options=FONTS,
    ),
    RoonNowPlayingSelectDescription(
        key="background",
        name="Background",
        icon="mdi:palette",
        static_options=BACKGROUNDS,
    ),
    RoonNowPlayingSelectDescription(
        key="zone",
        name="Zone",
        icon="mdi:speaker",
        options_key="zones",  # Dynamic from coordinator
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up select entities from a config entry."""
    coordinator: RoonNowPlayingCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Track which clients we've added entities for
    tracked_clients: set[str] = set()

    @callback
    def async_add_new_entities() -> None:
        """Add entities for new named clients."""
        new_entities = []

        for client_id, client in coordinator.clients.items():
            if client_id not in tracked_clients:
                tracked_clients.add(client_id)
                for description in SELECT_TYPES:
                    new_entities.append(
                        RoonNowPlayingSelect(coordinator, client_id, description)
                    )

        if new_entities:
            async_add_entities(new_entities)

    # Add initial entities
    async_add_new_entities()

    # Listen for new clients
    entry.async_on_unload(
        coordinator.async_add_listener(async_add_new_entities)
    )


class RoonNowPlayingSelect(
    CoordinatorEntity[RoonNowPlayingCoordinator], SelectEntity
):
    """Select entity for Roon Now Playing settings."""

    entity_description: RoonNowPlayingSelectDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: RoonNowPlayingCoordinator,
        client_id: str,
        description: RoonNowPlayingSelectDescription,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._client_id = client_id
        self.entity_description = description
        self._attr_unique_id = f"{client_id}_{description.key}"

    @property
    def _client(self) -> dict | None:
        """Return the client data."""
        return self.coordinator._clients.get(self._client_id)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        client = self._client or {}
        return DeviceInfo(
            identifiers={(DOMAIN, self._client_id)},
            name=client.get("friendlyName", f"Display {self._client_id[:8]}"),
            manufacturer="Roon Now Playing",
            model="Display Screen",
        )

    @property
    def options(self) -> list[str]:
        """Return available options."""
        if self.entity_description.static_options:
            return list(self.entity_description.static_options)

        # Dynamic options (zones)
        if self.entity_description.options_key == "zones":
            return [zone["display_name"] for zone in self.coordinator.zones]

        return []

    @property
    def current_option(self) -> str | None:
        """Return current selected option."""
        client = self._client
        if not client:
            return None

        key = self.entity_description.key
        if key == "zone":
            return client.get("zoneName")
        return client.get(key)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        client = self._client
        if not client:
            return False
        return not client.get("_disconnected", False)

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        key = self.entity_description.key

        if key == "layout":
            await self.coordinator.async_push_settings(
                self._client_id, layout=option
            )
        elif key == "font":
            await self.coordinator.async_push_settings(
                self._client_id, font=option
            )
        elif key == "background":
            await self.coordinator.async_push_settings(
                self._client_id, background=option
            )
        elif key == "zone":
            # Find zone ID from name
            zone_id = None
            for zone in self.coordinator.zones:
                if zone["display_name"] == option:
                    zone_id = zone["id"]
                    break
            if zone_id:
                await self.coordinator.async_push_settings(
                    self._client_id, zone_id=zone_id
                )
```

**Step 2: Commit**

```bash
git add .
git commit -m "feat: add select entities for layout, font, background, zone"
```

---

## Task 6: Testing & Documentation

**Files:**
- Update: `README.md` (final polish)

**Step 1: Manual testing checklist**

Test the integration by:

1. Copy `custom_components/roon_now_playing` to Home Assistant's `custom_components/` folder
2. Restart Home Assistant
3. Go to Settings → Integrations → Add Integration
4. Search "Roon Now Playing"
5. Enter server URL (e.g., `http://192.168.1.50:3000`)
6. Verify named screens appear as devices
7. Test changing layout/font/background via HA
8. Test screen disconnect/reconnect updates binary sensor

**Step 2: Verify HACS compatibility**

Ensure these files exist with correct content:
- `hacs.json` - HACS metadata
- `custom_components/roon_now_playing/manifest.json` - version field present
- `README.md` - installation instructions

**Step 3: Final commit and push**

```bash
git add .
git commit -m "docs: finalize README and documentation"
git push -u origin main
```

---

## Summary

| Task | Description | Files |
|------|-------------|-------|
| 1 | Repository setup & manifest | `manifest.json`, `const.py`, `__init__.py`, etc. |
| 2 | Config flow (setup UI) | `config_flow.py`, `strings.json`, translations |
| 3 | WebSocket coordinator | `coordinator.py`, update `__init__.py` |
| 4 | Binary sensor (connected) | `binary_sensor.py` |
| 5 | Select entities (layout, font, background, zone) | `select.py` |
| 6 | Testing & documentation | Manual testing, HACS verification |
