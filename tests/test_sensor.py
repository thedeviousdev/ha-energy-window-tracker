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
    """[Happy] async_setup_entry creates one sensor per window when store is empty."""
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
    ranges = state.attributes.get("ranges") or []
    assert len(ranges) == 1
    assert ranges[0].get("start") == "09:00"
    assert ranges[0].get("end") == "17:00"


@pytest.mark.asyncio
async def test_sensor_attributes(
    hass: HomeAssistant, mock_config_entry: ConfigEntry
) -> None:
    """[Happy] Sensor exposes source_entity, status, ranges (start, end) when source is available."""
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
    assert "ranges" in state.attributes
    assert isinstance(state.attributes["ranges"], list)
    assert len(state.attributes["ranges"]) >= 1
    assert "start" in state.attributes["ranges"][0]
    assert "end" in state.attributes["ranges"][0]


@pytest.mark.asyncio
async def test_sensor_setup_when_store_returns_none_creates_entity(
    hass: HomeAssistant, mock_config_entry: ConfigEntry
) -> None:
    """[Unhappy] When Store.async_load returns None, setup does not crash and one entity is created."""
    hass.states.async_set("sensor.today_load", "0")
    with patch(
        "custom_components.energy_window_tracker.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value=None,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    our = _get_tracker_sensors(hass, mock_config_entry.entry_id)
    assert len(our) == 1
    state = hass.states.get(our[0].entity_id)
    assert state is not None
    assert state.attributes.get("source_entity") == "sensor.today_load"


@pytest.mark.asyncio
async def test_sensor_when_source_unavailable_entity_has_attributes(
    hass: HomeAssistant, mock_config_entry: ConfigEntry
) -> None:
    """[Unhappy] When source is unavailable, entity still exists and exposes source_entity and ranges."""
    hass.states.async_set("sensor.today_load", "unavailable")
    with patch(
        "custom_components.energy_window_tracker.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    our = _get_tracker_sensors(hass, mock_config_entry.entry_id)
    assert len(our) == 1
    state = hass.states.get(our[0].entity_id)
    assert state is not None
    assert state.state in ("unavailable", "unknown")
    assert state.attributes.get("source_entity") == "sensor.today_load"
    assert "ranges" in state.attributes
    assert isinstance(state.attributes["ranges"], list)
    assert len(state.attributes["ranges"]) >= 1
