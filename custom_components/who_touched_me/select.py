"""Select entity platform for WhoTouchedMe.

This platform defines select entities that reflect the last detected fingerprint
for each configured user. The entity will always update (and thus can trigger
automations) on every new event, even if the finger stays the same.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, FINGER_OPTIONS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Set up WhoTouchedMe select entities from a config entry."""

    # We'll keep one select entity per known user.
    # The http_receiver will call update_sensor on these.
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    users = hass.data[DOMAIN][entry.entry_id]["users"]

    entities: list[WhoTouchedMeFingerSelect] = []

    for user_id, user_name in users.items():
        entities.append(
            WhoTouchedMeFingerSelect(
                entry_id=entry.entry_id,
                user_id=user_id,
                user_name=user_name,
            )
        )

    async_add_entities(entities)

    # Register entities back to hass.data so http_receiver can find & update them
    hass.data[DOMAIN][entry.entry_id]["finger_select_entities"] = {
        e._user_id: e for e in entities  # noqa: SLF001 (accessing protected for internal registry)
    }

    _LOGGER.debug("WhoTouchedMe select entities set up: %s", users)


class WhoTouchedMeFingerSelect(CoordinatorEntity, SelectEntity):
    """Select entity that shows the last finger used by a given user."""

    _attr_icon = "mdi:fingerprint"
    _attr_should_poll = False
    _attr_options = FINGER_OPTIONS

    def __init__(self, entry_id: str, user_id: str, user_name: str) -> None:
        """Init the select entity for this user."""
        # We are NOT using a DataUpdateCoordinator for periodic polling,
        # but CoordinatorEntity needs something. We don't strictly need
        # coordinator features here, but we'll keep the inheritance to match style.
        super().__init__(coordinator=None)

        self._entry_id = entry_id
        self._user_id = user_id
        self._user_name = user_name

        # This is the visible state (current_option)
        self._attr_current_option = "none"

        # We'll store latest event payload as attributes
        self._event_data: dict[str, Any] = {}

        # NEW: we keep a counter that increments on every event     # <-- NEU
        self._event_counter: int = 0                                # <-- NEU

        # Entity metadata
        self._attr_name = f"{self._user_name} Last Finger"
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_{user_id}_last_finger"

        # Show this under the integration device in HA
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="Who Touched Me",
            manufacturer="fixthisshit.wtf",
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose additional info from the last scan as attributes.

        This now also includes event_counter, which changes every time,
        to force HA to see this entity as 'updated' even if the finger name
        stayed the same.
        """
        # We just return whatever we stored in update_sensor()
        return self._event_data

    @callback
    def update_sensor(self, event_data: dict) -> None:
        """Update the select state and attributes.

        Called by http_receiver when an event is received.
        This WILL run on *every* scan, even if it's the same finger again.
        """

        # 1. Counter hochzählen bei jedem Event                      # <-- NEU
        self._event_counter += 1                                    # <-- NEU

        # 2. Fingername holen (state)
        finger_name = event_data.get("finger_name", "none")

        if finger_name in self._attr_options:
            self._attr_current_option = finger_name
        else:
            self._attr_current_option = "none"
            _LOGGER.warning(
                "Unknown finger name '%s' for user %s, setting to 'none'",
                finger_name,
                self._user_name,
            )

        # 3. Attribute zusammenbauen. Wir hängen den Counter dazu.   # <-- NEU
        data_with_counter = dict(event_data)
        data_with_counter["event_counter"] = self._event_counter
        self._event_data = data_with_counter

        # 4. State in HA schreiben (immer, ohne Vergleich!) ✅
        self.async_write_ha_state()

        _LOGGER.debug(
            "Updated Last Finger for %s (user_id=%s): %s (count=%s)",
            self._user_name,
            self._user_id,
            self._attr_current_option,
            self._event_counter,
        )

    async def async_select_option(self, option: str) -> None:
        """We don't actually allow manual selection to change backend state.

        But HA's select entity requires this method to exist.
        We'll just update the visible option, mostly for UI testing.
        """
        if option in self._attr_options:
            self._attr_current_option = option
            self.async_write_ha_state()
        else:
            _LOGGER.warning(
                "Tried to set invalid finger option '%s' for %s", option, self._user_name
            )
