"""Config flow for Energy Window Tracker."""

from __future__ import annotations

import hashlib
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_NAME,
    CONF_WINDOWS,
    CONF_WINDOW_END,
    CONF_WINDOW_NAME,
    CONF_WINDOW_START,
    CONF_SOURCE_ENTITY,
    DEFAULT_NAME,
    DEFAULT_WINDOW_END,
    DEFAULT_WINDOW_START,
    DOMAIN,
)


def _time_to_str(t: Any) -> str:
    """Convert time object or string to HH:MM format. Never raises."""
    try:
        if t is None:
            return "00:00"
        if hasattr(t, "strftime"):
            return t.strftime("%H:%M")
        if hasattr(t, "hour") and hasattr(t, "minute"):
            return f"{int(t.hour):02d}:{int(t.minute):02d}"
        if isinstance(t, str):
            s = t.strip()[:5]
            return s if len(s) >= 5 else "00:00"
        s = str(t).strip()[:5]
        return s if len(s) >= 5 else "00:00"
    except (TypeError, ValueError, AttributeError):
        return "00:00"


def _get_entity_friendly_name(hass, entity_id: str) -> str:
    """Get friendly name for an entity, fallback to entity id or default."""
    state = hass.states.get(entity_id)
    if state:
        name = state.attributes.get("friendly_name")
        if name:
            return str(name)
    return entity_id.split(".")[-1].replace("_", " ").title() if entity_id else DEFAULT_NAME


# Form-only keys (to avoid CONF_NAME vs CONF_WINDOW_NAME both being "name")
CONF_SENSOR_NAME = "sensor_name"


def _build_step_user_schema(
    default_name: str = "",
) -> vol.Schema:
    """Build step 1 schema: sensor name and energy sensor only."""
    return vol.Schema({
        vol.Optional(CONF_SENSOR_NAME, default=default_name): str,
        vol.Required(
            CONF_SOURCE_ENTITY,
            default="sensor.today_energy_import",
        ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
    })


def _build_windows_schema(
    hass: Any,
    source_entity: str,
    existing_windows: list[dict] | None = None,
    default_source_name: str | None = None,
    num_rows: int = 1,
) -> vol.Schema:
    """Build schema: source name + num_rows window rows (w{i}_name, w{i}_start, w{i}_end)."""
    if default_source_name is not None:
        default_name = default_source_name
    else:
        default_name = _get_entity_friendly_name(hass, source_entity) if source_entity else DEFAULT_NAME
    default_name = str(default_name) if default_name else DEFAULT_NAME
    existing = existing_windows or []
    if not isinstance(existing, list):
        existing = []

    schema_dict: dict[Any, Any] = {
        vol.Required(CONF_NAME, default=default_name): str,
    }
    for i in range(num_rows):
        if i < len(existing) and isinstance(existing[i], dict):
            ex = existing[i]
            name_val = ex.get(CONF_WINDOW_NAME) or ex.get("name") or ""
            start_val = _time_to_str(ex.get(CONF_WINDOW_START) or ex.get("start") or DEFAULT_WINDOW_START)
            end_val = _time_to_str(ex.get(CONF_WINDOW_END) or ex.get("end") or DEFAULT_WINDOW_END)
            schema_dict[vol.Optional(f"w{i}_name", default=name_val if isinstance(name_val, str) else "")] = str
            schema_dict[vol.Optional(f"w{i}_start", default=start_val)] = selector.TimeSelector()
            schema_dict[vol.Optional(f"w{i}_end", default=end_val)] = selector.TimeSelector()
        else:
            # New row: default 00:00-00:00 so it is skipped unless user sets valid times
            schema_dict[vol.Optional(f"w{i}_name", default="")] = str
            schema_dict[vol.Optional(f"w{i}_start", default="00:00")] = selector.TimeSelector()
            schema_dict[vol.Optional(f"w{i}_end", default="00:00")] = selector.TimeSelector()
    return vol.Schema(schema_dict)


def _collect_windows_from_input(data: dict, num_rows: int) -> list[dict[str, Any]]:
    """Collect windows from form data for rows 0..num_rows-1 where start < end."""
    windows = []
    for i in range(num_rows):
        start = _time_to_str(data.get(f"w{i}_start", "00:00"))
        end = _time_to_str(data.get(f"w{i}_end", "00:00"))
        if start >= end:
            continue
        name = (data.get(f"w{i}_name") or "").strip()
        windows.append({
            CONF_WINDOW_START: start,
            CONF_WINDOW_END: end,
            CONF_WINDOW_NAME: name or None,
        })
    return windows


def _get_window_rows_from_input(data: dict, num_rows: int) -> list[dict[str, Any]]:
    """Get all row data from input for re-showing form after validation error."""
    return [
        {
            CONF_WINDOW_NAME: data.get(f"w{i}_name") or "",
            CONF_WINDOW_START: _time_to_str(data.get(f"w{i}_start", "00:00")),
            CONF_WINDOW_END: _time_to_str(data.get(f"w{i}_end", "00:00")),
        }
        for i in range(num_rows)
    ]


class EnergyWindowConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Energy Window Tracker."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow."""
        self._source_entity: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Step 1: sensor name and energy sensor only."""
        if user_input is not None:
            self._source_entity = user_input[CONF_SOURCE_ENTITY]
            return await self.async_step_windows()

        return self.async_show_form(
            step_id="user",
            data_schema=_build_step_user_schema(),
        )

    async def async_step_windows(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Step 2: source name and one window row."""
        errors: dict[str, str] = {}
        source_entity = self._source_entity or ""

        if user_input is not None:
            windows = _collect_windows_from_input(user_input, num_rows=1)
            if not windows:
                errors["base"] = "at_least_one_window"
                return self.async_show_form(
                    step_id="windows",
                    data_schema=_build_windows_schema(
                        self.hass,
                        source_entity,
                        _get_window_rows_from_input(user_input, 1),
                        default_source_name=user_input.get(CONF_NAME) or "",
                    ),
                    errors=errors,
                )
            start = _time_to_str(user_input.get("w0_start", "00:00"))
            end = _time_to_str(user_input.get("w0_end", "00:00"))
            if start >= end:
                errors["base"] = "window_start_after_end"
                return self.async_show_form(
                    step_id="windows",
                    data_schema=_build_windows_schema(
                        self.hass,
                        source_entity,
                        _get_window_rows_from_input(user_input, 1),
                        default_source_name=user_input.get(CONF_NAME) or "",
                    ),
                    errors=errors,
                )
            source_name = (user_input.get(CONF_NAME) or "").strip() or _get_entity_friendly_name(self.hass, source_entity)
            windows_hash = hashlib.sha256(
                str(sorted(w.items()) for w in windows).encode()
            ).hexdigest()[:8]
            unique_id = f"{source_entity}_{windows_hash}"
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=source_name,
                data={
                    CONF_NAME: source_name,
                    CONF_SOURCE_ENTITY: source_entity,
                    CONF_WINDOWS: windows,
                },
            )

        return self.async_show_form(
            step_id="windows",
            data_schema=_build_windows_schema(self.hass, source_entity),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> EnergyWindowOptionsFlow:
        """Get the options flow."""
        return EnergyWindowOptionsFlow(config_entry)


class EnergyWindowOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Single step: source name + dynamic window rows (existing + 1, no cap)."""
        options = self.config_entry.options or {}
        current = {**self.config_entry.data, **options}
        source_entity = current.get(CONF_SOURCE_ENTITY) or "sensor.today_energy_import"
        existing = current.get(CONF_WINDOWS) or []
        if not isinstance(existing, list):
            existing = []
        num_rows = min(len(existing) + 1, 30)  # Cap to avoid 500 from huge schema
        default_name = current.get(CONF_NAME) or _get_entity_friendly_name(self.hass, source_entity)

        if user_input is not None:
            windows = _collect_windows_from_input(user_input, num_rows)
            if not windows:
                return self.async_show_form(
                    step_id="init",
                    data_schema=_build_windows_schema(
                        self.hass,
                        source_entity,
                        _get_window_rows_from_input(user_input, num_rows),
                        default_source_name=user_input.get(CONF_NAME) or default_name,
                        num_rows=num_rows,
                    ),
                    errors={"base": "at_least_one_window"},
                )
            source_name = (user_input.get(CONF_NAME) or "").strip() or default_name
            new_options = {
                CONF_NAME: source_name,
                CONF_SOURCE_ENTITY: source_entity,
                CONF_WINDOWS: windows,
            }
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                options=new_options,
            )
            return self.async_create_entry(
                title="",
                data=new_options,
            )

        return self.async_show_form(
            step_id="init",
            data_schema=_build_windows_schema(
                self.hass,
                source_entity,
                list(existing),
                default_source_name=default_name,
                num_rows=num_rows,
            ),
        )
