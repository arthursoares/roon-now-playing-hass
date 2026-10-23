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
from .identity import async_track_device_removals, device_identifier, entity_unique_id


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensors from a config entry."""
    coordinator: RoonNowPlayingCoordinator = hass.data[DOMAIN][entry.entry_id]

    tracked_devices: set[str] = set()
    async_track_device_removals(hass, entry, tracked_devices)

    @callback
    def async_add_new_entities() -> None:
        """Add entities for new stable display identities."""
        new_entities = []

        for screen_id, client in coordinator.ready_displays.items():
            friendly_name = client.get("friendlyName")
            if screen_id not in tracked_devices:
                tracked_devices.add(screen_id)
                new_entities.append(
                    RoonNowPlayingConnectedSensor(coordinator, screen_id, friendly_name)
                )

        if new_entities:
            async_add_entities(new_entities)

    # Add initial entities
    async_add_new_entities()

    # Listen for new clients
    entry.async_on_unload(coordinator.async_add_listener(async_add_new_entities))


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
        screen_id: str,
        friendly_name: str,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._screen_id = screen_id
        self._friendly_name = friendly_name
        self._attr_unique_id = entity_unique_id(
            coordinator.entry.entry_id, screen_id, "connected"
        )

    @property
    def _client(self) -> dict | None:
        """Resolve the display's latest session by stable identity."""
        return self.coordinator.client_for_device(self._screen_id)

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={
                (
                    DOMAIN,
                    device_identifier(self.coordinator.entry.entry_id, self._screen_id),
                )
            },
            name=(self._client or {}).get("friendlyName", self._friendly_name),
            manufacturer="Roon Now Playing",
            model="Display Screen",
        )

    @property
    def is_on(self) -> bool:
        """Return true if connected."""
        client = self._client
        if not client:
            return False
        return self.coordinator.is_live(client)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.can_check_removal
