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

## Screen identity and device removal

Administrative browser connections are excluded from screen discovery. Displays
use the server's persistent `deviceId`, scoped to the integration's config entry,
for their device and entity identities. Renaming a display or opening a new
session keeps the same device and entities. Controls follow the session reported
by the server. For older metadata without `deviceId`, the integration follows the
server's documented `extractDeviceId` contract: the prefix of
`deviceId:sessionSuffix`, or the whole client ID when it contains no colon. The
server must retain that device ID across sessions; clearing browser storage or
changing browser origin creates a different device.

Remove a retired display or old admin device from Home Assistant's device page.
Removal is allowed after a current server snapshot confirms that the display is
absent or disconnected. A live display cannot be removed. If the server is
unavailable, wait for the integration to reconnect before removing a device.
Removing a stale device is an explicit Home Assistant action; the integration
never purges registry records automatically. A removed display can be discovered
again when it reconnects.

### Legacy identity migration

Existing config entries upgrade from version 1 to version 2. The host setting and
options stay intact. Because older integration code uses different entity unique
IDs, rolling back requires restoring the pre-upgrade Home Assistant backup;
Home Assistant rejects the newer major config-entry version in the older code.

Registry migration waits for live metadata. When a display has one unambiguous
legacy name match, the integration updates its device identifiers and entity
unique IDs **in place**. It keeps the device's registry ID and the entities'
existing entity IDs, custom names, areas, icons, disabled/hidden settings and
options. A user-assigned device name also stays intact; the integration's device
name follows the server's friendly name. Customized entity IDs do not need to
match the old screen name. Named legacy entities without a device can also retain
their entity IDs if their original unique IDs match unambiguously.

Name-only records cannot prove which device a screen used to be. Migration and
discovery therefore defer on duplicate or normalized-name collisions, shared
legacy devices, unfamiliar unique IDs, conflicting target IDs, and historical
renames without a matching name. The integration leaves those records untouched
and logs a warning with the reason. While unresolved legacy records remain,
unknown displays also wait; already migrated displays keep working. An offline
legacy display can migrate when it returns under its original name.

For a screen renamed before this upgrade, verify the physical device first. You
can temporarily restore its old server friendly name, with no other client using
that name, let the integration migrate it, then rename it again. If you cannot
establish the mapping, leave the legacy records in place. Deliberately removing
stale records through Home Assistant is another option, but that deletes their
customizations; it is not a migration or a merge. Existing duplicate devices are
never automatically merged. Stop duplicate-name sessions and resolve conflicting
records explicitly before trying again.

## Development checks

Run `python3 -m unittest discover -v` for lifecycle and registry regressions, and
`python3 -m compileall -q custom_components tests` for syntax validation. The tests
need the integration's runtime dependency `aiohttp`; other HA imports are stubbed.
Registry calls use synchronous, signature-constrained mocks of the HA 2026.10.1
API. These tests do not run a complete Home Assistant instance. The repository's
existing GitHub workflow performs HACS validation.
