"""Small HA import stubs and strict synchronous registry API mocks.

Signatures checked against home-assistant/core, tag 2026.10.1:
homeassistant/helpers/{entity_registry,device_registry}.py.
These tests exercise integration code, not the full HA platform lifecycle.
"""

import sys
from dataclasses import dataclass, field, replace
from types import ModuleType, SimpleNamespace
from unittest.mock import create_autospec


def module(name, **attributes):
    obj = ModuleType(name)
    obj.__dict__.update(attributes)
    sys.modules[name] = obj
    return obj


@dataclass(frozen=True)
class DeviceEntry:
    id: str
    identifiers: set
    config_entries: set = field(default_factory=lambda: {"entry"})
    name: str = "Screen"
    name_by_user: str = "My customized display"
    area_id: str = "bedroom"
    disabled_by: str | None = "user"


@dataclass(frozen=True)
class RegistryEntry:
    entity_id: str
    unique_id: str
    device_id: str | None
    config_entry_id: str = "entry"
    platform: str = "roon_now_playing"
    name: str = "Custom entity name"
    disabled_by: str | None = "user"
    hidden_by: str | None = "user"
    area_id: str = "bedroom"
    icon: str = "mdi:test-tube"
    options: dict = field(default_factory=lambda: {"test": {"option": 1}})

    @property
    def domain(self):
        return self.entity_id.split(".")[0]


class EntityRegistryAPI:
    def async_get(self, entity_id): ...
    def async_get_entity_id(self, domain, platform, unique_id): ...
    def async_update_entity(self, entity_id, *, new_unique_id): ...


class DeviceRegistryAPI:
    def async_update_device(self, device_id, *, new_identifiers=None, name=None): ...


class RegistryStore:
    def __init__(self):
        self.devices = {}
        self.entities = {}
        self.er = create_autospec(EntityRegistryAPI, instance=True, spec_set=True)
        self.dr = create_autospec(DeviceRegistryAPI, instance=True, spec_set=True)
        self.er.async_get.side_effect = self.entities.get
        self.er.async_get_entity_id.side_effect = self.get_entity_id
        self.er.async_update_entity.side_effect = self.update_entity
        self.dr.async_update_device.side_effect = self.update_device

    def get_entity_id(self, domain, platform, unique_id):
        return next(
            (
                e.entity_id
                for e in self.entities.values()
                if (e.domain, e.platform, e.unique_id) == (domain, platform, unique_id)
            ),
            None,
        )

    def update_entity(self, entity_id, *, new_unique_id):
        old = self.entities[entity_id]
        collision = self.get_entity_id(old.domain, old.platform, new_unique_id)
        if collision and collision != entity_id:
            raise ValueError("unique ID collision")
        self.entities[entity_id] = replace(old, unique_id=new_unique_id)
        return self.entities[entity_id]

    def update_device(self, device_id, *, new_identifiers=None, name=None):
        updates = {}
        if new_identifiers is not None:
            updates["identifiers"] = new_identifiers
        if name is not None:
            updates["name"] = name
        self.devices[device_id] = replace(self.devices[device_id], **updates)
        return self.devices[device_id]


class ConfigEntry:
    def __init__(self, version=2, minor_version=1, entry_id="entry"):
        self.entry_id = entry_id
        self.data = {"host": "http://example.test:3000"}
        self.options = {"untouched": True}
        self.version = version
        self.minor_version = minor_version
        self.unloads = []

    def async_on_unload(self, callback):
        self.unloads.append(callback)


class ConfigEntries:
    def async_update_entry(self, entry, *, version, minor_version):
        entry.version = version
        entry.minor_version = minor_version


class Coordinator:
    def __class_getitem__(cls, item):
        return cls

    def __init__(self, hass, *args, **kwargs):
        self.hass = hass
        self.listeners = []

    def async_add_listener(self, listener):
        self.listeners.append(listener)
        return lambda: self.listeners.remove(listener)

    def async_set_updated_data(self, data):
        self.data = data
        for listener in list(self.listeners):
            listener()


class CoordinatorEntity:
    def __class_getitem__(cls, item):
        return cls

    def __init__(self, coordinator):
        self.coordinator = coordinator

    @property
    def unique_id(self):
        return self._attr_unique_id


@dataclass(frozen=True)
class SelectEntityDescription:
    key: str
    name: str
    icon: str


def install():
    module("homeassistant")
    module("homeassistant.config_entries", ConfigEntry=ConfigEntry)
    module("homeassistant.core", HomeAssistant=SimpleNamespace, callback=lambda f: f)
    module("homeassistant.const", CONF_HOST="host")
    module("homeassistant.helpers")
    dr = module(
        "homeassistant.helpers.device_registry",
        DeviceEntry=DeviceEntry,
        EVENT_DEVICE_REGISTRY_UPDATED="device_registry_updated",
        async_get=lambda hass: hass.registry.dr,
        async_entries_for_config_entry=lambda registry, entry_id: [
            d
            for d in STORE_BY_DR[id(registry)].devices.values()
            if entry_id in d.config_entries
        ],
    )
    er = module(
        "homeassistant.helpers.entity_registry",
        async_get=lambda hass: hass.registry.er,
        async_entries_for_config_entry=lambda registry, entry_id: [
            e
            for e in STORE_BY_ER[id(registry)].entities.values()
            if e.config_entry_id == entry_id
        ],
    )
    sys.modules["homeassistant.helpers"].device_registry = dr
    sys.modules["homeassistant.helpers"].entity_registry = er
    module(
        "homeassistant.helpers.update_coordinator",
        DataUpdateCoordinator=Coordinator,
        CoordinatorEntity=CoordinatorEntity,
    )
    module("homeassistant.helpers.entity", DeviceInfo=dict)
    module("homeassistant.helpers.entity_platform", AddEntitiesCallback=object)
    module(
        "homeassistant.helpers.aiohttp_client",
        async_get_clientsession=lambda hass: hass.session,
    )
    module("homeassistant.components")
    module(
        "homeassistant.components.select",
        SelectEntity=type("SelectEntity", (), {}),
        SelectEntityDescription=SelectEntityDescription,
    )
    module(
        "homeassistant.components.binary_sensor",
        BinarySensorEntity=type("BinarySensorEntity", (), {}),
        BinarySensorDeviceClass=SimpleNamespace(CONNECTIVITY="connectivity"),
    )


class EventBus:
    def __init__(self):
        self.listeners = {}

    def async_listen(self, event_type, listener):
        self.listeners.setdefault(event_type, []).append(listener)
        return lambda: self.listeners[event_type].remove(listener)

    def fire(self, event_type, data):
        for listener in list(self.listeners.get(event_type, ())):
            listener(SimpleNamespace(data=data))


STORE_BY_DR = {}
STORE_BY_ER = {}


def make_hass():
    store = RegistryStore()
    STORE_BY_DR[id(store.dr)] = store
    STORE_BY_ER[id(store.er)] = store
    return SimpleNamespace(
        registry=store, data={}, config_entries=ConfigEntries(), bus=EventBus()
    )
