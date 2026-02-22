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


def _build_window_schema(defaults: dict) -> vol.Schema:
    """Build schema for adding a single window."""
    return vol.Schema(
        {
            vol.Required(
                CONF_WINDOW_START,
                default=defaults.get(CONF_WINDOW_START, DEFAULT_WINDOW_START),
            ): selector.TimeSelector(),
            vol.Required(
                CONF_WINDOW_END,
                default=defaults.get(CONF_WINDOW_END, DEFAULT_WINDOW_END),
            ): selector.TimeSelector(),
            vol.Optional(
                CONF_WINDOW_NAME,
                default=defaults.get(CONF_WINDOW_NAME, ""),
            ): str,
            vol.Required("add_another", default=False): bool,
        }
    )


class EnergyWindowConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Energy Window Tracker."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow."""
        self._windows: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle the initial step: name and source entity."""
        if user_input is not None:
            self._config = {
                CONF_NAME: user_input[CONF_NAME],
                CONF_SOURCE_ENTITY: user_input[CONF_SOURCE_ENTITY],
            }
            self._windows = []
            return await self.async_step_add_window()

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(
                    CONF_SOURCE_ENTITY,
                    default="sensor.today_energy_import",
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
        )

    async def async_step_add_window(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle adding a window (start, end, optional name)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            start = _time_to_str(user_input[CONF_WINDOW_START])
            end = _time_to_str(user_input[CONF_WINDOW_END])

            if start >= end:
                errors["base"] = "window_start_after_end"
            else:
                window_name = (user_input.get(CONF_WINDOW_NAME) or "").strip()
                self._windows.append(
                    {
                        CONF_WINDOW_START: start,
                        CONF_WINDOW_END: end,
                        CONF_WINDOW_NAME: window_name or None,
                    }
                )

                if user_input.get("add_another"):
                    return self.async_show_form(
                        step_id="add_window",
                        data_schema=_build_window_schema({}),
                        errors={},
                        description_placeholders={
                            "window_count": str(len(self._windows)),
                        },
                    )
                else:
                    if not self._windows:
                        errors["base"] = "at_least_one_window"
                        return self.async_show_form(
                            step_id="add_window",
                            data_schema=_build_window_schema({}),
                            errors=errors,
                            description_placeholders={"window_count": "0"},
                        )
                    windows_hash = hashlib.sha256(
                        str(sorted(w.items()) for w in self._windows).encode()
                    ).hexdigest()[:8]
                    unique_id = f"{self._config[CONF_SOURCE_ENTITY]}_{windows_hash}"
                    await self.async_set_unique_id(unique_id)
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title=self._config[CONF_NAME],
                        data={
                            **self._config,
                            CONF_WINDOWS: self._windows,
                        },
                    )

        defaults = {}
        if self._windows:
            defaults = self._windows[-1].copy()
            defaults[CONF_WINDOW_NAME] = defaults.get(CONF_WINDOW_NAME) or ""

        return self.async_show_form(
            step_id="add_window",
            data_schema=_build_window_schema(defaults),
            errors=errors,
            description_placeholders={
                "window_count": str(len(self._windows)),
            },
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
        self._windows: list[dict[str, Any]] = []

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Manage the options - replace windows from scratch."""
        current = {**self.config_entry.data, **self.config_entry.options}
        existing = current.get(CONF_WINDOWS) or current.get("periods", [])

        self._windows = []
        self._config = {
            CONF_NAME: current.get(CONF_NAME, DEFAULT_NAME),
            CONF_SOURCE_ENTITY: current.get(
                CONF_SOURCE_ENTITY, "sensor.today_energy_import"
            ),
        }
        self._default_window = existing[0] if existing else {}
        return await self.async_step_add_window()

    async def async_step_add_window(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle adding/editing windows."""
        errors: dict[str, str] = {}

        if user_input is not None:
            start = _time_to_str(user_input[CONF_WINDOW_START])
            end = _time_to_str(user_input[CONF_WINDOW_END])

            if start >= end:
                errors["base"] = "window_start_after_end"
            else:
                window_name = (user_input.get(CONF_WINDOW_NAME) or "").strip()
                self._windows.append(
                    {
                        CONF_WINDOW_START: start,
                        CONF_WINDOW_END: end,
                        CONF_WINDOW_NAME: window_name or None,
                    }
                )

                if user_input.get("add_another"):
                    return self.async_show_form(
                        step_id="add_window",
                        data_schema=_build_window_schema({}),
                        errors={},
                        description_placeholders={
                            "window_count": str(len(self._windows)),
                        },
                    )
                if not self._windows:
                    errors["base"] = "at_least_one_window"
                else:
                    return self.async_create_entry(
                        title="",
                        data={
                            **self._config,
                            CONF_WINDOWS: self._windows,
                        },
                    )

        defaults = {}
        if self._windows:
            last = self._windows[-1]
            defaults = {
                CONF_WINDOW_START: last[CONF_WINDOW_START],
                CONF_WINDOW_END: last[CONF_WINDOW_END],
                CONF_WINDOW_NAME: last.get(CONF_WINDOW_NAME) or "",
            }
        elif getattr(self, "_default_window", None):
            dw = self._default_window
            defaults = {
                CONF_WINDOW_START: dw.get(CONF_WINDOW_START)
                or dw.get("start", DEFAULT_WINDOW_START),
                CONF_WINDOW_END: dw.get(CONF_WINDOW_END)
                or dw.get("end", DEFAULT_WINDOW_END),
                CONF_WINDOW_NAME: dw.get(CONF_WINDOW_NAME) or dw.get("name") or "",
            }

        return self.async_show_form(
            step_id="add_window",
            data_schema=_build_window_schema(defaults),
            errors=errors,
            description_placeholders={
                "window_count": str(len(self._windows)),
            },
        )
