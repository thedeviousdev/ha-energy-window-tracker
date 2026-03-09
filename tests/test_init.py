"""Tests for the Energy Window Tracker integration setup.

Uses the core interface (hass.config_entries.async_setup / async_unload) per
https://developers.home-assistant.io/docs/development_testing/#writing-tests-for-integrations
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.energy_window_tracker.const import CONF_SOURCES, DOMAIN


@pytest.mark.asyncio
async def test_setup_and_unload_entry(
    hass: HomeAssistant, mock_config_entry: ConfigEntry
) -> None:
    """[Happy] Setting up and unloading a config entry via the core config entries interface."""
    hass.states.async_set("sensor.today_load", "0")
    with patch(
        "custom_components.energy_window_tracker.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert DOMAIN in hass.data
    assert mock_config_entry.entry_id in hass.data[DOMAIN]

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    assert hass.data[DOMAIN].get(mock_config_entry.entry_id) is None


@pytest.mark.asyncio
async def test_unload_when_not_loaded_succeeds(hass: HomeAssistant) -> None:
    """[Unhappy] Unloading an entry that was never set up does not crash and returns True."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Never Setup",
        data={CONF_SOURCES: []},
        options={},
        entry_id="never_setup_id",
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.async_unload(entry.entry_id)
    assert result is True
