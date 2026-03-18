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
from pytest_homeassistant_custom_component.common import MockConfigEntry


def _get_tracker_sensors(hass: HomeAssistant, entry_id: str) -> list:
    """Return entity entries for our config entry (sensor domain)."""
    registry = er.async_get(hass)
    return [
        e
        for e in registry.entities.get_entries_for_config_entry_id(entry_id)
        if e.domain == SENSOR_DOMAIN
    ]


def _unique_ids_by_original_name(hass: HomeAssistant, entry_id: str) -> dict[str, str]:
    """Map original_name -> unique_id for our sensor entities."""
    entities = _get_tracker_sensors(hass, entry_id)
    out: dict[str, str] = {}
    for e in entities:
        if e.original_name:
            out[e.original_name] = e.unique_id
    return out


def _unique_ids_by_entity_id(hass: HomeAssistant, entry_id: str) -> dict[str, str]:
    """Map entity_id -> unique_id for our sensor entities."""
    entities = _get_tracker_sensors(hass, entry_id)
    return {e.entity_id: e.unique_id for e in entities}


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


@pytest.mark.asyncio
async def test_unique_ids_stable_when_windows_reordered(hass: HomeAssistant) -> None:
    """[Happy] Reordering windows must not swap unique_ids between window sensors."""
    entry = MockConfigEntry(
        domain="energy_window_tracker",
        title="Reorder",
        data={
            "sources": [
                {
                    "source_entity": "sensor.today_load",
                    "name": "Energy",
                    "windows": [
                        {"name": "Peak", "start": "09:00", "end": "12:00"},
                        {"name": "Off-Peak", "start": "12:00", "end": "17:00"},
                    ],
                }
            ]
        },
        options={},
        entry_id="reorder_entry_id",
    )
    entry.add_to_hass(hass)
    hass.states.async_set("sensor.today_load", "0")
    with patch(
        "custom_components.energy_window_tracker.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    initial = _unique_ids_by_entity_id(hass, entry.entry_id)
    assert set(initial.keys()) == {"sensor.today_load_peak", "sensor.today_load_off_peak"}
    assert len(set(initial.values())) == 2, "sanity check: two distinct sensors"

    # Reorder windows (simulate editing that changes list order)
    hass.config_entries.async_update_entry(
        entry,
        options={
            "sources": [
                {
                    "source_entity": "sensor.today_load",
                    "name": "Energy",
                    "windows": [
                        {"name": "Off-Peak", "start": "12:00", "end": "17:00"},
                        {"name": "Peak", "start": "09:00", "end": "12:00"},
                    ],
                }
            ]
        },
    )

    assert await hass.config_entries.async_unload(entry.entry_id)
    with patch(
        "custom_components.energy_window_tracker.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    after = _unique_ids_by_entity_id(hass, entry.entry_id)
    assert after == initial, "entity_id -> unique_id mapping must be stable after reorder"


@pytest.mark.asyncio
async def test_unique_ids_do_not_collide_when_names_slugify_same(hass: HomeAssistant) -> None:
    """[Unhappy] Different names that slugify similarly must still get distinct unique_ids."""
    entry = MockConfigEntry(
        domain="energy_window_tracker",
        title="Collisions",
        data={
            "sources": [
                {
                    "source_entity": "sensor.today_load",
                    "name": "Energy",
                    "windows": [
                        {"name": "Peak", "start": "09:00", "end": "10:00"},
                        {"name": "peak", "start": "10:00", "end": "11:00"},
                    ],
                }
            ]
        },
        options={},
        entry_id="collision_entry_id",
    )
    entry.add_to_hass(hass)
    hass.states.async_set("sensor.today_load", "0")
    with patch(
        "custom_components.energy_window_tracker.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    entities = _get_tracker_sensors(hass, entry.entry_id)
    assert len(entities) == 2
    unique_ids = {e.unique_id for e in entities}
    assert len(unique_ids) == 2, "unique_id must be distinct even if slug collides"


@pytest.mark.asyncio
async def test_renaming_one_window_does_not_change_others_unique_ids(hass: HomeAssistant) -> None:
    """[Unhappy] Renaming one window should only change that window's unique_id."""
    entry = MockConfigEntry(
        domain="energy_window_tracker",
        title="Rename",
        data={
            "sources": [
                {
                    "source_entity": "sensor.today_load",
                    "name": "Energy",
                    "windows": [
                        {"name": "Peak", "start": "09:00", "end": "12:00"},
                        {"name": "Off-Peak", "start": "12:00", "end": "17:00"},
                    ],
                }
            ]
        },
        options={},
        entry_id="rename_entry_id",
    )
    entry.add_to_hass(hass)
    hass.states.async_set("sensor.today_load", "0")
    with patch(
        "custom_components.energy_window_tracker.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    initial = _unique_ids_by_entity_id(hass, entry.entry_id)
    assert set(initial.keys()) == {"sensor.today_load_peak", "sensor.today_load_off_peak"}

    # Rename "Peak" -> "Super Peak" and also reorder to mimic the UI edit behavior.
    hass.config_entries.async_update_entry(
        entry,
        options={
            "sources": [
                {
                    "source_entity": "sensor.today_load",
                    "name": "Energy",
                    "windows": [
                        {"name": "Off-Peak", "start": "12:00", "end": "17:00"},
                        {"name": "Super Peak", "start": "09:00", "end": "12:00"},
                    ],
                }
            ]
        },
    )

    assert await hass.config_entries.async_unload(entry.entry_id)
    with patch(
        "custom_components.energy_window_tracker.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    after = _unique_ids_by_entity_id(hass, entry.entry_id)
    # Off-Peak should be unchanged.
    assert after["sensor.today_load_off_peak"] == initial["sensor.today_load_off_peak"]
    # Renamed window should result in a different entity_id and unique_id.
    assert "sensor.today_load_super_peak" in after
    assert after["sensor.today_load_super_peak"] != initial["sensor.today_load_peak"]
