"""Energy Window Tracker integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant

from .const import DOMAIN

# Use explicit name so configuration.yaml logger config and log viewer filter match
_MAIN_LOGGER = logging.getLogger("custom_components.energy_window_tracker")

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Energy Window Tracker from a config entry."""
    logging.warning("[energy_window_tracker] Integration loaded entry_id=%s", entry.entry_id)
    _MAIN_LOGGER.warning("init: Integration loaded - entry_id=%s", entry.entry_id)
    hass.data.setdefault(DOMAIN, {})
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry (called when entry is deleted or reloaded)."""
    logging.warning("[energy_window_tracker] Entry removed/unloading entry_id=%s", entry.entry_id)
    _MAIN_LOGGER.warning("init: Entry removed/unloading - entry_id=%s", entry.entry_id)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    _MAIN_LOGGER.warning("init: async_unload_entry - entry_id=%s ok=%s", entry.entry_id, unload_ok)
    return unload_ok


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    # Guard against reload races when options are updated while setup/reload is still running.
    # (Seen as OperationNotAllowed: ConfigEntryState.SETUP_IN_PROGRESS.)
    if entry.state != ConfigEntryState.LOADED:
        _MAIN_LOGGER.debug(
            "init: async_update_options - entry_id=%s state=%s; skip reload",
            entry.entry_id,
            entry.state,
        )
        return
    _MAIN_LOGGER.warning("init: async_update_options - entry_id=%s, reloading", entry.entry_id)
    await hass.config_entries.async_reload(entry.entry_id)
