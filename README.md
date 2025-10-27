# WhoTouchedMe

Home Assistant custom component for ekey fingerprint systems via HTTP webhooks.

## Features

- Receives fingerprint events from ekey systems
- User/Device name mapping from ekey exports
- Per-user sensors (last access time, result, finger)
- Event bus integration: `ekey.fingerprint_detected`
- Optional token authentication

## Installation

### HACS (Recommended)

1. Add custom repository: `https://github.com/fixthisshit-wtf/who_touched_me`
2. Search for "WhoTouchedMe" in HACS
3. Click "Install"
4. Restart Home Assistant

### Manual

Copy `custom_components/who_touched_me/` to your Home Assistant config folder.

## Configuration

1. Go to Settings → Devices & Services → Add Integration
2. Search for "WhoTouchedMe"
3. Configure HTTP port (default: 9123) and optional token
4. Export mapping from ekey app → Paste JSON in integration options
5. Configure ekey to POST to: `http://YOUR_HA_IP:9123/api/notification/finger`

## Entities Created

Per user from mapping:
- `sensor.{user}_last_access` - Timestamp of last access
- `sensor.{user}_last_result` - Result (match, no_match, etc.)
- `select.{user}_last_finger` - Which finger was used

## Example Automation
```yaml
automation:
  - alias: "Door opened by Michael"
    trigger:
      platform: event
      event_type: ekey.fingerprint_detected
      event_data:
        user_name: "Michael"
        result_name: "match"
    action:
      service: light.turn_on
      target:
        entity_id: light.entrance
```


