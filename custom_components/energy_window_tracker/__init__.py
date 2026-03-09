"""Energy Window Tracker integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, TRACE

# Use explicit name so configuration.yaml logger config and log viewer filter match
_LOGGER = logging.getLogger("custom_components.energy_window_tracker")

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Energy Window Tracker from a config entry."""
    # Log once via root logger so it shows even when log viewer is filtered to "core"
    logging.warning(
        "[energy_window_tracker] Integration loaded entry_id=%s — to see debug/trace logs add to configuration.yaml: logger: logs: custom_components.energy_window_tracker: debug then in Logs search for 'energy_window_tracker'",
        entry.entry_id,
    )
    _LOGGER.warning(
        "Energy Window Tracker loaded entry_id=%s (add logger in configuration.yaml for debug)",
        entry.entry_id,
    )
    _LOGGER.log(TRACE, "async_setup_entry: entry_id=%s", entry.entry_id)
    _LOGGER.debug("async_setup_entry: entry_id=%s", entry.entry_id)
    hass.data.setdefault(DOMAIN, {})
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    _LOGGER.debug("async_unload_entry: entry_id=%s ok=%s", entry.entry_id, unload_ok)
    return unload_ok


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    _LOGGER.debug("async_update_options: entry_id=%s, reloading", entry.entry_id)
    await hass.config_entries.async_reload(entry.entry_id)
