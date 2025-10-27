# WhoTouchedMe

Home Assistant custom component for ekey fingerprint systems via HTTP webhooks.

## Features

- Receives fingerprint events from ekey systems
- User/Device name mapping from ekey exports
- Per-user sensors (last access time, result, finger)
- Event bus integration: `ekey.fingerprint_detected`
- Optional token authentication for security

## Installation

### HACS (Recommended)

1. Add custom repository: `https://github.com/fixthisshit-wtf/who_touched_me`
2. Search for "WhoTouchedMe" in HACS
3. Click "Install"
4. Restart Home Assistant

### Manual

Copy `custom_components/who_touched_me/` to your Home Assistant config folder.

## Configuration

### 1. Home Assistant Setup

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for "WhoTouchedMe"
3. Configure:
   - **HTTP Port** (default: 9123)
   - **Secret Token** (optional but recommended for security)
4. Export mapping from ekey app → Paste JSON in integration options
5. Click **Save**

### 2. ekey bionyx App Configuration

**Important:** You must also configure the webhook in your ekey bionyx app!

1. Open **ekey bionyx app**
2. Go to **Settings → Notification Webhook**
3. Configure:
   - **URL**: `http://YOUR_HA_IP:9123`
     - Replace `YOUR_HA_IP` with your Home Assistant IP address
   - **Timeout**: 6.0s (recommended)
   - **Sicherheitsstufe**: AllowHttp
   - **Access-Token**: Enter the **same token** you configured in Home Assistant
     - Example: `X7Q9D2L5RT`
     - ⚠️ **This must match exactly** with the token in Home Assistant!
4. Click **Speichern** (Save)

### 3. Export User/Device Mapping

1. In ekey app: **Export system mapping** (JSON format)
2. Copy the JSON content
3. In Home Assistant: Go to **Integration Options** → Paste JSON into "Mapping JSON" field
4. Click **Submit**

Example mapping structure:
```json
{
  "system": "MyHome",
  "users": [
    {
      "userId": "xxxxxx",
      "userName": "Mandi"
    },
    {
      "userId": "xxxxxx",
      "userName": "Lisa"
    }
  ],
  "devices": [
    {
      "deviceId": "4510380543250009",
      "deviceName": "xLine Fingerprint Haustür"
    }
  ]
}
```

## Entities Created

Per user from mapping:
- `sensor.{user}_last_access` - Timestamp of last access
- `sensor.{user}_last_result` - Result (match, no_match, etc.)
- `select.{user}_last_finger` - Which finger was used

## Testing

Test the webhook with curl:
```bash
curl -X POST http://YOUR_HA_IP:9123/api/notification/finger \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "time": "2025-10-27T21:30:00.000Z",
    "type": 10,
    "result": 10,
    "ctlDevId": "0000000000000000",
    "acqDevId": "0000000000000000",
    "params": {
      "userId": "LOAbWecG",
      "fingerIndex": 1
    }
  }'
```

Expected responses:
- **With correct token**: `OK` (Status 200)
- **Without token**: `Unauthorized` (Status 401)
- **With wrong token**: `Forbidden` (Status 403)

## Example Automation

```yaml
automation:
  - alias: "Door opened by Mandi"
    trigger:
      platform: event
      event_type: ekey.fingerprint_detected
      event_data:
        user_name: "Mandi"
        result_name: "match"
    action:
      service: light.turn_on
      target:
        entity_id: light.entrance
```

## Troubleshooting

### No events received
1. Check Home Assistant logs for errors
2. Verify ekey app webhook URL is correct
3. Test with curl command (see Testing section)
4. Ensure port 9123 is not blocked by firewall

### Authentication errors (401/403)
1. Verify token matches in both Home Assistant and ekey app
2. Check token format: `Authorization: Bearer YOUR_TOKEN`
3. Ensure token field is not empty if authentication is enabled

### Sensors not updating
1. Check if mapping JSON is configured correctly
2. Verify userId in ekey event matches userId in mapping
3. Check Home Assistant logs for parsing errors

## Security Note

**Always use a secret token** to prevent unauthorized access to your Home Assistant instance. Without a token, anyone who can reach your Home Assistant IP could send fake fingerprint events.

#