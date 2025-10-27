"""Config flow for WhoTouchedMe integration."""
import json
import logging
from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, DEFAULT_PORT, CONF_PORT, CONF_SECRET_TOKEN, CONF_MAPPING

_LOGGER = logging.getLogger(__name__)


def validate_mapping(mapping: dict) -> dict[str, Any]:
    """Validate mapping structure and return summary info."""
    errors = {}
    info = {}
    
    if not isinstance(mapping, dict):
        return {"errors": {"mapping_json": "invalid_json_structure"}}
    
    # Check for required fields
    has_users = "users" in mapping and isinstance(mapping["users"], list)
    has_devices = "devices" in mapping and isinstance(mapping["devices"], list)
    
    if not has_users and not has_devices:
        return {"errors": {"mapping_json": "missing_required_fields"}}
    
    # Count valid users
    if has_users:
        info["users"] = sum(
            1 for u in mapping["users"] 
            if "userId" in u and "userName" in u
        )
    
    # Count valid devices
    if has_devices:
        info["devices"] = sum(
            1 for d in mapping["devices"] 
            if "deviceId" in d
        )
    
    info["system"] = mapping.get("system", "Unknown")
    return {"errors": errors, "info": info}


class WhoTouchedMeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for WhoTouchedMe."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial setup step."""
        # Only allow single instance
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        
        if user_input is not None:
            # Create the config entry with options
            return self.async_create_entry(
                title="WhoTouchedMe",
                data={},
                options={
                    CONF_PORT: user_input.get(CONF_PORT, DEFAULT_PORT),
                    CONF_SECRET_TOKEN: user_input.get(CONF_SECRET_TOKEN, ""),
                }
            )
        
        # Show form
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
                vol.Optional(CONF_SECRET_TOKEN, default=""): cv.string,
            }),
            description_placeholders={
                "default_port": str(DEFAULT_PORT),
                "endpoint": "/api/notification/finger",
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return WhoTouchedMeOptionsFlow(config_entry)


class WhoTouchedMeOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for WhoTouchedMe."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors = {}
        description_placeholders = {}

        if user_input is not None:
            # Build options dict
            options = {
                CONF_PORT: user_input.get(CONF_PORT, DEFAULT_PORT),
                CONF_SECRET_TOKEN: user_input.get(CONF_SECRET_TOKEN, ""),
            }
            
            # Handle mapping JSON
            mapping_json = user_input.get("mapping_json", "").strip()
            
            if mapping_json:
                try:
                    mapping_data = json.loads(mapping_json)
                    validation = validate_mapping(mapping_data)
                    
                    if validation.get("errors"):
                        errors = validation["errors"]
                    else:
                        # Mapping is valid
                        options[CONF_MAPPING] = mapping_data
                        info = validation["info"]
                        _LOGGER.info(
                            "Mapping loaded: %s - %d users, %d devices",
                            info.get("system", "Unknown"),
                            info.get("users", 0),
                            info.get("devices", 0),
                        )
                except json.JSONDecodeError as err:
                    errors["mapping_json"] = "invalid_json"
                    _LOGGER.error("JSON decode error: %s", err)
            else:
                # No mapping provided - clear it
                options[CONF_MAPPING] = None
            
            # Save options if no errors
            if not errors:
                return self.async_create_entry(title="", data=options)

        # Get current values for form defaults
        current_port = self.config_entry.options.get(CONF_PORT, DEFAULT_PORT)
        current_token = self.config_entry.options.get(CONF_SECRET_TOKEN, "")
        current_mapping = self.config_entry.options.get(CONF_MAPPING)
        current_json = ""
        
        # Format current mapping as JSON string
        if current_mapping:
            current_json = json.dumps(current_mapping, indent=2, ensure_ascii=False)
            validation = validate_mapping(current_mapping)
            if not validation.get("errors"):
                info = validation["info"]
                description_placeholders["current_info"] = (
                    f"Current: {info.get('system')} - "
                    f"{info.get('users', 0)} users, {info.get('devices', 0)} devices"
                )

        # Show form
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(CONF_PORT, default=current_port): cv.port,
                vol.Optional(CONF_SECRET_TOKEN, default=current_token): cv.string,
                vol.Optional("mapping_json", default=current_json): cv.string,
            }),
            errors=errors,
            description_placeholders=description_placeholders,
        )