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
