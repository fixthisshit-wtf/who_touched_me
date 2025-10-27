"""WhoTouchedMe integration."""
import json
import logging
from pathlib import Path
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN, PLATFORMS, DEFAULT_PORT, CONF_PORT, CONF_SECRET_TOKEN, CONF_MAPPING
from .http_receiver import start_server, stop_server

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up from YAML (deprecated)."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from config entry."""
    # Get configuration from options (or use defaults)
    port = entry.options.get(CONF_PORT, DEFAULT_PORT)
    secret_token = entry.options.get(CONF_SECRET_TOKEN, "")
    mapping = entry.options.get(CONF_MAPPING)
    
    # Try loading legacy mapping file if no mapping in options
    if not mapping:
        mapping = await _load_legacy_mapping(hass)
    
    # Initialize domain data structure if not exists
    hass.data.setdefault(DOMAIN, {})
    
    # Store entry-specific data
    hass.data[DOMAIN][entry.entry_id] = {
        "mapping": mapping,
        "entry": entry,
        "sensors": {},  # Will store sensors by user_id
        CONF_PORT: port,
        CONF_SECRET_TOKEN: secret_token,
    }
    
    if mapping:
        _LOGGER.info(
            "Loaded mapping for system: %s",
            mapping.get("system", "Unknown")
        )
    else:
        _LOGGER.info("No mapping configured - using raw IDs")
    
    # Start HTTP server (only once globally, not per entry)
    if "runner" not in hass.data[DOMAIN]:
        try:
            await start_server(hass, port)
        except OSError as err:
            raise ConfigEntryNotReady(
                f"Failed to start HTTP server on port {port}: {err}"
            ) from err
    
    # Set up platforms (sensor and select)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Listen for options updates
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def _load_legacy_mapping(hass: HomeAssistant) -> dict | None:
    """Load legacy mapping file (for backwards compatibility)."""
    mapping_file = Path(
        hass.config.path("custom_components", DOMAIN, "mapping.json")
    )
    
    if not mapping_file.exists():
        return None
    
    try:
        content = await hass.async_add_executor_job(mapping_file.read_text)
        mapping = json.loads(content)
        _LOGGER.warning(
            "Using legacy mapping.json file. "
            "Please migrate to integration options via UI!"
        )
        return mapping
    except (OSError, json.JSONDecodeError) as err:
        _LOGGER.error("Failed to load legacy mapping file: %s", err)
        return None


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        # Remove entry data
        hass.data[DOMAIN].pop(entry.entry_id, None)
        
        # Stop HTTP server only if this was the last entry
        remaining_entries = [
            e for e in hass.config_entries.async_entries(DOMAIN)
            if e.entry_id != entry.entry_id
        ]
        
        if len(remaining_entries) == 0:
            await stop_server(hass)
            _LOGGER.info("Last entry removed - HTTP server stopped")
    
    return unload_ok