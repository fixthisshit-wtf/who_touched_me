"""Select platform for WhoTouchedMe integration."""
import logging
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, FINGER_OPTIONS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> bool:
    """Set up WhoTouchedMe select entities from a config entry."""
    # Get entry data
    entry_data = hass.data[DOMAIN][entry.entry_id]
    mapping = entry_data.get("mapping")
    
    # If no mapping, don't create any entities
    if not mapping or "users" not in mapping:
        _LOGGER.info("No mapping configured - no select entities will be created")
        return True
    
    # Initialize sensors dict if not exists
    if "sensors" not in entry_data:
        entry_data["sensors"] = {}
    
    # Create select entities for each user
    entities = []
    for user in mapping["users"]:
        user_id = user.get("userId")
        user_name = user.get("userName", f"user_{user_id}")
        
        if user_id is None:
            continue
        
        # Create finger select entity
        finger_select = WhoTouchedMeFingerSelect(
            entry_id=entry.entry_id,
            user_id=user_id,
            user_name=user_name,
        )
        
        # Store in hass.data for http_receiver access
        # Append to existing sensors list (from sensor.py)
        if str(user_id) in entry_data["sensors"]:
            entry_data["sensors"][str(user_id)].append(finger_select)
        else:
            entry_data["sensors"][str(user_id)] = [finger_select]
        
        entities.append(finger_select)
    
    async_add_entities(entities)
    _LOGGER.info(
        "Created %d select entities for %d users",
        len(entities),
        len(mapping["users"])
    )
    
    return True


class WhoTouchedMeFingerSelect(SelectEntity):
    """Representation of a WhoTouchedMe finger select entity."""
    
    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_force_update = True

    def __init__(
        self,
        entry_id: str,
        user_id: str,
        user_name: str,
    ):
        """Initialize the select entity."""
        self._entry_id = entry_id
        self._user_id = user_id
        self._user_name = user_name
        self._attr_current_option = "none"
        self._event_data = {}
        self._update_counter = 0
        
        # Set available options
        self._attr_options = FINGER_OPTIONS
        
        # Generate unique_id: domain_entryid_userid_lastfinger
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_{user_id}_last_finger"
        
        # Set name and icon
        self._attr_name = "Last Finger"
        self._attr_icon = "mdi:fingerprint"

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

    async def async_select_option(self, option: str) -> None:
        """Change the selected option.
        
        This entity is read-only and updated by fingerprint events.
        Users cannot manually change the value.
        """
        raise NotImplementedError(
            "This select entity is read-only and cannot be manually changed"
        )

    @callback
    def update_sensor(self, event_data: dict):
        """Update the select state and attributes.

        Called by http_receiver when an event is received.
        """
        self._update_counter += 1

        # Store complete event data as attributes
        self._event_data = event_data
        
        # Update current option
        finger_name = event_data.get("finger_name", "none")
        if finger_name in self._attr_options:
            self._attr_current_option = finger_name
        else:
            # Fallback if finger_name is not in options
            self._attr_current_option = "none"
            _LOGGER.warning(
                "Unknown finger name '%s' for user %s, setting to 'none'",
                finger_name,
                self._user_name
            )
        
        # WORKAROUND: Force state change by toggling to None first
        # This ensures automations always trigger even with same finger
        old_option = self._attr_current_option
        self._attr_current_option = "none"
        self.async_write_ha_state()
        
        # Now set the actual finger (with small delay to ensure two distinct events)
        self._attr_current_option = old_option
        self.async_write_ha_state()
        
        _LOGGER.debug(
            "Updated select %s: %s (update_count: %d)",
            self.entity_id,
            self._attr_current_option,
            self._update_counter
        )