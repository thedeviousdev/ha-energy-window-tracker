"""Config flow for Energy Tracker."""

from __future__ import annotations

import logging
import re
from typing import Any

import voluptuous as vol

from homeassistant import config_entries, data_entry_flow
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_NAME,
    CONF_SOURCES,
    CONF_WINDOWS,
    CONF_WINDOW_END,
    CONF_WINDOW_NAME,
    CONF_WINDOW_START,
    CONF_SOURCE_ENTITY,
    DEFAULT_NAME,
    DEFAULT_SOURCE_ENTITY,
    DEFAULT_WINDOW_END,
    DEFAULT_WINDOW_START,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


# Only accept HH:MM or H:MM so schema defaults are always valid
_RE_HHMM = re.compile(r"^(\d{1,2}):(\d{2})$")


def _time_to_str(t: Any) -> str:
    """Convert time object or string to HH:MM format. Never raises. Invalid -> 00:00."""

    def valid(s: str) -> str:
        s = (s or "").strip()
        # Accept HH:MM:SS or HH:MM (e.g. frontend may send 09:00:00 or 9:00:00)
        if s.count(":") >= 2:
            s = s.rsplit(":", 1)[
                0
            ]  # drop seconds: "09:00:00" -> "09:00", "9:00:00" -> "9:00"
        elif len(s) > 5:
            s = s[:5]
        if _RE_HHMM.match(s):
            parts = s.split(":")
            h, m = int(parts[0], 10), int(parts[1], 10)
            if 0 <= h <= 23 and 0 <= m <= 59:
                return f"{h:02d}:{m:02d}"
        return "00:00"

    try:
        if t is None:
            return "00:00"
        if isinstance(t, str):
            return valid(t)
        if isinstance(t, dict):
            h = t.get("hour", t.get("hours", 0))
            m = t.get("minute", t.get("minutes", 0))
            return f"{int(h) % 24:02d}:{int(m) % 60:02d}"
        if hasattr(t, "strftime"):
            return valid(t.strftime("%H:%M"))
        if hasattr(t, "hour") and hasattr(t, "minute"):
            return f"{int(t.hour):02d}:{int(t.minute):02d}"
        return valid(str(t))
    except (TypeError, ValueError, AttributeError, KeyError):
        return "00:00"


def _get_entity_friendly_name(hass: Any, entity_id: str) -> str:
    """Get friendly name for an entity, fallback to entity id or default."""
    try:
        state = hass.states.get(entity_id)
        if state:
            name = state.attributes.get("friendly_name")
            if name:
                return str(name)[:200]
        if entity_id:
            return str(entity_id.split(".")[-1].replace("_", " ").title())[:200]
    except (TypeError, AttributeError, KeyError):
        pass
    return DEFAULT_NAME


def _normalize_windows_for_schema(raw: Any) -> list[dict[str, str]]:
    """Return a list of dicts with only string keys name/start/end for schema defaults. Never raises."""
    out: list[dict[str, str]] = []
    if not isinstance(raw, list):
        return out
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        out.append(
            {
                CONF_WINDOW_NAME: str(
                    item.get(CONF_WINDOW_NAME) or item.get("name") or ""
                )[:200],
                CONF_WINDOW_START: _time_to_str(
                    item.get(CONF_WINDOW_START) or item.get("start")
                ),
                CONF_WINDOW_END: _time_to_str(
                    item.get(CONF_WINDOW_END) or item.get("end")
                ),
            }
        )
    return out


def _build_step_user_schema() -> vol.Schema:
    """Build step 1 schema: energy source only."""
    return vol.Schema(
        {
            vol.Required(
                CONF_SOURCE_ENTITY,
                default=DEFAULT_SOURCE_ENTITY,
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
        }
    )


# Labels for config flow (single window)
_WINDOW_LABELS_CONFIG = ("Window name", "Start time", "End time")


def _window_labels(i: int) -> tuple[str, str, str]:
    """Return (name_label, start_label, end_label) for window row i (0-based)."""
    if i == 0:
        return _WINDOW_LABELS_CONFIG
    return (
        f"Window {i + 1} name",
        f"Window {i + 1} start time",
        f"Window {i + 1} end time",
    )


def _build_windows_schema(
    hass: Any,
    source_entity: str,
    existing_windows: list[dict] | None = None,
    num_rows: int = 1,
) -> vol.Schema:
    """Build schema: num_rows window rows (w{i}_name, w{i}_start, w{i}_end)."""
    existing = existing_windows or []
    if not isinstance(existing, list):
        existing = []

    schema_dict: dict[Any, Any] = {}
    for i in range(num_rows):
        name_lbl, start_lbl, end_lbl = _window_labels(i)
        if i < len(existing) and isinstance(existing[i], dict):
            ex = existing[i]
            name_val = ex.get(CONF_WINDOW_NAME) or ex.get("name") or ""
            start_val = _time_to_str(
                ex.get(CONF_WINDOW_START) or ex.get("start") or DEFAULT_WINDOW_START
            )
            end_val = _time_to_str(
                ex.get(CONF_WINDOW_END) or ex.get("end") or DEFAULT_WINDOW_END
            )
            schema_dict[
                vol.Optional(
                    f"w{i}_name",
                    default=name_val if isinstance(name_val, str) else "",
                    description=name_lbl,
                )
            ] = str
            schema_dict[
                vol.Optional(f"w{i}_start", default=start_val, description=start_lbl)
            ] = selector.TimeSelector()
            schema_dict[
                vol.Optional(f"w{i}_end", default=end_val, description=end_lbl)
            ] = selector.TimeSelector()
        else:
            # New row: default 00:00-00:00 so it is skipped unless user sets valid times
            schema_dict[
                vol.Optional(f"w{i}_name", default="", description=name_lbl)
            ] = str
            schema_dict[
                vol.Optional(f"w{i}_start", default="00:00", description=start_lbl)
            ] = selector.TimeSelector()
            schema_dict[
                vol.Optional(f"w{i}_end", default="00:00", description=end_lbl)
            ] = selector.TimeSelector()
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
        windows.append(
            {
                CONF_WINDOW_START: start,
                CONF_WINDOW_END: end,
                CONF_WINDOW_NAME: name or None,
            }
        )
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
    """Handle a config flow for Energy Tracker."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow."""
        self._source_entity: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Step 1: energy source only."""
        if user_input is not None:
            source_entity = user_input[CONF_SOURCE_ENTITY]
            # Validate entity not already in use by another entry
            for entry in self._async_current_entries():
                sources = (
                    entry.data.get(CONF_SOURCES)
                    or entry.options.get(CONF_SOURCES)
                    or []
                )
                for src in sources:
                    if (
                        isinstance(src, dict)
                        and src.get(CONF_SOURCE_ENTITY) == source_entity
                    ):
                        entry_title = entry.title or "Energy Tracker"
                        return self.async_show_form(
                            step_id="user",
                            data_schema=_build_step_user_schema(),
                            errors={"base": "source_already_in_use"},
                            description_placeholders={"entry_title": entry_title},
                        )
            self._source_entity = source_entity
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
                    ),
                    errors=errors,
                )
            source_name = _get_entity_friendly_name(self.hass, source_entity)
            # Entry title for "Integration entries": user-defined sensor name, or entity name, or default
            entry_title = (source_name or "Energy Tracker")[:200]
            # Single entry for the whole integration: all sources live under this one entry
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=entry_title,
                data={
                    CONF_SOURCES: [
                        {
                            CONF_NAME: source_name,
                            CONF_SOURCE_ENTITY: source_entity,
                            CONF_WINDOWS: windows,
                        }
                    ],
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


def _get_sources_from_entry(entry: config_entries.ConfigEntry) -> list[dict[str, Any]]:
    """Get list of sources from entry (CONF_SOURCES)."""
    current = {**entry.data, **(entry.options or {})}
    raw = current.get(CONF_SOURCES)
    if isinstance(raw, list):
        return list(raw)
    return []


def _build_init_menu_options() -> dict[str, str]:
    """Build main menu as step_id -> label (dict so labels show without translation lookup)."""
    return {
        "add_window": "✚ Add new window",
        "list_windows": "✏️ Manage windows",
        "source_entity": "⚡️ Update energy source",
    }


def _window_display_name(w: dict[str, Any], index: int) -> str:
    """Display name for a window (for list/dropdown labels)."""
    name = (w.get(CONF_WINDOW_NAME) or w.get("name") or "").strip()
    return name or f"Window {index + 1}"


def _build_select_window_schema(windows: list[dict[str, Any]]) -> vol.Schema:
    """Build schema for 'select a window' form: one dropdown, then user is taken to edit that window."""
    options = [
        {"value": str(i), "label": _window_display_name(w, i)}
        for i, w in enumerate(windows)
    ]
    return vol.Schema(
        {
            vol.Required(
                "window_index", description="Select a window"
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(options=options),
            ),
        }
    )


def _build_source_entity_schema(source_entity: str) -> vol.Schema:
    """Build schema for changing the source entity."""
    return vol.Schema(
        {
            vol.Required(
                CONF_SOURCE_ENTITY,
                default=source_entity or DEFAULT_SOURCE_ENTITY,
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
        }
    )


def _build_single_window_schema(
    window: dict[str, Any] | None = None,
    include_delete: bool = False,
) -> vol.Schema:
    """Build schema for add/edit single window. include_delete=True adds 'Delete this window' (edit only)."""
    w = window or {}
    name_val = str(w.get(CONF_WINDOW_NAME, "") or w.get("name", ""))[:200]
    start_val = _time_to_str(
        w.get(CONF_WINDOW_START) or w.get("start") or DEFAULT_WINDOW_START
    )
    end_val = _time_to_str(w.get(CONF_WINDOW_END) or w.get("end") or DEFAULT_WINDOW_END)
    schema_dict: dict[Any, Any] = {
        vol.Optional(
            CONF_WINDOW_NAME, default=name_val, description="Window name"
        ): str,
        vol.Optional(
            "w0_start", default=start_val, description="Start time"
        ): selector.TimeSelector(),
        vol.Optional(
            "w0_end", default=end_val, description="End time"
        ): selector.TimeSelector(),
    }
    if include_delete:
        schema_dict[
            vol.Optional("delete_this_window", default=False, description="❌ Delete?")
        ] = bool
    return vol.Schema(schema_dict)


class EnergyWindowOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow: Configure Energy Tracker — add/edit/delete windows, change source."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        super().__init__()
        self._config_entry = config_entry
        self._edit_index: int = 0
        self._delete_index: int = -1

    def _get_current_source(self) -> dict[str, Any]:
        """Get current source from entry."""
        sources = _get_sources_from_entry(self._config_entry)
        if not sources or not isinstance(sources[0], dict):
            raise ValueError("No source configured")
        return sources[0]

    def _save_source(self, source_entity: str, windows: list[dict[str, Any]]) -> None:
        """Persist source and windows to config entry."""
        source_name = _get_entity_friendly_name(self.hass, source_entity)
        new_source = {
            CONF_NAME: source_name,
            CONF_SOURCE_ENTITY: source_entity,
            CONF_WINDOWS: windows,
        }
        self.hass.config_entries.async_update_entry(
            self._config_entry,
            options={CONF_SOURCES: [new_source]},
        )

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Configure Energy Tracker: show menu (Add new window, Manage windows, Update energy source)."""
        try:
            return await self._async_step_manage_impl(user_input)
        except Exception as err:
            _LOGGER.exception(
                "Energy Tracker options flow failed: %s",
                err,
            )
            raise

    def _async_show_menu(
        self,
        step_id: str,
        menu_options: list[str] | dict[str, str],
        description_placeholders: dict[str, str] | None = None,
        description: str | None = None,
        title: str | None = None,
    ) -> config_entries.FlowResult:
        """Show a menu step. menu_options: list of step_ids or dict step_id->label. Optional description/title override translation."""
        result: config_entries.FlowResult = {
            "type": data_entry_flow.FlowResultType.MENU,
            "flow_id": self.flow_id,
            "handler": self.handler,
            "step_id": step_id,
            "menu_options": menu_options,
        }
        if description_placeholders:
            result["description_placeholders"] = description_placeholders
        if description is not None:
            result["description"] = description
        if title is not None:
            result["title"] = title
        return result

    async def _async_step_manage_impl(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Show Configure Energy Tracker menu."""
        src = self._get_current_source()
        source_entity = str(src.get(CONF_SOURCE_ENTITY) or DEFAULT_SOURCE_ENTITY)
        windows = _normalize_windows_for_schema(src.get(CONF_WINDOWS) or [])

        menu_options = _build_init_menu_options()
        return self._async_show_menu(
            step_id="init",
            menu_options=menu_options,
            description_placeholders={"windows_list": ""},
            title="Configure Energy Tracker",
        )

    async def _async_step_manage_windows_impl(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Show Manage windows: form to select a window, then user goes to edit that window."""
        src = self._get_current_source()
        windows = _normalize_windows_for_schema(src.get(CONF_WINDOWS) or [])
        if not windows:
            if user_input is not None:
                return await self._async_step_manage_impl(None)
            return self.async_show_form(
                step_id="manage_windows_empty",
                data_schema=vol.Schema({}),
            )
        if user_input is not None:
            raw = user_input.get("window_index")
            idx = int(raw[0] if isinstance(raw, list) else raw, 10)
            self._edit_index = idx
            return await self.async_step_edit_window(None)
        return self.async_show_form(
            step_id="manage_windows",
            data_schema=_build_select_window_schema(windows),
        )

    async def async_step_list_windows(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Entry from main menu (menu option 'Manage windows'): show list or empty state."""
        return await self._async_step_manage_windows_impl(user_input)

    async def async_step_manage_windows(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Show Manage windows list or empty state (e.g. when returning from edit/delete)."""
        return await self._async_step_manage_windows_impl(user_input)

    async def async_step_confirm_delete(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Confirm deletion of the window at _delete_index, then return to menu."""
        src = self._get_current_source()
        source_entity = str(src.get(CONF_SOURCE_ENTITY) or DEFAULT_SOURCE_ENTITY)
        windows = _normalize_windows_for_schema(src.get(CONF_WINDOWS) or [])
        idx = self._delete_index
        if idx < 0 or idx >= len(windows):
            return await self._async_step_manage_windows_impl(None)
        window_name = (
            windows[idx].get(CONF_WINDOW_NAME) or windows[idx].get("name") or ""
        ).strip() or f"Window {idx + 1}"
        if user_input is not None:
            new_windows = [w for i, w in enumerate(windows) if i != idx]
            self._save_source(source_entity, new_windows)
            return await self._async_step_manage_windows_impl(None)
        return self.async_show_form(
            step_id="confirm_delete",
            data_schema=vol.Schema({}),
            description_placeholders={"window_name": window_name},
        )

    async def async_step_source_entity(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Change the source entity (form), then return to menu."""
        src = self._get_current_source()
        source_entity = str(src.get(CONF_SOURCE_ENTITY) or DEFAULT_SOURCE_ENTITY)
        windows = _normalize_windows_for_schema(src.get(CONF_WINDOWS) or [])

        if user_input is not None:
            new_entity = user_input.get(CONF_SOURCE_ENTITY) or source_entity
            if new_entity:
                self._save_source(new_entity, windows)
            return await self._async_step_manage_impl(None)

        return self.async_show_form(
            step_id="source_entity",
            data_schema=_build_source_entity_schema(source_entity),
        )

    async def async_step_add_window(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Add a new window."""
        src = self._get_current_source()
        source_entity = str(src.get(CONF_SOURCE_ENTITY) or DEFAULT_SOURCE_ENTITY)
        windows = _normalize_windows_for_schema(src.get(CONF_WINDOWS) or [])

        if user_input is not None:
            start = _time_to_str(user_input.get("w0_start", "00:00"))
            end = _time_to_str(user_input.get("w0_end", "00:00"))
            if start >= end:
                return self.async_show_form(
                    step_id="add_window",
                    data_schema=_build_single_window_schema(
                        {
                            CONF_WINDOW_NAME: user_input.get(CONF_WINDOW_NAME, ""),
                            "start": start,
                            "end": end,
                        }
                    ),
                    errors={"base": "window_start_after_end"},
                )
            name = (user_input.get(CONF_WINDOW_NAME) or "").strip() or None
            new_window = {
                CONF_WINDOW_START: start,
                CONF_WINDOW_END: end,
                CONF_WINDOW_NAME: name,
            }
            windows.append(new_window)
            self._save_source(source_entity, windows)
            return await self._async_step_manage_impl(None)

        return self.async_show_form(
            step_id="add_window",
            data_schema=_build_single_window_schema(),
        )

    async def async_step_edit_window(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Edit an existing window."""
        src = self._get_current_source()
        source_entity = str(src.get(CONF_SOURCE_ENTITY) or DEFAULT_SOURCE_ENTITY)
        windows = _normalize_windows_for_schema(src.get(CONF_WINDOWS) or [])
        edit_index = self._edit_index

        if edit_index < 0 or edit_index >= len(windows):
            return await self._async_step_manage_windows_impl(None)

        if user_input is not None:
            if user_input.get("delete_this_window"):
                self._delete_index = edit_index
                return await self.async_step_confirm_delete(None)
            start = _time_to_str(user_input.get("w0_start", "00:00"))
            end = _time_to_str(user_input.get("w0_end", "00:00"))
            if start >= end:
                return self.async_show_form(
                    step_id="edit_window",
                    data_schema=_build_single_window_schema(
                        {
                            CONF_WINDOW_NAME: user_input.get(CONF_WINDOW_NAME, ""),
                            "start": start,
                            "end": end,
                        },
                        include_delete=True,
                    ),
                    errors={"base": "window_start_after_end"},
                )
            name = (user_input.get(CONF_WINDOW_NAME) or "").strip() or None
            windows[edit_index] = {
                CONF_WINDOW_START: start,
                CONF_WINDOW_END: end,
                CONF_WINDOW_NAME: name,
            }
            self._save_source(source_entity, windows)
            return await self._async_step_manage_windows_impl(None)

        return self.async_show_form(
            step_id="edit_window",
            data_schema=_build_single_window_schema(
                windows[edit_index], include_delete=True
            ),
        )
