"""The Roon Now Playing integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry

from .const import DOMAIN, PLATFORMS
from .coordinator import RoonNowPlayingCoordinator
from .identity import device_id, device_identifier

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


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Guard registry identity changes against loading old integration code.

    Live metadata needed for legacy name matching arrives later; the coordinator
    completes each registry migration before creating that display's entities.
    """
    if entry.version > 2:
        return False
    if entry.version == 1:
        hass.config_entries.async_update_entry(entry, version=2, minor_version=1)
    return entry.version == 2


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: ConfigEntry, device_entry: DeviceEntry
) -> bool:
    """Allow explicit removal of stale devices, refuse live displays.

    An unavailable server cannot establish that a display is stale. Old admin
    devices are removable because administrative clients never count as displays.
    """
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if coordinator is None or not coordinator.can_check_removal:
        return False
    for client in coordinator._clients.values():
        if client.get("isAdmin") or not coordinator.is_live(client):
            continue
        identifiers = set()
        screen_id = device_id(client)
        if screen_id:
            identifiers.add((DOMAIN, device_identifier(entry.entry_id, screen_id)))
        if client.get("friendlyName"):
            identifiers.add((DOMAIN, client["friendlyName"]))
        if device_entry.identifiers & identifiers:
            return False
    return True
