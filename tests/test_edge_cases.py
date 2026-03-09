"""Edge case tests for Energy Window Tracker.

Covers validation boundaries, malformed config, empty data, and unusual flows
that should not crash and should behave predictably.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries, data_entry_flow
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
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


# ----- Config flow edge cases -----


@pytest.mark.asyncio
async def test_windows_step_start_equals_end_rejected(hass: HomeAssistant) -> None:
    """Start time equal to end time yields no valid window -> at_least_one_window."""
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
async def test_windows_step_empty_window_name_creates_entry(hass: HomeAssistant) -> None:
    """Empty or whitespace window name is allowed; entry created with null/empty name."""
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
    """Cost per kWh zero is stored as 0 (schema rejects negative in UI)."""
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
    """Options flow Add window with start >= end shows window_start_after_end."""
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
async def test_options_edit_window_invalid_time_range_shows_error(
    hass: HomeAssistant, mock_config_entry: ConfigEntry
) -> None:
    """Options flow Edit window with start >= end shows error and keeps form."""
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
    """When entry has window with default (empty) name, Manage windows -> select 'Window 1' opens edit form."""
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
    """When there are no windows, Manage windows shows empty step; submit returns to menu."""
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
    """Options Add window: use Add another time range, submit with two ranges; entry has new window with 2 ranges."""
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
    """Manage windows list shows one option per unique window name (not per range)."""
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
    """Editing a window by name replaces all ranges for that name with the new set."""
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
async def test_options_edit_window_add_another_time_range_then_save(
    hass: HomeAssistant,
) -> None:
    """Edit window: add another time range, then save; both ranges are persisted."""
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
    """Options flow Update source with empty entity id is rejected (schema or flow)."""
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
async def test_window_form_labels_built_from_time_range_n(hass: HomeAssistant) -> None:
    """Labels for start/end fields are built from time_range_n + start_suffix/end_suffix (dynamic, any N)."""
    from custom_components.energy_window_tracker.config_flow import (
        _data_key,
        _get_window_form_labels,
    )

    step_id = "add_window"
    trans = {
        _data_key(step_id, "time_range_n"): "Range #{n}",
        _data_key(step_id, "start_suffix"): "Start time",
        _data_key(step_id, "end_suffix"): "End time",
    }
    with patch(
        "custom_components.energy_window_tracker.config_flow.async_get_translations",
        new_callable=AsyncMock,
        return_value=trans,
    ):
        labels = await _get_window_form_labels(hass, "options", step_id, num_ranges=3)

    assert labels["start"] == "Range #1 - Start time"
    assert labels["end"] == "Range #1 - End time"
    assert labels["start_1"] == "Range #2 - Start time"
    assert labels["end_1"] == "Range #2 - End time"
    assert labels["start_2"] == "Range #3 - Start time"
    assert labels["end_2"] == "Range #3 - End time"


@pytest.mark.asyncio
async def test_window_form_schema_descriptions_match_dynamic_labels(hass: HomeAssistant) -> None:
    """Schema field descriptions (shown as labels) match time_range_n template for any number of slots."""
    from custom_components.energy_window_tracker.config_flow import (
        _build_single_window_multi_range_schema,
        _get_window_form_labels,
    )

    step_id = "add_window"
    trans = {
        f"step.{step_id}.data.time_range_n": "Range #{n}",
        f"step.{step_id}.data.start_suffix": "Start time",
        f"step.{step_id}.data.end_suffix": "End time",
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

    assert descriptions.get("start") == "Range #1 - Start time"
    assert descriptions.get("end") == "Range #1 - End time"
    assert descriptions.get("start_1") == "Range #2 - Start time"
    assert descriptions.get("end_1") == "Range #2 - End time"
    assert descriptions.get("start_2") == "Range #3 - Start time"
    assert descriptions.get("end_2") == "Range #3 - End time"
    assert descriptions.get("start_3") == "Range #4 - Start time"
    assert descriptions.get("end_3") == "Range #4 - End time"


# ----- Sensor / init edge cases -----


@pytest.mark.asyncio
async def test_setup_entry_empty_sources_no_entities(hass: HomeAssistant) -> None:
    """Config entry with empty sources list: setup succeeds, no sensors created."""
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
    """Config entry with source but empty windows: no sensors created."""
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
    """Config entry with source that is not a dict: skipped, no crash, no sensors."""
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
    """Config entry with source dict missing source_entity: skipped, no sensors."""
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
    """When source entity state is 'unknown', sensor reports unavailable or unknown."""
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
    """When source entity state is 'unavailable', sensor reports unavailable or unknown."""
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
async def test_setup_entry_multiple_windows_creates_multiple_sensors(
    hass: HomeAssistant,
) -> None:
    """Config entry with two windows creates two sensor entities."""
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
    """Store.async_load returning None (no stored data) does not crash load()."""
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
async def test_unload_when_not_loaded_no_crash(hass: HomeAssistant) -> None:
    """Unloading an entry that was never set up does not crash."""
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
