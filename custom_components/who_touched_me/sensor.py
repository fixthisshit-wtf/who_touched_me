"""Sensor platform for WhoTouchedMe integration."""
import logging
from datetime import datetime
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up WhoTouchedMe sensors from a config entry."""
    # Get entry data
    entry_data = hass.data[DOMAIN][entry.entry_id]
    mapping = entry_data.get("mapping")
    
    # If no mapping, don't create any entities
    if not mapping or "users" not in mapping:
        _LOGGER.info("No mapping configured - no sensors will be created")
        return True
    
    # Initialize sensors dict if not exists
    if "sensors" not in entry_data:
        entry_data["sensors"] = {}
    
    # Create sensors for each user
    entities = []
    for user in mapping["users"]:
        user_id = user.get("userId")
        user_name = user.get("userName", f"user_{user_id}")
        
        if user_id is None:
            continue
        
        # Create 2 sensors per user
        user_sensors = [
            WhoTouchedMeSensor(
                entry_id=entry.entry_id,
                user_id=user_id,
                user_name=user_name,
                sensor_type="last_access_time"
            ),
            WhoTouchedMeSensor(
                entry_id=entry.entry_id,
                user_id=user_id,
                user_name=user_name,
                sensor_type="last_result"
            ),
        ]
        
        # Store sensors by user_id for http_receiver access
        if str(user_id) in entry_data["sensors"]:
            entry_data["sensors"][str(user_id)].extend(user_sensors)
        else:
            entry_data["sensors"][str(user_id)] = user_sensors
        
        entities.extend(user_sensors)
    
    async_add_entities(entities)
    _LOGGER.info(
        "Created %d sensors for %d users",
        len(entities),
        len(mapping["users"])
    )
    
    return True


class WhoTouchedMeSensor(SensorEntity):
    """Representation of a WhoTouchedMe sensor."""
    
    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_force_update = True

    def __init__(
        self,
        entry_id: str,
        user_id: str,
        user_name: str,
        sensor_type: str
    ):
        """Initialize the sensor."""
        self._entry_id = entry_id
        self._user_id = user_id
        self._user_name = user_name
        self._sensor_type = sensor_type
        self._attr_native_value = None
        self._event_data = {}
        self._update_counter = 0
        
        # Generate unique_id: domain_entryid_userid_sensortype
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_{user_id}_{sensor_type}"
        
        # Set attributes based on sensor type
        if sensor_type == "last_access_time":
            self._attr_name = "Last Access"
            self._attr_icon = "mdi:clock-outline"
            self._attr_device_class = SensorDeviceClass.TIMESTAMP
        elif sensor_type == "last_result":
            self._attr_name = "Last Result"
            self._attr_icon = "mdi:check-circle-outline"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this entity."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._entry_id}_{self._user_id}")},
            name=self._user_name,
            manufacturer="ekey",
            model="Fingerprint User",
        )

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            **self._event_data,
            "update_count": self._update_counter
        }

    @callback
    def update_sensor(self, event_data: dict):
        """Update the sensor state and attributes.

        Called by http_receiver when an event is received.
        """
        self._update_counter += 1

        # Store complete event data as attributes
        self._event_data = event_data
        
        # Update state based on sensor type
        if self._sensor_type == "last_access_time":
            # Use datetime object for timestamp sensor
            timestamp = event_data.get("timestamp")
            if isinstance(timestamp, datetime):
                self._attr_native_value = timestamp
            else:
                # Fallback to string if timestamp parsing failed
                self._attr_native_value = event_data.get("time", "unknown")
        
        elif self._sensor_type == "last_result":
            self._attr_native_value = event_data.get("result_name", "unknown")
        
        # Schedule an update to Home Assistant
        self.async_write_ha_state()
        
        _LOGGER.debug(
            "Updated sensor %s: %s (update_count: %d)",
            self.entity_id,
            self._attr_native_value,
            self._update_counter
        )