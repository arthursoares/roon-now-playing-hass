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
