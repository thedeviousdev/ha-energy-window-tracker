"""Edge case tests for Energy Window Tracker.

Covers validation boundaries, malformed config, empty data, and unusual flows
that should not crash and should behave predictably.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries, data_entry_flow
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.energy_window_tracker.const import (
    CONF_COST_PER_KWH,
    CONF_NAME,
    CONF_SOURCE_ENTITY,
    CONF_SOURCES,
    CONF_WINDOW_END,
    CONF_WINDOW_NAME,
    CONF_WINDOW_START,
    CONF_WINDOWS,
    DOMAIN,
)


def _get_tracker_sensors(hass: HomeAssistant, entry_id: str) -> list:
    """Return entity entries for our config entry (sensor domain)."""
    registry = er.async_get(hass)
    return [
        e
        for e in registry.entities.get_entries_for_config_entry_id(entry_id)
        if e.domain == SENSOR_DOMAIN
    ]


def _get_sensor_entity(hass: HomeAssistant, entry_id: str):
    """Return first WindowEnergySensor for this config entry, or None."""
    entities = _get_tracker_sensors(hass, entry_id)
    if not entities:
        return None
    entity_id = entities[0].entity_id
    comp = hass.data.get("entity_components", {}).get(SENSOR_DOMAIN)
    if comp is None:
        return None
    return comp.get_entity(entity_id)


# ----- Config flow edge cases -----


@pytest.mark.asyncio
async def test_windows_step_start_equals_end_rejected(hass: HomeAssistant) -> None:
    """[Unhappy] Start time equal to end time yields no valid window."""
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
            "source_name": "Energy",
            "window_name": "Peak",
            "cost_per_kwh": 0,
            "start": "12:00",
            "end": "12:00",
        },
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result.get("errors", {}).get("base") in ("at_least_one_window", "window_start_after_end")


@pytest.mark.asyncio
async def test_windows_step_overlapping_ranges_rejected(hass: HomeAssistant) -> None:
    """[Unhappy] Second range starting before first range ends yields range_start_before_previous_end."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_SOURCE_ENTITY: "sensor.today_load"},
    )
    # Add another slot so we have two ranges
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "source_name": "Energy",
            "window_name": "Peak",
            CONF_COST_PER_KWH: 0,
            "start": "09:00",
            "end": "12:00",
            "add_another": True,
        },
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "windows"
    # Submit with overlapping ranges: 09:00-12:00 and 10:00-14:00 (10:00 < 12:00)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "source_name": "Energy",
            "window_name": "Peak",
            CONF_COST_PER_KWH: 0,
            "start": "09:00",
            "end": "12:00",
            "start_1": "10:00",
            "end_1": "14:00",
        },
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result.get("errors", {}).get("base") == "range_start_before_previous_end"


@pytest.mark.asyncio
async def test_windows_step_empty_window_name_creates_entry(hass: HomeAssistant) -> None:
    """[Happy] Empty or whitespace window name is allowed; entry created."""
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
            "source_name": "Energy",
            "window_name": "   ",
            "cost_per_kwh": 0,
            "start": "09:00",
            "end": "17:00",
        },
    )
    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    sources = result["data"][CONF_SOURCES]
    windows = sources[0][CONF_WINDOWS]
    assert windows[0][CONF_WINDOW_NAME] is None or windows[0][CONF_WINDOW_NAME] == ""


@pytest.mark.asyncio
async def test_windows_step_cost_zero_stored(hass: HomeAssistant) -> None:
    """[Happy] Cost per kWh zero is stored as 0."""
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
            "source_name": "Energy",
            "window_name": "Peak",
            "start": "09:00",
            "end": "17:00",
            CONF_COST_PER_KWH: 0,
        },
    )
    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    windows = result["data"][CONF_SOURCES][0][CONF_WINDOWS]
    assert windows[0].get(CONF_COST_PER_KWH) == 0.0


@pytest.mark.asyncio
async def test_options_add_window_invalid_time_range_shows_error(
    hass: HomeAssistant, mock_config_entry: ConfigEntry
) -> None:
    """[Unhappy] Options Add window with start >= end shows window_start_after_end."""
    hass.states.async_set("sensor.today_load", "0")
    with patch(
        "custom_components.energy_window_tracker.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        opts = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        opts["flow_id"],
        {"next_step_id": "add_window"},
    )
    assert result["step_id"] == "add_window"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "window_name": "Off-Peak",
            "cost_per_kwh": 0,
            "start": "18:00",
            "end": "06:00",
        },
    )
    # 18:00 >= 06:00 (next day not supported in simple time) -> invalid
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result.get("errors", {}).get("base") == "window_start_after_end"


@pytest.mark.asyncio
async def test_options_add_window_invalid_time_value_shows_field_error(
    hass: HomeAssistant, mock_config_entry: ConfigEntry
) -> None:
    """[Unhappy] Options Add window with invalid time value shows invalid_time error on field."""
    from homeassistant.data_entry_flow import InvalidData

    hass.states.async_set("sensor.today_load", "0")
    with patch(
        "custom_components.energy_window_tracker.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        opts = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        opts["flow_id"],
        {"next_step_id": "add_window"},
    )
    assert result["step_id"] == "add_window"
    try:
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "window_name": "Bad",
                "cost_per_kwh": 0,
                "start": "25:00",
                "end": "06:00",
            },
        )
        assert result["type"] is data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "add_window"
        assert result.get("errors", {}).get("start") == "invalid_time"
    except InvalidData:
        # Some HA versions reject invalid time values at schema level before flow logic runs.
        pass


@pytest.mark.asyncio
async def test_options_edit_window_invalid_time_range_shows_error(
    hass: HomeAssistant, mock_config_entry: ConfigEntry
) -> None:
    """[Unhappy] Options Edit window with start >= end shows error and keeps form."""
    hass.states.async_set("sensor.today_load", "0")
    with patch(
        "custom_components.energy_window_tracker.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        opts = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        opts["flow_id"],
        {"next_step_id": "list_windows"},
    )
    assert result["step_id"] in ("list_windows", "manage_windows")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"window_index": "0"},
    )
    assert result["step_id"] == "edit_window"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "window_name": "Peak",
            "cost_per_kwh": 0,
            "start": "17:00",
            "end": "09:00",
            "delete_this_window": False,
        },
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result.get("errors", {}).get("base") == "window_start_after_end"


@pytest.mark.asyncio
async def test_options_manage_windows_with_default_empty_window_name(
    hass: HomeAssistant,
) -> None:
    """[Happy] Manage windows with default (empty) name: select 'Window 1' opens edit form."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Energy",
        data={
            CONF_SOURCES: [
                {
                    CONF_SOURCE_ENTITY: "sensor.today_load",
                    CONF_NAME: "Energy",
                    CONF_WINDOWS: [
                        {
                            CONF_WINDOW_NAME: "",
                            CONF_WINDOW_START: "11:00",
                            CONF_WINDOW_END: "14:00",
                        }
                    ],
                }
            ]
        },
        options={},
        entry_id="test_entry_empty_name",
    )
    entry.add_to_hass(hass)
    hass.states.async_set("sensor.today_load", "0")
    with patch(
        "custom_components.energy_window_tracker.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        opts = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        opts["flow_id"],
        {"next_step_id": "list_windows"},
    )
    # List shows "Window 1" (fallback for empty name); select it
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"window_index": "0"},
    )
    # Should reach edit_window (not bounce back to list)
    assert result["step_id"] == "edit_window"


@pytest.mark.asyncio
async def test_options_manage_windows_empty_submit_returns_to_menu(
    hass: HomeAssistant, mock_config_entry: ConfigEntry
) -> None:
    """[Unhappy] When there are no windows, Manage windows submit returns to menu."""
    hass.states.async_set("sensor.today_load", "0")
    # Start with one window; delete it so we have zero
    with patch(
        "custom_components.energy_window_tracker.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        opts = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        opts["flow_id"],
        {"next_step_id": "list_windows"},
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"window_index": "0"},
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "window_name": "Peak",
            "cost_per_kwh": 0,
            "start": "09:00",
            "end": "17:00",
            "delete_this_window": True,
        },
    )
    # After save the options flow completes (options persist); flow closes
    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY


@pytest.mark.asyncio
async def test_options_add_window_add_another_then_save_two_ranges(
    hass: HomeAssistant, mock_config_entry: ConfigEntry
) -> None:
    """[Happy] Options Add window: Add another time range, submit with two ranges; entry has new window with 2 ranges."""
    hass.states.async_set("sensor.today_load", "0")
    with patch(
        "custom_components.energy_window_tracker.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ), patch.object(
        hass.config_entries,
        "async_reload",
        new_callable=AsyncMock,
    ):
        opts = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            opts["flow_id"],
            {"next_step_id": "add_window"},
        )
        assert result["step_id"] == "add_window"
        # First submit: one range, add_another=True
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "window_name": "Off-Peak",
                "cost_per_kwh": 0.1,
                "start": "00:00",
                "end": "07:00",
                "add_another": True,
            },
        )
        assert result["type"] is data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "add_window"
        # Second submit: two ranges (start_1, end_1), add_another=False
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "window_name": "Off-Peak",
                "cost_per_kwh": 0.1,
                "start": "00:00",
                "end": "07:00",
                "start_1": "23:00",
                "end_1": "23:59",
                "add_another": False,
            },
        )
    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    entry = hass.config_entries.async_get_entry(mock_config_entry.entry_id)
    assert entry
    sources = entry.options.get(CONF_SOURCES) or entry.data.get(CONF_SOURCES) or []
    windows = sources[0][CONF_WINDOWS]
    assert len(windows) == 3  # original Peak 09-17 + Off-Peak 00-07 + Off-Peak 23-23:59
    off_peak = [w for w in windows if (w.get(CONF_WINDOW_NAME) or "") == "Off-Peak"]
    assert len(off_peak) == 2
    assert off_peak[0][CONF_WINDOW_START] == "00:00" and off_peak[0][CONF_WINDOW_END] == "07:00"
    assert off_peak[1][CONF_WINDOW_START] == "23:00" and off_peak[1][CONF_WINDOW_END] == "23:59"


@pytest.mark.asyncio
async def test_options_manage_windows_shows_unique_names_only(
    hass: HomeAssistant,
) -> None:
    """[Happy] Manage windows list shows one option per unique window name."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Multi",
        data={
            CONF_SOURCES: [
                {
                    CONF_SOURCE_ENTITY: "sensor.today_load",
                    CONF_NAME: "Energy",
                    CONF_WINDOWS: [
                        {CONF_WINDOW_NAME: "Peak", CONF_WINDOW_START: "09:00", CONF_WINDOW_END: "12:00"},
                        {CONF_WINDOW_NAME: "Peak", CONF_WINDOW_START: "14:00", CONF_WINDOW_END: "17:00"},
                        {CONF_WINDOW_NAME: "Off-Peak", CONF_WINDOW_START: "12:00", CONF_WINDOW_END: "14:00"},
                    ],
                }
            ]
        },
        options={},
        entry_id="multi_ranges_id",
    )
    entry.add_to_hass(hass)
    hass.states.async_set("sensor.today_load", "0")
    with patch(
        "custom_components.energy_window_tracker.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        opts = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        opts["flow_id"],
        {"next_step_id": "list_windows"},
    )
    assert result["step_id"] in ("list_windows", "manage_windows")
    # Select option 1 (Off-Peak); proves list has at least 2 options (Peak=0, Off-Peak=1)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"window_index": "1"},
    )
    assert result["step_id"] == "edit_window"


@pytest.mark.asyncio
async def test_options_edit_window_replaces_all_ranges_for_that_name(
    hass: HomeAssistant,
) -> None:
    """[Happy] Editing a window by name replaces all ranges for that name with the new set."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Edit Ranges",
        data={
            CONF_SOURCES: [
                {
                    CONF_SOURCE_ENTITY: "sensor.today_load",
                    CONF_NAME: "Energy",
                    CONF_WINDOWS: [
                        {CONF_WINDOW_NAME: "Peak", CONF_WINDOW_START: "09:00", CONF_WINDOW_END: "12:00", CONF_COST_PER_KWH: 0.2},
                        {CONF_WINDOW_NAME: "Peak", CONF_WINDOW_START: "14:00", CONF_WINDOW_END: "17:00", CONF_COST_PER_KWH: 0.2},
                    ],
                }
            ]
        },
        options={},
        entry_id="edit_ranges_id",
    )
    entry.add_to_hass(hass)
    hass.states.async_set("sensor.today_load", "0")
    with patch(
        "custom_components.energy_window_tracker.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ), patch.object(
        hass.config_entries,
        "async_reload",
        new_callable=AsyncMock,
    ):
        opts = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            opts["flow_id"],
            {"next_step_id": "list_windows"},
        )
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {"window_index": "0"},
        )
        assert result["step_id"] == "edit_window"
        # Save with a single range (10:00-11:00); invalidate second slot so only one range is collected
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "window_name": "Peak",
                "cost_per_kwh": 0.25,
                "start": "10:00",
                "end": "11:00",
                "start_1": "11:00",
                "end_1": "11:00",  # start >= end so this range is not collected
                "delete_this_window": False,
            },
        )
    # After save the options flow completes so options persist
    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    entry = hass.config_entries.async_get_entry(entry.entry_id)
    assert entry
    sources = entry.options.get(CONF_SOURCES) or entry.data.get(CONF_SOURCES) or []
    windows = sources[0][CONF_WINDOWS]
    peak = [w for w in windows if (w.get(CONF_WINDOW_NAME) or "") == "Peak"]
    assert len(peak) == 1
    assert peak[0][CONF_WINDOW_START] == "10:00"
    assert peak[0][CONF_WINDOW_END] == "11:00"
    assert peak[0][CONF_COST_PER_KWH] == 0.25


@pytest.mark.asyncio
async def test_options_edit_window_preserves_window_order_in_list(
    hass: HomeAssistant,
) -> None:
    """[Happy] Editing a window does not change dropdown order (stored list order is preserved)."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Order",
        data={
            CONF_SOURCES: [
                {
                    CONF_SOURCE_ENTITY: "sensor.today_load",
                    CONF_NAME: "Energy",
                    CONF_WINDOWS: [
                        {CONF_WINDOW_NAME: "Peak", CONF_WINDOW_START: "09:00", CONF_WINDOW_END: "12:00", CONF_COST_PER_KWH: 0.2},
                        {CONF_WINDOW_NAME: "Off-Peak", CONF_WINDOW_START: "12:00", CONF_WINDOW_END: "17:00", CONF_COST_PER_KWH: 0.1},
                    ],
                }
            ]
        },
        options={},
        entry_id="order_preserve_id",
    )
    entry.add_to_hass(hass)
    hass.states.async_set("sensor.today_load", "0")
    with patch(
        "custom_components.energy_window_tracker.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ), patch.object(
        hass.config_entries,
        "async_reload",
        new_callable=AsyncMock,
    ):
        opts = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            opts["flow_id"],
            {"next_step_id": "list_windows"},
        )
        # Select option 0 (Peak)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {"window_index": "0"},
        )
        assert result["step_id"] == "edit_window"
        # Save with adjusted Peak range
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "window_name": "Peak",
                "cost_per_kwh": 0.25,
                "start": "10:00",
                "end": "11:00",
                "delete_this_window": False,
            },
        )
    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    entry2 = hass.config_entries.async_get_entry(entry.entry_id)
    assert entry2
    sources = entry2.options.get(CONF_SOURCES) or entry2.data.get(CONF_SOURCES) or []
    windows = sources[0][CONF_WINDOWS]
    # Peak should still be the first window group in the list.
    assert (windows[0].get(CONF_WINDOW_NAME) or "") == "Peak"


@pytest.mark.asyncio
async def test_options_edit_window_add_another_time_range_then_save(
    hass: HomeAssistant,
) -> None:
    """[Happy] Edit window: add another time range, then save; both ranges are persisted."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Edit Add Range",
        data={
            CONF_SOURCES: [
                {
                    CONF_SOURCE_ENTITY: "sensor.today_load",
                    CONF_NAME: "Energy",
                    CONF_WINDOWS: [
                        {CONF_WINDOW_NAME: "Peak", CONF_WINDOW_START: "09:00", CONF_WINDOW_END: "12:00", CONF_COST_PER_KWH: 0.2},
                    ],
                }
            ]
        },
        options={},
        entry_id="edit_add_range_id",
    )
    entry.add_to_hass(hass)
    hass.states.async_set("sensor.today_load", "0")
    with patch(
        "custom_components.energy_window_tracker.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ), patch.object(
        hass.config_entries,
        "async_reload",
        new_callable=AsyncMock,
    ):
        opts = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            opts["flow_id"],
            {"next_step_id": "list_windows"},
        )
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {"window_index": "0"},
        )
        assert result["step_id"] == "edit_window"
        # First submit: one range, add_another=True -> form re-shows with 2 slots
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "window_name": "Peak",
                "cost_per_kwh": 0.2,
                "start": "09:00",
                "end": "12:00",
                "add_another": True,
                "delete_this_window": False,
            },
        )
        assert result["type"] is data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "edit_window"
        # Second submit: two ranges (start_1, end_1), add_another=False -> save
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "window_name": "Peak",
                "cost_per_kwh": 0.2,
                "start": "09:00",
                "end": "12:00",
                "start_1": "14:00",
                "end_1": "17:00",
                "add_another": False,
                "delete_this_window": False,
            },
        )
    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    entry = hass.config_entries.async_get_entry(entry.entry_id)
    assert entry
    sources = entry.options.get(CONF_SOURCES) or entry.data.get(CONF_SOURCES) or []
    windows = sources[0][CONF_WINDOWS]
    peak = [w for w in windows if (w.get(CONF_WINDOW_NAME) or "") == "Peak"]
    assert len(peak) == 2
    assert peak[0][CONF_WINDOW_START] == "09:00" and peak[0][CONF_WINDOW_END] == "12:00"
    assert peak[1][CONF_WINDOW_START] == "14:00" and peak[1][CONF_WINDOW_END] == "17:00"


@pytest.mark.asyncio
async def test_options_update_source_empty_entity_rejected(
    hass: HomeAssistant, mock_config_entry: ConfigEntry
) -> None:
    """[Unhappy] Options Update source with empty entity id is rejected (schema or flow)."""
    from homeassistant.data_entry_flow import InvalidData

    hass.states.async_set("sensor.today_load", "0")
    with patch(
        "custom_components.energy_window_tracker.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        opts = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        opts["flow_id"],
        {"next_step_id": "source_entity"},
    )
    try:
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                CONF_SOURCE_ENTITY: "",
                CONF_NAME: "Energy",
                "remove_previous_entities": False,
            },
        )
        assert result["type"] is data_entry_flow.FlowResultType.FORM
        assert result["step_id"] == "source_entity"
    except InvalidData:
        # Schema (EntitySelector) may reject empty before flow runs
        pass


@pytest.mark.asyncio
async def test_window_form_labels_built_from_start_time_end_time(hass: HomeAssistant) -> None:
    """[Happy] Labels for start/end fields are built from start_time/end_time + index."""
    from custom_components.energy_window_tracker.config_flow import (
        _data_key,
        _get_window_form_labels,
    )

    step_id = "add_window"
    trans = {
        _data_key(step_id, "start_time"): "Start time",
        _data_key(step_id, "end_time"): "End time",
    }
    with patch(
        "custom_components.energy_window_tracker.config_flow.async_get_translations",
        new_callable=AsyncMock,
        return_value=trans,
    ):
        labels = await _get_window_form_labels(hass, "options", step_id, num_ranges=3)

    assert labels["start"] == "1 - Start time"
    assert labels["end"] == "1 - End time"
    assert labels["start_1"] == "2 - Start time"
    assert labels["end_1"] == "2 - End time"
    assert labels["start_2"] == "3 - Start time"
    assert labels["end_2"] == "3 - End time"


@pytest.mark.asyncio
async def test_translation_contains_start_end_range_keys() -> None:
    """[Happy] Translations include labels for start/end and start_1/end_1 fields."""
    import json
    from pathlib import Path

    strings = json.loads(
        Path("custom_components/energy_window_tracker/strings.json").read_text()
    )
    for section in ("config", "options"):
        for step in ("windows", "add_window", "edit_window"):
            # "windows" only exists in config
            if section == "options" and step == "windows":
                continue
            data = strings[section]["step"][step]["data"]
            assert "start" in data and "end" in data
            assert "start_1" in data and "end_1" in data


@pytest.mark.asyncio
async def test_window_form_schema_descriptions_match_dynamic_labels(hass: HomeAssistant) -> None:
    """[Happy] Schema field descriptions match dynamic labels for any number of slots."""
    from custom_components.energy_window_tracker.config_flow import (
        _build_single_window_multi_range_schema,
        _get_window_form_labels,
    )

    step_id = "add_window"
    trans = {
        f"step.{step_id}.data.start_time": "Start time",
        f"step.{step_id}.data.end_time": "End time",
    }
    with patch(
        "custom_components.energy_window_tracker.config_flow.async_get_translations",
        new_callable=AsyncMock,
        return_value=trans,
    ):
        labels = await _get_window_form_labels(hass, "options", step_id, num_ranges=4)

    schema = _build_single_window_multi_range_schema(
        labels,
        None,
        "",
        0.0,
        [],
        include_add_another=True,
        include_delete=False,
        num_slots=4,
    )
    # Schema keys are vol.Optional with .description set to the label
    descriptions = {}
    for key in schema.schema:
        if getattr(key, "description", None) is not None:
            descriptions[key.schema] = key.description

    assert descriptions.get("start") == "1 - Start time"
    assert descriptions.get("end") == "1 - End time"
    assert descriptions.get("start_1") == "2 - Start time"
    assert descriptions.get("end_1") == "2 - End time"
    assert descriptions.get("start_2") == "3 - Start time"
    assert descriptions.get("end_2") == "3 - End time"
    assert descriptions.get("start_3") == "4 - Start time"
    assert descriptions.get("end_3") == "4 - End time"


# ----- Sensor / init edge cases -----


@pytest.mark.asyncio
async def test_setup_entry_empty_sources_no_entities(hass: HomeAssistant) -> None:
    """[Unhappy] Config entry with empty sources list: setup succeeds, no sensors created."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Empty",
        data={CONF_SOURCES: []},
        options={},
        entry_id="empty_sources_id",
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    sensors = _get_tracker_sensors(hass, entry.entry_id)
    assert len(sensors) == 0


@pytest.mark.asyncio
async def test_setup_entry_source_empty_windows_no_entities(hass: HomeAssistant) -> None:
    """[Unhappy] Config entry with source but empty windows: no sensors created."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="No Windows",
        data={
            CONF_SOURCES: [
                {
                    CONF_SOURCE_ENTITY: "sensor.today_load",
                    CONF_NAME: "Energy",
                    CONF_WINDOWS: [],
                }
            ]
        },
        options={},
        entry_id="empty_windows_id",
    )
    entry.add_to_hass(hass)
    hass.states.async_set("sensor.today_load", "0")
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    sensors = _get_tracker_sensors(hass, entry.entry_id)
    assert len(sensors) == 0


@pytest.mark.asyncio
async def test_setup_entry_source_not_dict_skipped(hass: HomeAssistant) -> None:
    """[Unhappy] Config entry with source that is not a dict: skipped, no crash, no sensors."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Bad Source",
        data={CONF_SOURCES: ["not a dict"]},
        options={},
        entry_id="bad_source_id",
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    sensors = _get_tracker_sensors(hass, entry.entry_id)
    assert len(sensors) == 0


@pytest.mark.asyncio
async def test_setup_entry_source_missing_source_entity_skipped(hass: HomeAssistant) -> None:
    """[Unhappy] Config entry with source dict missing source_entity: skipped, no sensors."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="No Entity",
        data={
            CONF_SOURCES: [
                {
                    CONF_NAME: "Energy",
                    CONF_WINDOWS: [
                        {CONF_WINDOW_NAME: "Peak", CONF_WINDOW_START: "09:00", CONF_WINDOW_END: "17:00"}
                    ],
                }
            ]
        },
        options={},
        entry_id="no_entity_id",
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    sensors = _get_tracker_sensors(hass, entry.entry_id)
    assert len(sensors) == 0


@pytest.mark.asyncio
async def test_sensor_source_unknown_state_reports_unavailable(
    hass: HomeAssistant, mock_config_entry: ConfigEntry
) -> None:
    """[Unhappy] When source entity state is 'unknown', sensor reports unavailable or unknown."""
    hass.states.async_set("sensor.today_load", "unknown")
    with patch(
        "custom_components.energy_window_tracker.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    sensors = _get_tracker_sensors(hass, mock_config_entry.entry_id)
    assert len(sensors) == 1
    state = hass.states.get(sensors[0].entity_id)
    assert state is not None
    assert state.state in ("unavailable", "unknown")


@pytest.mark.asyncio
async def test_sensor_source_unavailable_state_reports_unavailable(
    hass: HomeAssistant, mock_config_entry: ConfigEntry
) -> None:
    """[Unhappy] When source entity state is 'unavailable', sensor reports unavailable or unknown."""
    hass.states.async_set("sensor.today_load", "unavailable")
    with patch(
        "custom_components.energy_window_tracker.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    sensors = _get_tracker_sensors(hass, mock_config_entry.entry_id)
    state = hass.states.get(sensors[0].entity_id)
    assert state is not None
    assert state.state in ("unavailable", "unknown")


@pytest.mark.asyncio
async def test_sensor_source_numeric_state_reports_value(
    hass: HomeAssistant, mock_config_entry: ConfigEntry
) -> None:
    """[Happy] When source entity has numeric state, sensor reports a numeric value (0 or computed)."""
    hass.states.async_set("sensor.today_load", "5.25")
    with patch(
        "custom_components.energy_window_tracker.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    sensors = _get_tracker_sensors(hass, mock_config_entry.entry_id)
    assert len(sensors) == 1
    state = hass.states.get(sensors[0].entity_id)
    assert state is not None
    assert state.state not in ("unknown", "unavailable")
    assert state.attributes.get("source_entity") == "sensor.today_load"
    # Value is numeric (0 before/during window without snapshot, or computed)
    float(state.state)


@pytest.mark.asyncio
async def test_setup_entry_multiple_windows_creates_multiple_sensors(
    hass: HomeAssistant,
) -> None:
    """[Happy] Config entry with two windows creates two sensor entities."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Two Windows",
        data={
            CONF_SOURCES: [
                {
                    CONF_SOURCE_ENTITY: "sensor.today_load",
                    CONF_NAME: "Energy",
                    CONF_WINDOWS: [
                        {CONF_WINDOW_NAME: "Peak", CONF_WINDOW_START: "09:00", CONF_WINDOW_END: "12:00"},
                        {CONF_WINDOW_NAME: "Off-Peak", CONF_WINDOW_START: "12:00", CONF_WINDOW_END: "17:00"},
                    ],
                }
            ]
        },
        options={},
        entry_id="two_windows_id",
    )
    entry.add_to_hass(hass)
    hass.states.async_set("sensor.today_load", "5.0")
    with patch(
        "custom_components.energy_window_tracker.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    sensors = _get_tracker_sensors(hass, entry.entry_id)
    assert len(sensors) == 2
    starts = set()
    for s in sensors:
        state = hass.states.get(s.entity_id)
        if state and state.attributes.get("ranges"):
            starts.add(state.attributes["ranges"][0]["start"])
    assert "09:00" in starts and "12:00" in starts


@pytest.mark.asyncio
async def test_storage_load_none_no_crash(hass: HomeAssistant, mock_config_entry: ConfigEntry) -> None:
    """[Unhappy] Store.async_load returning None (no stored data) does not crash load()."""
    hass.states.async_set("sensor.today_load", "0")
    with patch(
        "custom_components.energy_window_tracker.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value=None,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    sensors = _get_tracker_sensors(hass, mock_config_entry.entry_id)
    assert len(sensors) == 1
    state = hass.states.get(sensors[0].entity_id)
    assert state is not None


@pytest.mark.asyncio
async def test_storage_load_empty_dict_creates_entities(
    hass: HomeAssistant, mock_config_entry: ConfigEntry
) -> None:
    """[Happy] When Store.async_load returns empty dict, setup creates entities and sensor has state."""
    hass.states.async_set("sensor.today_load", "1.5")
    with patch(
        "custom_components.energy_window_tracker.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    sensors = _get_tracker_sensors(hass, mock_config_entry.entry_id)
    assert len(sensors) == 1
    state = hass.states.get(sensors[0].entity_id)
    assert state is not None
    assert state.attributes.get("source_entity") == "sensor.today_load"
    assert "ranges" in state.attributes
    assert state.state not in ("unknown", "unavailable")


@pytest.mark.asyncio
async def test_unload_when_not_loaded_no_crash(hass: HomeAssistant) -> None:
    """[Unhappy] Unloading an entry that was never set up does not crash."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Never Setup",
        data={CONF_SOURCES: []},
        options={},
        entry_id="never_setup_id",
    )
    entry.add_to_hass(hass)
    # Do not call async_setup
    result = await hass.config_entries.async_unload(entry.entry_id)
    assert result is True


# ----- State written when source changes (last_updated advances) -----


@pytest.mark.asyncio
async def test_sensor_writes_state_when_source_value_changes_even_if_displayed_unchanged(
    hass: HomeAssistant, mock_config_entry: ConfigEntry
) -> None:
    """[Happy] (Single range.) When source value changes but displayed value and status stay the same, we still write state (last_updated advances)."""
    noon_today = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
    hass.states.async_set("sensor.today_load", "1.0")
    with patch(
        "custom_components.energy_window_tracker.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ), patch(
        "custom_components.energy_window_tracker.sensor.dt_util.now",
        return_value=noon_today,
    ), patch(
        "custom_components.energy_window_tracker.sensor.WindowData.take_late_start_snapshot",
        return_value=False,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    entity = _get_sensor_entity(hass, mock_config_entry.entry_id)
    assert entity is not None
    with patch.object(entity, "async_write_ha_state") as mock_write:
        entity._handle_data_update()
        first_calls = mock_write.call_count
        hass.states.async_set("sensor.today_load", "2.0")
        await hass.async_block_till_done()
        entity._handle_data_update()
        second_calls = mock_write.call_count
    assert second_calls > first_calls, "async_write_ha_state should be called again when source value changes (so last_updated advances)"


@pytest.mark.asyncio
async def test_sensor_does_not_write_state_when_source_value_unchanged(
    hass: HomeAssistant, mock_config_entry: ConfigEntry
) -> None:
    """[Unhappy] (Single range.) When source value does not change (and value/status unchanged), we do not write state again (no redundant write)."""
    noon_today = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
    hass.states.async_set("sensor.today_load", "1.0")
    with patch(
        "custom_components.energy_window_tracker.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ), patch(
        "custom_components.energy_window_tracker.sensor.dt_util.now",
        return_value=noon_today,
    ), patch(
        "custom_components.energy_window_tracker.sensor.WindowData.take_late_start_snapshot",
        return_value=False,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    entity = _get_sensor_entity(hass, mock_config_entry.entry_id)
    assert entity is not None
    with patch.object(entity, "async_write_ha_state") as mock_write:
        entity._handle_data_update()
        first_calls = mock_write.call_count
        entity._handle_data_update()
        second_calls = mock_write.call_count
    assert second_calls == first_calls, "async_write_ha_state should not be called again when source value is unchanged"


def _multi_range_config_entry():
    """Config entry with one window name and multiple time ranges (e.g. Shoulder: 00:00-11:00, 14:00-16:00, 23:00-23:59)."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Multi-Range",
        data={
            CONF_SOURCES: [
                {
                    CONF_SOURCE_ENTITY: "sensor.today_load",
                    CONF_NAME: "Energy",
                    CONF_WINDOWS: [
                        {CONF_WINDOW_NAME: "Shoulder", CONF_WINDOW_START: "00:00", CONF_WINDOW_END: "11:00"},
                        {CONF_WINDOW_NAME: "Shoulder", CONF_WINDOW_START: "14:00", CONF_WINDOW_END: "16:00"},
                        {CONF_WINDOW_NAME: "Shoulder", CONF_WINDOW_START: "23:00", CONF_WINDOW_END: "23:59"},
                    ],
                }
            ]
        },
        options={},
        entry_id="multi_range_entry_id",
    )


@pytest.mark.asyncio
async def test_sensor_writes_state_when_source_changes_multiple_ranges(
    hass: HomeAssistant,
) -> None:
    """[Happy] (Multiple ranges.) Same as single-range: when source value changes we write state (last_updated advances)."""
    entry = _multi_range_config_entry()
    entry.add_to_hass(hass)
    noon_today = datetime.now().replace(hour=15, minute=0, second=0, microsecond=0)
    hass.states.async_set("sensor.today_load", "1.0")
    with patch(
        "custom_components.energy_window_tracker.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ), patch(
        "custom_components.energy_window_tracker.sensor.dt_util.now",
        return_value=noon_today,
    ), patch(
        "custom_components.energy_window_tracker.sensor.WindowData.take_late_start_snapshot",
        return_value=False,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    entity = _get_sensor_entity(hass, entry.entry_id)
    assert entity is not None
    assert len(entity._ranges) == 3
    with patch.object(entity, "async_write_ha_state") as mock_write:
        entity._handle_data_update()
        first_calls = mock_write.call_count
        hass.states.async_set("sensor.today_load", "2.0")
        await hass.async_block_till_done()
        entity._handle_data_update()
        second_calls = mock_write.call_count
    assert second_calls > first_calls, "async_write_ha_state should be called again when source value changes (multi-range)"


@pytest.mark.asyncio
async def test_sensor_does_not_write_state_when_source_unchanged_multiple_ranges(
    hass: HomeAssistant,
) -> None:
    """[Unhappy] (Multiple ranges.) Same as single-range: when source value unchanged we do not write again."""
    entry = _multi_range_config_entry()
    entry.add_to_hass(hass)
    noon_today = datetime.now().replace(hour=15, minute=0, second=0, microsecond=0)
    hass.states.async_set("sensor.today_load", "1.0")
    with patch(
        "custom_components.energy_window_tracker.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ), patch(
        "custom_components.energy_window_tracker.sensor.dt_util.now",
        return_value=noon_today,
    ), patch(
        "custom_components.energy_window_tracker.sensor.WindowData.take_late_start_snapshot",
        return_value=False,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    entity = _get_sensor_entity(hass, entry.entry_id)
    assert entity is not None
    assert len(entity._ranges) == 3
    with patch.object(entity, "async_write_ha_state") as mock_write:
        entity._handle_data_update()
        first_calls = mock_write.call_count
        entity._handle_data_update()
        second_calls = mock_write.call_count
    assert second_calls == first_calls, "async_write_ha_state should not be called again when source unchanged (multi-range)"


# ----- Snapshot date validation (stale snapshots discarded for daily-reset sources) -----


@pytest.mark.asyncio
async def test_load_keeps_snapshots_when_stored_date_is_today(
    hass: HomeAssistant, mock_config_entry: ConfigEntry
) -> None:
    """[Happy] When stored snapshot_date is today, load() keeps snapshots and they are used for get_window_value."""
    noon_today = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
    today = noon_today.date().isoformat()
    stored = {
        "snapshot_date": today,
        "windows": {"0": {"snapshot_start": 1.0, "snapshot_end": None}},
    }
    hass.states.async_set("sensor.today_load", "3.5")
    with patch(
        "custom_components.energy_window_tracker.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value=stored,
    ), patch(
        "custom_components.energy_window_tracker.sensor.dt_util.now",
        return_value=noon_today,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        entity = _get_sensor_entity(hass, mock_config_entry.entry_id)
        assert entity is not None and hasattr(entity, "_data")
        data = entity._data
        assert data._snapshot_date == today
        assert data._snapshots[0].snapshot_start == 1.0
        value, status = data.get_window_value(data._windows[0])
        assert value == 2.5
        assert status == "during_window"
        sensors = _get_tracker_sensors(hass, mock_config_entry.entry_id)
        state = hass.states.get(sensors[0].entity_id)
        assert state is not None and float(state.state) == 2.5
        assert state.attributes.get("status") == "during_window"


@pytest.mark.asyncio
async def test_load_discards_snapshots_when_stored_date_not_today(
    hass: HomeAssistant, mock_config_entry: ConfigEntry
) -> None:
    """[Unhappy] When stored snapshot_date is not today, load() clears snapshots and sets _snapshot_date to today."""
    # Use a fixed old date so it never equals the integration's "today" (dt_util.now() may differ from date.today())
    stored_date = "2020-01-01"
    stored = {
        "snapshot_date": stored_date,
        "windows": {
            "0": {"snapshot_start": 100.0, "snapshot_end": 150.0},
        },
    }
    hass.states.async_set("sensor.today_load", "0")
    with patch(
        "custom_components.energy_window_tracker.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value=stored,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    entity = _get_sensor_entity(hass, mock_config_entry.entry_id)
    assert entity is not None and hasattr(entity, "_data")
    data = entity._data
    assert data._snapshot_date == dt_util.now().date().isoformat()
    # Stale stored values (100, 150) must not be used; may be None or a new late-start snapshot (e.g. 0)
    assert data._snapshots[0].snapshot_start != 100.0
    assert data._snapshots[0].snapshot_end != 150.0


@pytest.mark.asyncio
async def test_get_window_value_ignores_snapshots_when_date_not_today(
    hass: HomeAssistant, mock_config_entry: ConfigEntry
) -> None:
    """[Unhappy] get_window_value treats snapshots as missing when _snapshot_date is not today."""
    hass.states.async_set("sensor.today_load", "5.0")
    with patch(
        "custom_components.energy_window_tracker.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value={},
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    entity = _get_sensor_entity(hass, mock_config_entry.entry_id)
    assert entity is not None and hasattr(entity, "_data")
    data = entity._data
    window = data._windows[0]
    # Stale snapshot from another day: would wrongly give value = max(0, 5 - 100) = 0
    data._snapshot_date = "2020-01-01"
    from custom_components.energy_window_tracker.sensor import WindowSnapshots

    data._snapshots[window.index] = WindowSnapshots(snapshot_start=100.0, snapshot_end=150.0)
    # Freeze "now" to during window (09:00–17:00) so we're in the window
    noon_today = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
    with patch("custom_components.energy_window_tracker.sensor.dt_util.now", return_value=noon_today):
        value, status = data.get_window_value(window)
    # Should ignore stale snapshot and report no snapshot
    assert value == 0.0
    assert status == "during_window (no snapshot)"


@pytest.mark.asyncio
async def test_sensor_updates_after_load_with_yesterday_snapshots(
    hass: HomeAssistant, mock_config_entry: ConfigEntry
) -> None:
    """[Unhappy→recovery] After load with yesterday's stored data, sensor uses same-day snapshot and value updates correctly."""
    stored_date = "2020-01-01"  # Fixed old date so load() clears snapshots
    stored = {
        "snapshot_date": stored_date,
        "windows": {"0": {"snapshot_start": 100.0, "snapshot_end": 150.0}},
    }
    hass.states.async_set("sensor.today_load", "2.0")
    noon_today = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
    with patch(
        "custom_components.energy_window_tracker.sensor.Store.async_load",
        new_callable=AsyncMock,
        return_value=stored,
    ), patch(
        "custom_components.energy_window_tracker.sensor.dt_util.now",
        return_value=noon_today,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
        sensors = _get_tracker_sensors(hass, mock_config_entry.entry_id)
        assert len(sensors) == 1
        state = hass.states.get(sensors[0].entity_id)
        assert state is not None
        # Cleared snapshots -> either "during_window (no snapshot)" or "during_window" if late-start already ran
        assert state.attributes.get("status", "").startswith("during_window")
        assert state.state == "0.0"
        # Late-start snapshot (2.0) taken; source increase to 2.5 should show 0.5
        hass.states.async_set("sensor.today_load", "2.5")
        await hass.async_block_till_done()
        state = hass.states.get(sensors[0].entity_id)
        assert state is not None
        assert float(state.state) == 0.5
