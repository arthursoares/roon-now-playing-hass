"""Stable screen identity and conservative, in-place legacy registry migration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
ENTITY_KEYS = {
    "select": ("layout", "font", "background", "zone"),
    "binary_sensor": ("connected",),
}


def device_id(client: dict[str, Any]) -> str | None:
    """Use metadata or the server's documented extractDeviceId contract.

    packages/server/src/websocket.ts: clientId is deviceId:sessionSuffix;
    extractDeviceId takes the prefix before the first colon, or the whole ID
    when no colon exists. Do not derive identity from a friendly name.
    """
    explicit = client.get("deviceId")
    if isinstance(explicit, str) and explicit:
        return explicit
    client_id = client.get("clientId")
    if not isinstance(client_id, str) or not client_id:
        return None
    colon = client_id.find(":")
    return client_id[:colon] if colon > 0 else client_id


def device_identifier(entry_id: str, screen_id: str) -> str:
    """Namespace screens by server/config entry, including across HA versions."""
    return f"{entry_id}:device:{screen_id}"


def entity_unique_id(entry_id: str, screen_id: str, key: str) -> str:
    """Return a name-independent entity ID scoped to this server."""
    return f"{device_identifier(entry_id, screen_id)}:{key}"


def legacy_prefix(name: str) -> str:
    """Match the exact normalization used by integration versions through 1.0.2."""
    return name.lower().replace(" ", "_")


def _owned_only_by(device: dr.DeviceEntry, entry_id: str) -> bool:
    """Support both the old shared registry and the newer per-entry registry."""
    owner = getattr(device, "config_entry_id", None)
    if owner is not None:
        return owner == entry_id
    return device.config_entries == {entry_id}


def prepare_identity(
    hass, entry, screen_id: str, name: str, clients: list[dict]
) -> bool:
    """Migrate only an unambiguous name match, before platforms create entities.

    A historical rename cannot be inferred from a name-only registry. Unknown
    screens wait while unresolved legacy records exist. No records are deleted.
    Calls are synchronous HA registry callbacks, so preflight and updates cannot
    interleave with another coordinator callback.
    """
    devices = dr.async_get(hass)
    entities = er.async_get(hass)
    own_devices = dr.async_entries_for_config_entry(devices, entry.entry_id)
    own_entities = er.async_entries_for_config_entry(entities, entry.entry_id)
    stable = (DOMAIN, device_identifier(entry.entry_id, screen_id))
    prefix = f"{entry.entry_id}:device:"
    stable_devices = [d for d in own_devices if stable in d.identifiers]
    legacy_devices = [
        d
        for d in own_devices
        if any(
            domain == DOMAIN and not value.startswith(prefix)
            for domain, value in d.identifiers
        )
    ]
    legacy_entities = [
        e
        for e in own_entities
        if e.platform == DOMAIN and not e.unique_id.startswith(prefix)
    ]
    candidates = [d for d in legacy_devices if (DOMAIN, name) in d.identifiers]

    def defer(reason: str) -> bool:
        # Deduplicate warning messages while leaving the reason visible by default.
        warnings = getattr(hass, "data", {}).setdefault(
            f"{DOMAIN}_identity_warnings", set()
        )
        warning = (entry.entry_id, screen_id, reason)
        if warning not in warnings:
            warnings.add(warning)
            _LOGGER.warning(
                "Deferring screen %s identity: %s. See the integration's "
                "legacy identity migration documentation",
                screen_id,
                reason,
            )
        return False

    if len(stable_devices) > 1 or len(candidates) > 1:
        return defer("multiple matching devices")
    allowed_devices = {d.id for d in stable_devices + candidates}
    for domain, keys in ENTITY_KEYS.items():
        for key in keys:
            existing = entities.async_get_entity_id(
                domain, DOMAIN, entity_unique_id(entry.entry_id, screen_id, key)
            )
            if existing is not None:
                registered = entities.async_get(existing)
                if registered.config_entry_id != entry.entry_id or (
                    registered.device_id is not None
                    and registered.device_id not in allowed_devices
                ):
                    return defer("target entity belongs to another device or server")
    if stable_devices and not candidates:
        # An inconsistent/partly migrated registry must not spawn a second set.
        if any(
            e.device_id == stable_devices[0].id
            or (
                e.device_id is None
                and any(
                    e.unique_id == f"{legacy_prefix(name)}_{key}"
                    for key in ENTITY_KEYS.get(e.domain, ())
                )
            )
            for e in legacy_entities
        ):
            return defer("stable device still has unresolved legacy entities")
        devices.async_update_device(stable_devices[0].id, name=name)
        return True

    # All reported clients count towards ambiguity, including admin connections.
    matching_ids = {
        device_id(c)
        for c in clients
        if isinstance(c.get("friendlyName"), str)
        and legacy_prefix(c["friendlyName"]) == legacy_prefix(name)
    }
    old_ids = {
        (domain, f"{legacy_prefix(name)}_{key}"): key
        for domain, keys in ENTITY_KEYS.items()
        for key in keys
    }
    orphan_matches = [
        e
        for e in legacy_entities
        if (e.domain, e.unique_id) in old_ids and e.device_id is None
    ]
    if not candidates and not orphan_matches:
        if legacy_devices or legacy_entities:
            return defer(
                "unresolved legacy records; historical rename cannot be inferred"
            )
        return True
    if matching_ids != {screen_id}:
        return defer("name identifies multiple reported clients")
    if stable_devices:
        return defer("both a legacy and a stable device already exist")
    candidate = candidates[0] if candidates else None
    if candidate and {i for i in candidate.identifiers if i[0] == DOMAIN} != {
        (DOMAIN, name)
    }:
        return defer("multiple legacy identifiers cannot be mapped safely")
    if candidate and not _owned_only_by(candidate, entry.entry_id):
        return defer("legacy device shared with another config entry")
    conflicting_devices = [
        d
        for d in legacy_devices
        if d is not candidate
        and any(
            domain == DOMAIN and legacy_prefix(value) == legacy_prefix(name)
            for domain, value in d.identifiers
        )
    ]
    if conflicting_devices:
        return defer("legacy names normalize to the same entity ID")

    for domain, old_id in old_ids:
        existing = entities.async_get_entity_id(domain, DOMAIN, old_id)
        if existing is not None:
            registered = entities.async_get(existing)
            if (
                registered.config_entry_id != entry.entry_id
                or registered.device_id
                not in (None, candidate.id if candidate else None)
            ):
                return defer("legacy unique ID belongs to another device or server")

    associated = [
        e
        for e in own_entities
        if e.platform == DOMAIN and candidate and e.device_id == candidate.id
    ]
    associated += orphan_matches
    updates = []
    for entity in associated:
        key = old_ids.get((entity.domain, entity.unique_id))
        if key is None:
            # Accept a partially completed migration on retry.
            key = next(
                (
                    k
                    for k in ENTITY_KEYS.get(entity.domain, ())
                    if entity.unique_id
                    == entity_unique_id(entry.entry_id, screen_id, k)
                ),
                None,
            )
        if key is None:
            return defer("unrecognized legacy entity identity")
        target = entity_unique_id(entry.entry_id, screen_id, key)
        collision = entities.async_get_entity_id(entity.domain, DOMAIN, target)
        if collision is not None and collision != entity.entity_id:
            return defer("target entity unique ID already exists")
        # A legacy ID attached to a different device must not be reassigned.
        old_collision = entities.async_get_entity_id(
            entity.domain, DOMAIN, f"{legacy_prefix(name)}_{key}"
        )
        if old_collision is not None and old_collision != entity.entity_id:
            return defer("legacy entity belongs to another device")
        updates.append((entity.entity_id, target))

    # Only the identity changes: entity_id/name/disabled_by/options are retained.
    for entity_id, target in updates:
        entities.async_update_entity(entity_id, new_unique_id=target)
    if candidate:
        identifiers = set(candidate.identifiers) - {(DOMAIN, name)}
        identifiers.add(stable)
        devices.async_update_device(
            candidate.id, new_identifiers=identifiers, name=name
        )
    _LOGGER.info("Migrated legacy screen %s to stable identity %s", name, screen_id)
    return True


@callback
def async_track_device_removals(hass, entry, tracked: set[str]) -> None:
    """Let a deliberately removed screen be rediscovered on a later connection."""

    @callback
    def device_removed(event) -> None:
        if event.data["action"] != "remove":
            return
        identifiers = {tuple(value) for value in event.data["device"]["identifiers"]}
        for screen_id in tuple(tracked):
            if (DOMAIN, device_identifier(entry.entry_id, screen_id)) in identifiers:
                tracked.discard(screen_id)

    entry.async_on_unload(
        hass.bus.async_listen(dr.EVENT_DEVICE_REGISTRY_UPDATED, device_removed)
    )
