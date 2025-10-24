# WhoTouchedMe

A Home Assistant custom component that receives fingerprint detection notifications from ekey systems via HTTP webhooks.

## Overview

This integration creates an HTTP endpoint that listens for fingerprint detection events from ekey fingerprint readers. When a fingerprint is detected, it fires a Home Assistant event that can be used in automations.

## Features

- HTTP webhook receiver for ekey fingerprint notifications
- Fires `ekey.fingerprint_detected` events in Home Assistant
- Provides user ID and finger index information
- Lightweight and easy to integrate with existing automations

## Installation

### Manual Installation

1. Copy the `custom_components/who_touched_me` directory to your Home Assistant `custom_components` directory
2. Restart Home Assistant

### HACS Installation

1. Add this repository as a custom repository in HACS
2. Search for "WhoTouchedMe" in HACS
3. Install the integration
4. Restart Home Assistant

## Configuration

Add the following to your `configuration.yaml`:

```yaml
who_touched_me:
```

After adding the configuration, restart Home Assistant. The HTTP endpoint will be available at:

```
http://your-home-assistant:9123/api/notification/finger
```

## Usage

### Configure Your ekey System

Configure your ekey system to send POST requests to:

```
http://your-home-assistant-ip:9123/api/notification/finger
```

The expected JSON payload format:

```json
{
  "params": {
    "userId": "123",
    "fingerIndex": "1"
  }
}
```

### Event Data

When a fingerprint is detected, the integration fires an `ekey.fingerprint_detected` event with the following data:

- `user_id`: The user ID from the ekey system
- `finger_index`: The finger index that was scanned

### Example Automation

```yaml
automation:
  - alias: "Fingerprint Detected"
    trigger:
      platform: event
      event_type: ekey.fingerprint_detected
    action:
      - service: notify.mobile_app
        data:
          message: "Fingerprint detected: User {{ trigger.event.data.user_id }}, Finger {{ trigger.event.data.finger_index }}"
      - service: light.turn_on
        target:
          entity_id: light.entrance
```

## Technical Details

- **HTTP Port**: 9123
- **Endpoint**: `/api/notification/finger`
- **Method**: POST
- **Content-Type**: application/json
- **Event Type**: `ekey.fingerprint_detected`

## Troubleshooting

### Connection Issues

- Ensure port 9123 is not blocked by your firewall
- Verify your ekey system can reach your Home Assistant instance
- Check Home Assistant logs for any error messages

### Event Not Firing

- Enable debug logging to see incoming requests
- Verify the JSON payload format matches the expected structure
- Check that the integration is properly loaded in Home Assistant

## Support

For issues, questions, or feature requests, please open an issue on the GitHub repository.

## License

This project is provided as-is for integration with ekey fingerprint systems and Home Assistant.
