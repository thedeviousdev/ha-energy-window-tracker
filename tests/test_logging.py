"""Tests that verify all expected logging is emitted.

Uses pytest's caplog to capture log records and assert that key code paths
log at the expected levels. Enable debug for the component so debug/info/warning
are all visible.
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries, data_entry_flow
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from custom_components.energy_window_tracker.const import (
    CONF_NAME,
    CONF_SOURCE_ENTITY,
    CONF_SOURCES,
    CONF_WINDOWS,
    DOMAIN,
)

COMPONENT_LOGGERS = (
    "custom_components.energy_window_tracker",
    "custom_components.energy_window_tracker.config_flow",
    "custom_components.energy_window_tracker.sensor",
)


def _component_records(caplog):
    """Return log records from our component (any level)."""
    return [r for r in caplog.records if r.name.startswith("custom_components.energy_window_tracker")]


def _component_messages(caplog):
    """Return concatenated message text from component loggers."""
    return " ".join(r.message for r in _component_records(caplog))


@pytest.mark.asyncio
async def test_setup_and_unload_logging(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Setup and unload log entry_id and result."""
    for logger_name in COMPONENT_LOGGERS:
        caplog.set_level(logging.DEBUG, logger=logger_name)
    hass.states.async_set("sensor.today_load", "0")
    with patch(
        "custom_components.energy_window_tracker.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert "async_setup_entry: entry_id=" in _component_messages(caplog), "setup should log entry_id"

    caplog.clear()
    for logger_name in COMPONENT_LOGGERS:
        caplog.set_level(logging.DEBUG, logger=logger_name)
    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    assert "async_unload_entry: entry_id=" in _component_messages(caplog)
    assert "ok=" in _component_messages(caplog)


@pytest.mark.asyncio
async def test_config_flow_user_and_entity_selector_logging(
    hass: HomeAssistant,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """User step with valid source logs submitted keys, source_entity, and entity selector value."""
    for logger_name in COMPONENT_LOGGERS:
        caplog.set_level(logging.DEBUG, logger=logger_name)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_SOURCE_ENTITY: "sensor.today_load"},
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "windows"
    messages = _component_messages(caplog)
    assert "config flow step user: submitted keys=" in messages
    assert "source_entity=" in messages and "proceeding to windows" in messages
    assert "entity selector value:" in messages


@pytest.mark.asyncio
async def test_config_flow_windows_create_entry_logging(
    hass: HomeAssistant,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Submitting windows step that creates entry logs 'creating entry'."""
    for logger_name in COMPONENT_LOGGERS:
        caplog.set_level(logging.DEBUG, logger=logger_name)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_SOURCE_ENTITY: "sensor.today_load"},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "source_name": "My Energy",
            "name": "Peak",
            "start": "09:00",
            "end": "17:00",
        },
    )
    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    messages = _component_messages(caplog)
    assert "config flow step windows: creating entry" in messages
    assert "title=" in messages and "source=" in messages


@pytest.mark.asyncio
async def test_options_flow_save_logging(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Options flow save (e.g. update source) logs 'options flow: saved' and options reload."""
    for logger_name in COMPONENT_LOGGERS:
        caplog.set_level(logging.DEBUG, logger=logger_name)
    hass.states.async_set("sensor.today_load", "0")
    hass.states.async_set("sensor.today_import", "0")
    with patch(
        "custom_components.energy_window_tracker.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        opts_result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            opts_result["flow_id"],
            {"next_step_id": "source_entity"},
        )
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                CONF_SOURCE_ENTITY: "sensor.today_import",
                CONF_NAME: "Import",
                "remove_previous_entities": True,
            },
        )
    assert result["type"] is data_entry_flow.FlowResultType.MENU
    await hass.async_block_till_done()
    messages = _component_messages(caplog)
    assert "options flow: saved" in messages
    assert "entry_id=" in messages and "source_entity=" in messages
    # Listener triggers reload; we see either update_options log or setup from reload
    assert "async_update_options" in messages or "async_setup_entry" in messages


@pytest.mark.asyncio
async def test_sensor_setup_and_load_logging(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Sensor setup logs 'added N sensor(s)'; load() logs load message."""
    for logger_name in COMPONENT_LOGGERS:
        caplog.set_level(logging.DEBUG, logger=logger_name)
    hass.states.async_set("sensor.today_load", "10.5")
    with patch(
        "custom_components.energy_window_tracker.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    messages = _component_messages(caplog)
    assert "added" in messages and "sensor(s)" in messages
    assert "load:" in messages
    assert "loaded" in messages or "no stored data" in messages


@pytest.mark.asyncio
async def test_sensor_get_source_value_non_numeric_logging(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """When source state is not numeric, get_source_value logs debug."""
    for logger_name in COMPONENT_LOGGERS:
        caplog.set_level(logging.DEBUG, logger=logger_name)
    hass.states.async_set("sensor.today_load", "not_a_number")
    with patch(
        "custom_components.energy_window_tracker.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    messages = _component_messages(caplog)
    assert "get_source_value" in messages
    assert "not numeric" in messages or "state not numeric" in messages


def _get_sensor_entity(hass: HomeAssistant, entry_id: str):
    """Return first WindowEnergySensor for this config entry, or None."""
    registry = er.async_get(hass)
    entities = [
        e
        for e in registry.entities.get_entries_for_config_entry_id(entry_id)
        if e.domain == SENSOR_DOMAIN
    ]
    if not entities:
        return None
    entity_id = entities[0].entity_id
    comp = hass.data.get("entity_components", {}).get(SENSOR_DOMAIN)
    if comp is None:
        return None
    return comp.get_entity(entity_id)


@pytest.mark.asyncio
async def test_sensor_midnight_reset_logging(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """_handle_midnight logs reset message."""
    for logger_name in COMPONENT_LOGGERS:
        caplog.set_level(logging.DEBUG, logger=logger_name)
    hass.states.async_set("sensor.today_load", "0")
    with patch(
        "custom_components.energy_window_tracker.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    entity = _get_sensor_entity(hass, mock_config_entry.entry_id)
    if entity is None or not hasattr(entity, "_data"):
        pytest.skip("could not get sensor entity to call _handle_midnight")
    caplog.clear()
    for logger_name in COMPONENT_LOGGERS:
        caplog.set_level(logging.DEBUG, logger=logger_name)
    entity._data._handle_midnight(dt_util.now())
    messages = _component_messages(caplog)
    assert "_handle_midnight" in messages or "resetting snapshots" in messages


@pytest.mark.asyncio
async def test_sensor_save_logging(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """When a snapshot is saved (e.g. window start), save() logs debug."""
    for logger_name in COMPONENT_LOGGERS:
        caplog.set_level(logging.DEBUG, logger=logger_name)
    hass.states.async_set("sensor.today_load", "5.0")
    with patch(
        "custom_components.energy_window_tracker.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ), patch(
        "custom_components.energy_window_tracker.sensor.Store.async_save",
        new_callable=AsyncMock,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    entity = _get_sensor_entity(hass, mock_config_entry.entry_id)
    if entity is None or not hasattr(entity, "_data"):
        pytest.skip("could not get sensor entity")
    caplog.clear()
    for logger_name in COMPONENT_LOGGERS:
        caplog.set_level(logging.DEBUG, logger=logger_name)
    # Call _handle_window_start to trigger save() and its log
    window = entity._data._windows[0]
    entity._data._handle_window_start(window, dt_util.now())
    await hass.async_block_till_done()
    messages = _component_messages(caplog)
    assert "Window" in messages and ("start:" in messages or "kWh" in messages)
    assert "save:" in messages or "window(s)" in messages


@pytest.mark.asyncio
async def test_sensor_cost_calc_fail_logging(
    hass: HomeAssistant,
    mock_config_entry_data: dict,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """When cost calculation fails in _update_value, we log debug."""
    data = dict(mock_config_entry_data)
    data[CONF_SOURCES][0][CONF_WINDOWS][0]["cost_per_kwh"] = 0.15
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    entry = MockConfigEntry(domain=DOMAIN, title="Test", data=data, options={}, entry_id="cost_test_id")
    entry.add_to_hass(hass)
    for logger_name in COMPONENT_LOGGERS:
        caplog.set_level(logging.DEBUG, logger=logger_name)
    hass.states.async_set("sensor.today_load", "10")
    with patch(
        "custom_components.energy_window_tracker.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    entity = _get_sensor_entity(hass, entry.entry_id)
    if entity is None or not hasattr(entity, "_data"):
        pytest.skip("could not get sensor entity")
    # Patch get_window_value to return non-numeric value so cost calc fails
    def bad_value(window):
        return ("not_a_float", "during_window")
    entity._data.get_window_value = bad_value
    caplog.clear()
    for logger_name in COMPONENT_LOGGERS:
        caplog.set_level(logging.DEBUG, logger=logger_name)
    entity._update_value()
    messages = _component_messages(caplog)
    assert "_update_value" in messages and "cost" in messages
