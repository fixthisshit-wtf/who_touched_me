"""HTTP receiver for ekey events."""
from aiohttp import web
import logging
from datetime import datetime
from typing import Any

from .const import (
    DOMAIN,
    DEFAULT_PORT,
    CONF_PORT,
    CONF_SECRET_TOKEN,
    FINGER_MAPPING,
    RESULT_CODES,
    TYPE_CODES,
    DETAIL_CODES,
)

_LOGGER = logging.getLogger(__name__)


def get_user_name(mapping: dict | None, user_id: str) -> str:
    """Get user name from mapping or return user_id if not found."""
    if not mapping or "users" not in mapping:
        return user_id
    
    for user in mapping["users"]:
        if user.get("userId") == user_id:
            return user.get("userName", user_id)
    
    return user_id


def get_finger_name(finger_index: int | None) -> str:
    """Get finger name from index."""
    if finger_index is None:
        return "unknown"
    return FINGER_MAPPING.get(finger_index, f"finger_{finger_index}")


def get_device_name(mapping: dict | None, device_id: str) -> str:
    """Get device name from mapping or return device_id if not found."""
    if not mapping or "devices" not in mapping:
        return device_id
    
    for device in mapping["devices"]:
        if device.get("deviceId") == device_id:
            return device.get("deviceName", device_id)
    
    return device_id


def parse_ekey_timestamp(time_str: str) -> datetime | None:
    """Parse ekey timestamp to datetime object (UTC).
    
    ekey format: "2025-01-27T14:30:45.123Z" or "2025-01-27T14:30:45Z"
    """
    if not time_str:
        return None
    
    try:
        # Replace 'Z' with '+00:00' for ISO format
        time_str_fixed = time_str.replace("Z", "+00:00")
        return datetime.fromisoformat(time_str_fixed)
    except (ValueError, AttributeError) as err:
        _LOGGER.warning("Could not parse timestamp '%s': %s", time_str, err)
        return None


def validate_event_data(data: dict) -> bool:
    """Validate incoming event structure."""
    required_fields = ["time", "type", "result"]
    return all(field in data for field in required_fields)


async def handle_post(request: web.Request) -> web.Response:
    """Handle incoming POST request from ekey system."""
    hass = request.app["hass"]
    
    # Check secret token if configured (find from any entry)
    secret_token = None
    for entry_data in hass.data.get(DOMAIN, {}).values():
        if isinstance(entry_data, dict) and CONF_SECRET_TOKEN in entry_data:
            token = entry_data.get(CONF_SECRET_TOKEN)
            if token:  # Only if token is not empty
                secret_token = token
                break
    
    # Validate token if configured
    if secret_token:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            _LOGGER.warning(
                "Rejected request: Missing or invalid Authorization header"
            )
            return web.Response(status=401, text="Unauthorized")
        
        token = auth_header[7:]  # Remove "Bearer " prefix
        if token != secret_token:
            _LOGGER.warning("Rejected request: Invalid secret token")
            return web.Response(status=403, text="Forbidden")
    
    # Parse JSON body
    try:
        data = await request.json()
    except Exception as err:
        _LOGGER.error("Invalid JSON received: %s", err)
        return web.Response(status=400, text="Invalid JSON")
    
    # Validate event structure
    if not validate_event_data(data):
        _LOGGER.warning("Missing required fields in event: %s", list(data.keys()))
        return web.Response(status=400, text="Missing required fields")
    
    # Extract main event data (root level)
    time_str = data.get("time")
    timestamp = parse_ekey_timestamp(time_str)
    event_type = data.get("type")
    result = data.get("result")
    detail = data.get("detail")
    ctl_dev_id = data.get("ctlDevId")
    acq_dev_id = data.get("acqDevId")
    
    # Extract params (nested object)
    params = data.get("params", {})
    user_id = params.get("userId")
    finger_index = params.get("fingerIndex")
    input_number = params.get("inputNumber")
    trigger = params.get("trigger")
    
    # Find mapping from any entry
    mapping = None
    for entry_data in hass.data.get(DOMAIN, {}).values():
        if isinstance(entry_data, dict) and "mapping" in entry_data:
            mapping = entry_data.get("mapping")
            if mapping:
                break
    
    # Map IDs to human-readable names
    user_name = get_user_name(mapping, user_id)
    finger_name = get_finger_name(finger_index)
    ctl_device_name = get_device_name(mapping, ctl_dev_id)
    acq_device_name = get_device_name(mapping, acq_dev_id)
    result_name = RESULT_CODES.get(result, f"unknown_{result}")
    type_name = TYPE_CODES.get(event_type, f"unknown_{event_type}")
    detail_name = DETAIL_CODES.get(detail, f"unknown_{detail}") if detail else None
    
    # Log event
    _LOGGER.info(
        "eKey event: %s | %s | User: %s (%s) | Finger: %s | Device: %s | Time: %s",
        type_name,
        result_name,
        user_name,
        user_id,
        finger_name,
        acq_device_name,
        time_str,
    )
    
    # Build complete event data
    event_data = {
        # Time information
        "time": time_str,
        "timestamp": timestamp,  # datetime object for sensors
        
        # Type information
        "type": event_type,
        "type_name": type_name,
        
        # Result information
        "result": result,
        "result_name": result_name,
        
        # Detail information
        "detail": detail,
        "detail_name": detail_name,
        
        # User information
        "user_id": user_id,
        "user_name": user_name,
        
        # Finger information
        "finger_index": finger_index,
        "finger_name": finger_name,
        
        # Device information
        "ctl_device_id": ctl_dev_id,
        "ctl_device_name": ctl_device_name,
        "acq_device_id": acq_dev_id,
        "acq_device_name": acq_device_name,
        
        # Digital input information (if applicable)
        "input_number": input_number,
        "trigger": trigger,
    }
    
    # Fire Home Assistant event
    hass.bus.async_fire("ekey.fingerprint_detected", event_data)
    
    # Update sensors for this user (across all entries)
    if user_id:
        for entry_data in hass.data.get(DOMAIN, {}).values():
            if isinstance(entry_data, dict) and "sensors" in entry_data:
                await update_user_sensors(
                    entry_data["sensors"], user_id, user_name, event_data
                )
    
    return web.Response(text="OK")


async def update_user_sensors(
    sensors_dict: dict, user_id: str, user_name: str, event_data: dict
) -> None:
    """Update sensors for a specific user."""
    sensors = sensors_dict.get(str(user_id))
    
    if not sensors:
        _LOGGER.debug("No sensors found for user_id %s", user_id)
        return
    
    # Update all sensors/selects for this user
    for sensor in sensors:
        sensor.update_sensor(event_data)
    
    _LOGGER.debug("Updated %d entities for user %s", len(sensors), user_name)


async def start_server(hass, port: int = DEFAULT_PORT) -> None:
    """Start HTTP server (once globally)."""
    # Check if server is already running
    if "runner" in hass.data.get(DOMAIN, {}):
        _LOGGER.debug("HTTP server already running on port %d", port)
        return
    
    # Create aiohttp application
    app = web.Application()
    app["hass"] = hass
    app.router.add_post("/api/notification/finger", handle_post)
    
    # Create runner
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Start server
    try:
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
    except OSError as err:
        await runner.cleanup()
        raise OSError(f"Failed to start server on port {port}: {err}") from err
    
    # Store runner globally for cleanup
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["runner"] = runner
    
    _LOGGER.info("eKey HTTP server started on port %d", port)


async def stop_server(hass) -> None:
    """Stop HTTP server."""
    runner = hass.data.get(DOMAIN, {}).pop("runner", None)
    if runner:
        await runner.cleanup()
        _LOGGER.info("eKey HTTP server stopped")