"""Tests for the Energy Window Tracker sensor platform.

Assert entity state via hass.states and entity registry per
https://developers.home-assistant.io/docs/development_testing/#writing-tests-for-integrations
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.energy_window_tracker.const import DOMAIN


def _get_tracker_sensors(hass: HomeAssistant, entry_id: str) -> list:
    """Return entity entries for our config entry (sensor domain)."""
    registry = er.async_get(hass)
    return [
        e
        for e in registry.entities.get_entries_for_config_entry_id(entry_id)
        if e.domain == SENSOR_DOMAIN
    ]


@pytest.mark.asyncio
async def test_sensor_setup_creates_entities(
    hass: HomeAssistant, mock_config_entry: ConfigEntry
) -> None:
    """Test that async_setup_entry creates one sensor per window."""
    hass.states.async_set("sensor.today_load", "10.5")
    with patch(
        "custom_components.energy_window_tracker.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    our_entities = _get_tracker_sensors(hass, mock_config_entry.entry_id)
    assert len(our_entities) == 1
    state = hass.states.get(our_entities[0].entity_id)
    assert state is not None
    assert state.attributes.get("start") == "09:00"
    assert state.attributes.get("end") == "17:00"


@pytest.mark.asyncio
async def test_sensor_attributes(
    hass: HomeAssistant, mock_config_entry: ConfigEntry
) -> None:
    """Test sensor exposes source_entity, status, start, end."""
    hass.states.async_set("sensor.today_load", "0")
    with patch(
        "custom_components.energy_window_tracker.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    our = _get_tracker_sensors(hass, mock_config_entry.entry_id)
    assert len(our) >= 1
    state = hass.states.get(our[0].entity_id)
    assert state is not None
    assert "source_entity" in state.attributes
    assert state.attributes["source_entity"] == "sensor.today_load"
    assert "status" in state.attributes
    assert "start" in state.attributes
    assert "end" in state.attributes
