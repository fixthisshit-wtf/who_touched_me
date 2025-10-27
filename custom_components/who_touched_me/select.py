from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, FINGER_OPTIONS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Set up WhoTouchedMe select entities from a config entry."""

    # hole die user-map, die im __init__.py beim setup gespeichert wurde
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

    # Entities an HA anhängen
    async_add_entities(entities)

    # Referenz speichern, damit http_receiver sie updaten kann
    hass.data[DOMAIN][entry.entry_id]["finger_select_entities"] = {
        e.user_id: e for e in entities
    }

    _LOGGER.debug("WhoTouchedMe select entities set up: %s", users)


class WhoTouchedMeFingerSelect(SelectEntity):
    """Select entity that shows the last finger used by a given user.

    WICHTIG: Wir erzwingen ein State-/Attribute-Update bei jedem Scan,
    damit Automationen mit Zustand-Trigger jedes Mal feuern.
    """

    _attr_icon = "mdi:fingerprint"
    _attr_should_poll = False
    _attr_options = FINGER_OPTIONS

    def __init__(self, entry_id: str, user_id: str, user_name: str) -> None:
        """Init the select entity for this user."""
        self._entry_id = entry_id
        self._user_id = user_id
        self._user_name = user_name

        # sichtbarer Wert (state)
        self._attr_current_option = "none"

        # zusätzliche Attribute (werden in extra_state_attributes exposed)
        self._event_data: dict[str, Any] = {}

        # NEW: Counter für jeden Scan, damit sich Attribute immer ändern
        self._event_counter: int = 0

        # Anzeigename und unique_id so wie vorher
        self._attr_name = f"{self._user_name} Last Finger"
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_{user_id}_last_finger"

        # DeviceInfo, damit es schön unter deinem Integration-"Gerät" hängt
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="Who Touched Me",
            manufacturer="fixthisshit.wtf",
        )

    #
    # Hilfs-Properties, damit http_receiver weiterarbeiten kann
    #
    @property
    def user_id(self) -> str:
        return self._user_id

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose Zusatzinfos vom letzten Scan als Attribute."""
        return self._event_data

    @callback
    def update_sensor(self, event_data: dict) -> None:
        """Wird von http_receiver bei JEDEM Scan aufgerufen.

        Wichtig: Wir erhöhen jedes Mal den Counter, auch wenn derselbe Finger
        nochmal kommt. Dadurch ändert sich das Attribut 'event_counter' jedes Mal
        -> Home Assistant sieht das als Update
        -> Deine Automation mit Zustand-Trigger feuert jedes Mal.
        """

        # 1. Counter +1 bei jedem Finger-Event
        self._event_counter += 1

        # 2. Finger (State)
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

        # 3. Attributes zusammenbauen, inkl. Counter
        data_with_counter = dict(event_data)
        data_with_counter["event_counter"] = self._event_counter
        self._event_data = data_with_counter

        # 4. Home Assistant updaten (immer!)
        self.async_write_ha_state()

        _LOGGER.debug(
            "Updated Last Finger for %s (user_id=%s): %s (count=%s)",
            self._user_name,
            self._user_id,
            self._attr_current_option,
            self._event_counter,
        )

    async def async_select_option(self, option: str) -> None:
        """select.* Entities müssen diese Methode haben.

        Wir erlauben das Setzen im UI (kosmetisch), aber das hat KEINEN Effekt
        auf ekey oder irgendwas anderes.
        """
        if option in self._attr_options:
            self._attr_current_option = option
            self.async_write_ha_state()
        else:
            _LOGGER.warning(
                "Tried to set invalid finger option '%s' for %s",
                option,
                self._user_name,
            )
