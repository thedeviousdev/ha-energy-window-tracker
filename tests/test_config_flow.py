"""Tests for the Energy Window Tracker config flow.

Config flow tests verify form steps, validation, and create/options flows per
https://developers.home-assistant.io/docs/development_testing/
"""

from __future__ import annotations

import pytest
from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant

from custom_components.energy_window_tracker.const import (
    CONF_NAME,
    CONF_SOURCE_ENTITY,
    CONF_SOURCES,
    CONF_WINDOW_END,
    CONF_WINDOW_NAME,
    CONF_WINDOW_START,
    CONF_WINDOWS,
    DOMAIN,
)


@pytest.mark.asyncio
async def test_user_flow_show_form(hass: HomeAssistant) -> None:
    """Test initial user step shows the source entity form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"
    assert CONF_SOURCE_ENTITY in (result.get("data_schema") or {}).schema


@pytest.mark.asyncio
async def test_user_flow_empty_source_shows_error(hass: HomeAssistant) -> None:
    """Test that empty source entity is rejected (schema or flow validation)."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM

    try:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_SOURCE_ENTITY: ""},
        )
    except Exception as exc:
        # Newer HA: EntitySelector schema may reject empty string before flow runs
        if "Schema validation failed" in str(exc) or "InvalidData" in type(exc).__name__:
            return
        raise
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result.get("errors", {}).get("base") == "source_entity_required"


@pytest.mark.asyncio
async def test_user_flow_then_windows_then_create_entry(hass: HomeAssistant) -> None:
    """Test full flow: user step -> windows step -> create entry."""
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
    assert result["title"] == "My Energy"
    data = result["data"]
    assert CONF_SOURCES in data
    sources = data[CONF_SOURCES]
    assert len(sources) == 1
    assert sources[0][CONF_SOURCE_ENTITY] == "sensor.today_load"
    assert sources[0][CONF_NAME] == "My Energy"
    windows = sources[0][CONF_WINDOWS]
    assert len(windows) == 1
    assert windows[0][CONF_WINDOW_NAME] == "Peak"
    assert windows[0][CONF_WINDOW_START] == "09:00"
    assert windows[0][CONF_WINDOW_END] == "17:00"


@pytest.mark.asyncio
async def test_windows_validation_invalid_time_range(hass: HomeAssistant) -> None:
    """Test windows step rejects invalid time range (start >= end yields no valid window)."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_SOURCE_ENTITY: "sensor.today_load"},
    )
    assert result["step_id"] == "windows"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "source_name": "Energy",
            "name": "Peak",
            "start": "17:00",
            "end": "09:00",
        },
    )
    # Flow collects only windows with start < end; this row is skipped -> 0 windows -> at_least_one_window
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {"base": "at_least_one_window"}


@pytest.mark.asyncio
async def test_options_flow_init_shows_menu(
    hass: HomeAssistant, mock_config_entry: config_entries.ConfigEntry
) -> None:
    """Test options flow shows menu (Add window, Manage windows, Update energy source)."""
    entry = mock_config_entry
    opts_result = await hass.config_entries.options.async_init(entry.entry_id)
    assert opts_result["type"] is data_entry_flow.FlowResultType.MENU
    menu_options = opts_result.get("menu_options", [])
    if isinstance(menu_options, dict):
        assert "add_window" in menu_options
        assert "source_entity" in menu_options
    else:
        assert "add_window" in menu_options
        assert "source_entity" in menu_options


@pytest.mark.asyncio
async def test_options_flow_update_source_entity_form(
    hass: HomeAssistant, mock_config_entry: config_entries.ConfigEntry
) -> None:
    """Test options flow: choose Update energy source -> form (with or without prior confirm step)."""
    entry = mock_config_entry
    opts_result = await hass.config_entries.options.async_init(entry.entry_id)
    assert opts_result["type"] is data_entry_flow.FlowResultType.MENU

    result = await hass.config_entries.options.async_configure(
        opts_result["flow_id"],
        {"next_step_id": "source_entity"},
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    # Some flows show a confirm step first; if so, submit to reach the source_entity form
    if result["step_id"] == "source_entity_confirm":
        result = await hass.config_entries.options.async_configure(result["flow_id"], {})
        assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "source_entity"
    schema = result.get("data_schema")
    assert schema is not None
    schema_keys = {k for k in schema.schema}
    assert CONF_SOURCE_ENTITY in schema_keys
    assert CONF_NAME in schema_keys
