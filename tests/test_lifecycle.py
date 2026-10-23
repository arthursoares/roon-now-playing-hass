"""Regression tests using strict mocks of HA's actual registry callbacks."""

import ast
import asyncio
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import AsyncMock, patch

from tests.ha_mock import ConfigEntry, DeviceEntry, RegistryEntry, install, make_hass

install()

from custom_components.roon_now_playing import (  # noqa: E402
    async_migrate_entry,
    async_remove_config_entry_device,
    binary_sensor,
    select,
)
from custom_components.roon_now_playing.coordinator import RoonNowPlayingCoordinator  # noqa: E402
from custom_components.roon_now_playing.identity import (  # noqa: E402
    DOMAIN,
    ENTITY_KEYS,
    device_id,
    device_identifier,
    entity_unique_id,
    prepare_identity,
)


def client(screen="screen", name="Screen", session="one", **extra):
    return {
        "clientId": f"{screen}:{session}",
        "friendlyName": name,
        "isAdmin": False,
        "layout": "detailed",
        **extra,
    }


class LifecycleTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.hass = make_hass()
        self.entry = ConfigEntry()
        self.coordinator = RoonNowPlayingCoordinator(self.hass, self.entry)
        self.coordinator._connected = True
        self.hass.data = {DOMAIN: {self.entry.entry_id: self.coordinator}}
        self.store = self.hass.registry

    async def snapshot(self, *clients):
        await self.coordinator._handle_message(
            {"type": "clients_list", "clients": list(clients)}
        )

    async def event(self, kind, **data):
        await self.coordinator._handle_message({"type": kind, **data})

    async def platforms(self):
        self.selects, self.sensors = [], []
        await select.async_setup_entry(self.hass, self.entry, self.selects.extend)
        await binary_sensor.async_setup_entry(
            self.hass, self.entry, self.sensors.extend
        )

    def legacy(self, name="Screen", registry_id="old", entities=True):
        self.store.devices[registry_id] = DeviceEntry(
            registry_id, {(DOMAIN, name)}, name=name
        )
        if entities:
            for domain, keys in ENTITY_KEYS.items():
                for key in keys:
                    entity_id = f"{domain}.custom_{registry_id}_{key}"
                    self.store.entities[entity_id] = RegistryEntry(
                        entity_id,
                        f"{name.lower().replace(' ', '_')}_{key}",
                        registry_id,
                    )
        return self.store.devices[registry_id]

    def prepare(self, record=None, *others):
        record = record or client()
        return prepare_identity(
            self.hass,
            self.entry,
            device_id(record),
            record["friendlyName"],
            [record, *others],
        )

    async def test_admin_never_creates_entities_or_devices(self):
        await self.snapshot(client(isAdmin=True))
        await self.platforms()
        self.assertEqual(self.selects + self.sensors, [])
        for kind in ("client_connected", "client_updated"):
            await self.event(kind, client=client(isAdmin=True))
        self.assertEqual(self.selects + self.sensors, [])
        self.store.dr.async_update_device.assert_not_called()
        await self.event("client_connected", client=client("real"))
        self.assertEqual((len(self.selects), len(self.sensors)), (4, 1))

    async def test_rename_and_reconnect_reuse_entities_and_latest_push_target(self):
        self.legacy()
        await self.snapshot(client())
        await self.platforms()
        unique_ids = [e.unique_id for e in self.selects + self.sensors]
        old_device = self.store.devices["old"]
        await self.event("client_updated", client=client(name="New Screen"))
        await self.event(
            "client_connected",
            client=client(name="New Screen", session="two", layout="minimal"),
        )
        await self.event("client_disconnected", clientId="screen:one")
        self.assertEqual((len(self.selects), len(self.sensors)), (4, 1))
        self.assertEqual(unique_ids, [e.unique_id for e in self.selects + self.sensors])
        self.assertEqual(self.store.devices["old"].id, old_device.id)
        self.assertEqual(self.store.devices["old"].name, "New Screen")
        self.assertEqual(self.selects[0].current_option, "minimal")
        self.assertTrue(self.sensors[0].is_on)
        self.coordinator.async_push_settings = AsyncMock()
        await self.selects[0].async_select_option("detailed")
        self.coordinator.async_push_settings.assert_awaited_once_with(
            "screen:two", layout="detailed"
        )

    async def test_server_switches_back_to_older_remaining_session(self):
        await self.snapshot(client())
        await self.platforms()
        await self.event(
            "client_updated", client=client(session="two", layout="minimal")
        )
        self.assertEqual(self.selects[0]._client["clientId"], "screen:two")
        # Server closes tab two and reports tab one as the remaining session.
        await self.event("client_updated", client=client(layout="ambient"))
        self.assertEqual(self.selects[0]._client["clientId"], "screen:one")
        self.assertEqual(self.selects[0].current_option, "ambient")
        await self.event("client_disconnected", clientId="screen:one")
        self.assertFalse(self.sensors[0].is_on)
        self.assertFalse(self.selects[0].available)

    async def test_removed_stale_display_waits_for_reconnect(self):
        await self.snapshot(client())
        await self.platforms()
        await self.event("client_disconnected", clientId="screen:one")
        self.hass.bus.fire(
            "device_registry_updated",
            {
                "action": "remove",
                "device_id": "old",
                "device": {
                    "identifiers": [[DOMAIN, device_identifier("entry", "screen")]]
                },
            },
        )
        self.selects.clear()
        self.sensors.clear()
        await self.event("zones", zones=[])
        self.assertEqual(self.selects + self.sensors, [])
        await self.event("client_connected", client=client(session="two"))
        self.assertEqual((len(self.selects), len(self.sensors)), (4, 1))
        for unsubscribe in self.entry.unloads:
            unsubscribe()
        self.assertEqual(self.hass.bus.listeners["device_registry_updated"], [])

    async def test_stable_device_with_unmigrated_entity_defers(self):
        self.legacy()
        self.store.devices["old"] = replace(
            self.store.devices["old"],
            identifiers={(DOMAIN, device_identifier("entry", "screen"))},
        )
        self.assertFalse(self.prepare())
        self.store.er.async_update_entity.assert_not_called()

    async def test_both_stable_and_legacy_devices_defer(self):
        self.legacy()
        self.store.devices["stable"] = DeviceEntry(
            "stable", {(DOMAIN, device_identifier("entry", "screen"))}
        )
        self.assertFalse(self.prepare())
        self.store.er.async_update_entity.assert_not_called()

    async def test_admin_with_same_stable_id_does_not_displace_display(self):
        await self.snapshot(client())
        await self.platforms()
        await self.event(
            "client_connected", client=client(session="admin", isAdmin=True)
        )
        self.assertTrue(self.sensors[0].is_on)
        self.assertEqual(self.selects[0]._client["clientId"], "screen:one")

    async def test_same_name_new_displays_stay_distinct(self):
        await self.snapshot(client("first"), client("second"))
        await self.platforms()
        self.assertEqual((len(self.selects), len(self.sensors)), (8, 2))
        self.assertEqual(len({e.unique_id for e in self.selects + self.sensors}), 10)

    async def test_in_place_migration_preserves_customizations(self):
        before_device = self.legacy(name="Living Room")
        before_entities = self.store.entities.copy()
        self.assertTrue(self.prepare(client(name="Living Room")))
        after_device = self.store.devices["old"]
        self.assertEqual(
            after_device,
            replace(
                before_device,
                identifiers={(DOMAIN, device_identifier("entry", "screen"))},
            ),
        )
        for entity_id, old in before_entities.items():
            key = old.unique_id.rsplit("_", 1)[1]
            self.assertEqual(
                self.store.entities[entity_id],
                replace(old, unique_id=entity_unique_id("entry", "screen", key)),
            )
        self.assertTrue(self.prepare(client(name="Renamed")))
        self.assertEqual(len(self.store.devices), 1)
        self.assertEqual(len(self.store.entities), 5)

    async def test_platform_unique_ids_reuse_all_customized_registry_entries(self):
        self.legacy()
        previous = self.store.entities.copy()
        await self.snapshot(client())
        await self.platforms()
        actual = {
            self.store.er.async_get_entity_id("select", DOMAIN, entity.unique_id)
            for entity in self.selects
        }
        actual.update(
            self.store.er.async_get_entity_id("binary_sensor", DOMAIN, entity.unique_id)
            for entity in self.sensors
        )
        self.assertEqual(actual, set(previous))
        self.assertEqual(len(self.store.entities), 5)

    async def test_new_display_target_collision_does_not_reassign_entity(self):
        self.store.entities["select.foreign"] = RegistryEntry(
            "select.foreign",
            entity_unique_id("entry", "screen", "layout"),
            "some-other-device",
        )
        self.assertFalse(self.prepare())
        self.store.er.async_update_entity.assert_not_called()
        self.store.dr.async_update_device.assert_not_called()

    async def test_normalized_legacy_names_are_ambiguous(self):
        self.legacy("Living Room", "first")
        self.legacy("living_room", "second", entities=False)
        self.assertFalse(self.prepare(client(name="Living Room")))
        self.store.er.async_update_entity.assert_not_called()
        self.store.dr.async_update_device.assert_not_called()

    async def test_duplicate_reported_names_defer_migration_and_discovery(self):
        self.legacy()
        await self.snapshot(client("first"), client("second"))
        await self.platforms()
        self.assertEqual(self.selects + self.sensors, [])
        self.store.er.async_update_entity.assert_not_called()
        self.store.dr.async_update_device.assert_not_called()

    async def test_admin_name_collision_cannot_claim_display(self):
        self.legacy()
        self.assertFalse(self.prepare(client(), client("admin", isAdmin=True)))
        self.store.er.async_update_entity.assert_not_called()

    async def test_historical_rename_deferred_without_duplicates(self):
        self.legacy("Old name")
        await self.snapshot(client(name="New name"))
        await self.platforms()
        self.assertEqual(self.selects + self.sensors, [])
        self.assertEqual(len(self.store.devices), 1)
        self.assertEqual(len(self.store.entities), 5)

    async def test_offline_legacy_screen_migrates_when_it_returns(self):
        self.legacy()
        await self.snapshot()
        await self.platforms()
        self.assertEqual(self.selects + self.sensors, [])
        await self.event("client_connected", client=client())
        self.assertEqual((len(self.selects), len(self.sensors)), (4, 1))
        self.assertEqual(len(self.store.entities), 5)

    async def test_collision_preflight_never_partially_updates(self):
        self.legacy()
        target = entity_unique_id("entry", "screen", "zone")
        self.store.entities["select.collision"] = RegistryEntry(
            "select.collision", target, "other"
        )
        self.assertFalse(self.prepare())
        self.store.er.async_update_entity.assert_not_called()
        self.store.dr.async_update_device.assert_not_called()

    async def test_unknown_legacy_unique_id_defers_without_changes(self):
        self.legacy()
        old = self.store.entities["select.custom_old_zone"]
        self.store.entities[old.entity_id] = replace(
            old, unique_id="nonstandard_unique_id"
        )
        self.assertFalse(self.prepare())
        self.store.er.async_update_entity.assert_not_called()
        self.store.dr.async_update_device.assert_not_called()

    async def test_partially_updated_entities_can_resume(self):
        self.legacy()
        old = self.store.entities["select.custom_old_zone"]
        self.store.entities[old.entity_id] = replace(
            old, unique_id=entity_unique_id("entry", "screen", "zone")
        )
        self.assertTrue(self.prepare())
        self.assertEqual(len(self.store.entities), 5)

    async def test_shared_legacy_device_defers(self):
        old = self.legacy()
        self.store.devices[old.id] = replace(old, config_entries={"entry", "other"})
        self.assertFalse(self.prepare())
        self.store.er.async_update_entity.assert_not_called()

    async def test_foreign_legacy_entity_collision_defers(self):
        self.legacy(entities=False)
        self.store.entities["select.other"] = RegistryEntry(
            "select.other", "screen_layout", "other", "other"
        )
        self.assertFalse(self.prepare())
        self.store.dr.async_update_device.assert_not_called()

    async def test_orphan_entity_migration_retains_entity_id(self):
        self.store.entities["select.custom"] = RegistryEntry(
            "select.custom", "screen_layout", None
        )
        self.assertTrue(self.prepare())
        self.assertEqual(
            self.store.entities["select.custom"].unique_id,
            entity_unique_id("entry", "screen", "layout"),
        )
        self.assertEqual(len(self.store.entities), 1)

    async def test_removal_live_stale_admin_and_server_unavailable(self):
        stale = self.legacy("Retired", "retired", entities=False)
        live = DeviceEntry("live", {(DOMAIN, device_identifier("entry", "screen"))})
        old_live = DeviceEntry("old-live", {(DOMAIN, "Screen")})
        admin = DeviceEntry("admin", {(DOMAIN, "Admin tab")})
        await self.snapshot(client(), client("admin", "Admin tab", isAdmin=True))
        remove = async_remove_config_entry_device
        self.assertTrue(await remove(self.hass, self.entry, stale))
        self.assertTrue(await remove(self.hass, self.entry, admin))
        self.assertFalse(await remove(self.hass, self.entry, live))
        self.assertFalse(await remove(self.hass, self.entry, old_live))
        await self.event("client_disconnected", clientId="screen:one")
        self.assertTrue(await remove(self.hass, self.entry, live))
        self.coordinator._connected = False
        self.assertFalse(await remove(self.hass, self.entry, stale))
        self.coordinator._connected = True
        self.coordinator._has_snapshot = False
        self.assertFalse(await remove(self.hass, self.entry, stale))
        self.hass.data[DOMAIN].clear()
        self.assertFalse(await remove(self.hass, self.entry, stale))

    async def test_live_unnamed_display_still_blocks_stable_device_removal(self):
        await self.snapshot(client(name=None))
        live = DeviceEntry("live", {(DOMAIN, device_identifier("entry", "screen"))})
        self.assertFalse(
            await async_remove_config_entry_device(self.hass, self.entry, live)
        )

    async def test_clean_websocket_close_marks_cached_entities_unavailable(self):
        await self.snapshot(client())
        await self.platforms()
        self.hass.session = object()
        self.coordinator._connect_and_listen = AsyncMock()
        with patch(
            "custom_components.roon_now_playing.coordinator.asyncio.sleep",
            side_effect=asyncio.CancelledError,
        ):
            with self.assertRaises(asyncio.CancelledError):
                await self.coordinator._ws_loop()
        self.assertFalse(self.selects[0].available)
        self.assertFalse(self.sensors[0].available)
        self.assertFalse(self.sensors[0].is_on)
        self.assertFalse(self.coordinator.can_check_removal)

    async def test_admin_conversion_cannot_receive_settings(self):
        await self.snapshot(client())
        await self.platforms()
        await self.event("client_updated", client=client(isAdmin=True))
        self.coordinator.async_push_settings = AsyncMock()
        await self.selects[0].async_select_option("minimal")
        self.coordinator.async_push_settings.assert_not_awaited()
        self.assertFalse(self.sensors[0].is_on)

    async def test_v1_entry_migration_preserves_config_and_defers_registry(self):
        self.entry.version = 1
        data, options = self.entry.data.copy(), self.entry.options.copy()
        before = self.legacy()
        self.assertTrue(await async_migrate_entry(self.hass, self.entry))
        self.assertEqual((self.entry.version, self.entry.minor_version), (2, 1))
        self.assertEqual((self.entry.data, self.entry.options), (data, options))
        self.assertEqual(self.store.devices["old"], before)
        self.store.dr.async_update_device.assert_not_called()
        await self.snapshot(client())
        await self.platforms()
        self.assertEqual((len(self.selects), len(self.sensors)), (4, 1))

    async def test_version_rollback_guard_and_forward_minor(self):
        self.entry.version = 3
        self.assertFalse(await async_migrate_entry(self.hass, self.entry))
        self.assertEqual(self.entry.version, 3)
        self.entry.version, self.entry.minor_version = 2, 9
        self.assertTrue(await async_migrate_entry(self.hass, self.entry))
        self.assertEqual(self.entry.minor_version, 9)
        flow = ast.parse(
            Path("custom_components/roon_now_playing/config_flow.py").read_text()
        )
        cls = next(n for n in flow.body if isinstance(n, ast.ClassDef))
        self.assertTrue(
            any(
                isinstance(n, ast.Assign)
                and isinstance(n.targets[0], ast.Name)
                and n.targets[0].id == "VERSION"
                and n.value.value == 2
                for n in cls.body
            )
        )

    def test_explicit_and_documented_old_client_id_contract(self):
        self.assertEqual(
            device_id({"deviceId": "explicit:device", "clientId": "other:session"}),
            "explicit:device",
        )
        self.assertEqual(device_id({"clientId": "persistent:session"}), "persistent")
        self.assertEqual(
            device_id({"clientId": "old-client-without-colon"}),
            "old-client-without-colon",
        )
        self.assertIsNone(device_id({"friendlyName": "Not an ID"}))
        self.assertIsNone(device_id({"clientId": None}))
        self.assertNotEqual(
            entity_unique_id("a", "screen", "layout"),
            entity_unique_id("b", "screen", "layout"),
        )


if __name__ == "__main__":
    unittest.main()
