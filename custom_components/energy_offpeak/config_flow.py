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
    """Convert time object or string to HH:MM format."""
    if t is None:
        return "00:00"
    if hasattr(t, "strftime"):
        return t.strftime("%H:%M")
    if hasattr(t, "hour") and hasattr(t, "minute"):
        return f"{t.hour:02d}:{t.minute:02d}"
    if isinstance(t, str):
        return t[:5] if len(t) >= 5 else t
    return str(t)


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
CONF_WINDOW_NAME_FIELD = "window_name"


def _build_user_schema(
    default_name: str = "",
    default_window_name: str = "",
    default_start: str = DEFAULT_WINDOW_START,
    default_end: str = DEFAULT_WINDOW_END,
) -> vol.Schema:
    """Build single-step schema: sensor name, energy sensor, window name, start, end."""
    return vol.Schema({
        vol.Optional(CONF_SENSOR_NAME, default=default_name): str,
        vol.Required(
            CONF_SOURCE_ENTITY,
            default="sensor.today_energy_import",
        ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
        vol.Optional(CONF_WINDOW_NAME_FIELD, default=default_window_name): str,
        vol.Optional(CONF_WINDOW_START, default=default_start): selector.TimeSelector(),
        vol.Optional(CONF_WINDOW_END, default=default_end): selector.TimeSelector(),
    })


def _build_options_schema(
    default_name: str,
    default_window_name: str,
    default_start: str,
    default_end: str,
) -> vol.Schema:
    """Build options schema: sensor name, window name, start, end (no entity change)."""
    return vol.Schema({
        vol.Optional(CONF_SENSOR_NAME, default=default_name): str,
        vol.Optional(CONF_WINDOW_NAME_FIELD, default=default_window_name): str,
        vol.Optional(CONF_WINDOW_START, default=default_start): selector.TimeSelector(),
        vol.Optional(CONF_WINDOW_END, default=default_end): selector.TimeSelector(),
    })


class EnergyWindowConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Energy Window Tracker."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Single step: sensor name, energy sensor, window name, start time, end time."""
        errors: dict[str, str] = {}

        if user_input is not None:
            source_entity = user_input[CONF_SOURCE_ENTITY]
            start = _time_to_str(user_input.get(CONF_WINDOW_START, "00:00"))
            end = _time_to_str(user_input.get(CONF_WINDOW_END, "00:00"))
            if start >= end:
                errors["base"] = "window_start_after_end"
                return self.async_show_form(
                    step_id="user",
                    data_schema=_build_user_schema(
                        default_name=user_input.get(CONF_SENSOR_NAME) or "",
                        default_window_name=user_input.get(CONF_WINDOW_NAME_FIELD) or "",
                        default_start=start,
                        default_end=end,
                    ),
                    errors=errors,
                )
            source_name = (user_input.get(CONF_SENSOR_NAME) or "").strip() or _get_entity_friendly_name(
                self.hass, source_entity
            )
            window_name = (user_input.get(CONF_WINDOW_NAME_FIELD) or "").strip() or DEFAULT_NAME
            window = {
                CONF_WINDOW_START: start,
                CONF_WINDOW_END: end,
                CONF_WINDOW_NAME: window_name or None,
            }
            windows = [window]
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
            step_id="user",
            data_schema=_build_user_schema(),
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
        """Single step: sensor name, window name, start time, end time."""
        current = {**self.config_entry.data, **self.config_entry.options}
        source_entity = current.get(CONF_SOURCE_ENTITY) or "sensor.today_energy_import"
        existing = current.get(CONF_WINDOWS) or []
        first = existing[0] if existing else {}
        default_name = current.get(CONF_NAME) or _get_entity_friendly_name(self.hass, source_entity)
        default_window_name = first.get(CONF_WINDOW_NAME) or first.get("name") or ""
        default_start = _time_to_str(first.get(CONF_WINDOW_START) or first.get("start") or DEFAULT_WINDOW_START)
        default_end = _time_to_str(first.get(CONF_WINDOW_END) or first.get("end") or DEFAULT_WINDOW_END)

        if user_input is not None:
            start = _time_to_str(user_input.get(CONF_WINDOW_START, "00:00"))
            end = _time_to_str(user_input.get(CONF_WINDOW_END, "00:00"))
            if start >= end:
                return self.async_show_form(
                    step_id="init",
                    data_schema=_build_options_schema(
                        user_input.get(CONF_SENSOR_NAME) or default_name,
                        user_input.get(CONF_WINDOW_NAME_FIELD) or "",
                        start,
                        end,
                    ),
                    errors={"base": "window_start_after_end"},
                )
            source_name = (user_input.get(CONF_SENSOR_NAME) or "").strip() or default_name
            window_name = (user_input.get(CONF_WINDOW_NAME_FIELD) or "").strip() or DEFAULT_NAME
            window = {
                CONF_WINDOW_START: start,
                CONF_WINDOW_END: end,
                CONF_WINDOW_NAME: window_name or None,
            }
            return self.async_create_entry(
                title="",
                data={
                    CONF_NAME: source_name,
                    CONF_SOURCE_ENTITY: source_entity,
                    CONF_WINDOWS: [window],
                },
            )

        return self.async_show_form(
            step_id="init",
            data_schema=_build_options_schema(
                default_name,
                default_window_name,
                default_start,
                default_end,
            ),
        )
