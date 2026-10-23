"""Select platform for Roon Now Playing."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import BACKGROUNDS, DOMAIN, FONTS, LAYOUTS
from .coordinator import RoonNowPlayingCoordinator
from .identity import async_track_device_removals, device_identifier, entity_unique_id


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
                for description in SELECT_TYPES:
                    new_entities.append(
                        RoonNowPlayingSelect(
                            coordinator, screen_id, friendly_name, description
                        )
                    )

        if new_entities:
            async_add_entities(new_entities)

    # Add initial entities
    async_add_new_entities()

    # Listen for new clients
    entry.async_on_unload(coordinator.async_add_listener(async_add_new_entities))


class RoonNowPlayingSelect(CoordinatorEntity[RoonNowPlayingCoordinator], SelectEntity):
    """Select entity for Roon Now Playing settings."""

    entity_description: RoonNowPlayingSelectDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: RoonNowPlayingCoordinator,
        screen_id: str,
        friendly_name: str,
        description: RoonNowPlayingSelectDescription,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._friendly_name = friendly_name
        self._screen_id = screen_id
        self.entity_description = description
        self._attr_unique_id = entity_unique_id(
            coordinator.entry.entry_id, screen_id, description.key
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
        return self.coordinator.is_live(client)

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        client = self._client
        if not client or not self.coordinator.is_live(client):
            return

        client_id = client.get("clientId")
        if not client_id:
            return

        key = self.entity_description.key

        if key == "layout":
            await self.coordinator.async_push_settings(client_id, layout=option)
        elif key == "font":
            await self.coordinator.async_push_settings(client_id, font=option)
        elif key == "background":
            await self.coordinator.async_push_settings(client_id, background=option)
        elif key == "zone":
            # Find zone ID from name
            zone_id = None
            for zone in self.coordinator.zones:
                if zone["display_name"] == option:
                    zone_id = zone["id"]
                    break
            if zone_id:
                await self.coordinator.async_push_settings(client_id, zone_id=zone_id)
