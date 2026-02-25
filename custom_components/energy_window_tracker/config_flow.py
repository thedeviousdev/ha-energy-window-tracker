"""Config flow for Energy Window Tracker."""

from __future__ import annotations

import logging
import re
from typing import Any

import voluptuous as vol

from homeassistant import config_entries, data_entry_flow
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er, selector
from homeassistant.helpers.storage import Store

from .const import (
    CONF_COST_PER_KWH,
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


def _normalize_windows_for_schema(raw: Any) -> list[dict[str, Any]]:
    """Return a list of dicts with name/start/end/cost_per_kwh for schema defaults. Never raises."""
    out: list[dict[str, Any]] = []
    if not isinstance(raw, list):
        return out
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        cost = 0.0
        if CONF_COST_PER_KWH in item and item[CONF_COST_PER_KWH] is not None:
            try:
                cost = max(0.0, float(item[CONF_COST_PER_KWH]))
            except (TypeError, ValueError):
                pass
        out.append(
            {
                CONF_WINDOW_NAME: str(item.get(CONF_WINDOW_NAME) or "")[:200],
                CONF_WINDOW_START: _time_to_str(item.get(CONF_WINDOW_START)),
                CONF_WINDOW_END: _time_to_str(item.get(CONF_WINDOW_END)),
                CONF_COST_PER_KWH: cost,
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
_WINDOW_LABELS_CONFIG = ("Window name", "Start time", "End time", "Cost per kWh ($)")


def _window_labels(i: int) -> tuple[str, str, str, str]:
    """Return (name_label, start_label, end_label, cost_label) for window row i (0-based)."""
    if i == 0:
        return _WINDOW_LABELS_CONFIG
    return (
        f"Window {i + 1} name",
        f"Window {i + 1} start time",
        f"Window {i + 1} end time",
        f"Window {i + 1} cost per kWh ($)",
    )


def _build_windows_schema(
    hass: Any,
    source_entity: str,
    existing_windows: list[dict] | None = None,
    num_rows: int = 1,
    default_source_name: str | None = None,
    use_simple_keys: bool = False,
) -> vol.Schema:
    """Build schema: optional source name, then num_rows window rows. use_simple_keys=True uses name/start/end for row 0."""
    existing = existing_windows or []
    if not isinstance(existing, list):
        existing = []

    schema_dict: dict[Any, Any] = {}
    if default_source_name is not None:
        schema_dict[
            vol.Optional("source_name", default=default_source_name, description="Energy source name")
        ] = str
    for i in range(num_rows):
        name_lbl, start_lbl, end_lbl, cost_lbl = _window_labels(i)
        name_key = "name" if (use_simple_keys and i == 0) else f"w{i}_name"
        start_key = "start" if (use_simple_keys and i == 0) else f"w{i}_start"
        end_key = "end" if (use_simple_keys and i == 0) else f"w{i}_end"
        cost_key = CONF_COST_PER_KWH if (use_simple_keys and i == 0) else f"w{i}_{CONF_COST_PER_KWH}"
        if i < len(existing) and isinstance(existing[i], dict):
            ex = existing[i]
            name_val = ex.get(CONF_WINDOW_NAME) or ""
            start_val = _time_to_str(ex.get(CONF_WINDOW_START) or DEFAULT_WINDOW_START)
            end_val = _time_to_str(ex.get(CONF_WINDOW_END) or DEFAULT_WINDOW_END)
            cost_val = 0.0
            if CONF_COST_PER_KWH in ex and ex[CONF_COST_PER_KWH] is not None:
                try:
                    cost_val = max(0.0, float(ex[CONF_COST_PER_KWH]))
                except (TypeError, ValueError):
                    pass
            schema_dict[
                vol.Optional(
                    name_key,
                    default=name_val if isinstance(name_val, str) else "",
                    description=name_lbl,
                )
            ] = str
            schema_dict[
                vol.Optional(start_key, default=start_val, description=start_lbl)
            ] = selector.TimeSelector()
            schema_dict[
                vol.Optional(end_key, default=end_val, description=end_lbl)
            ] = selector.TimeSelector()
            schema_dict[
                vol.Optional(
                    cost_key,
                    default=cost_val,
                    description=cost_lbl,
                )
            ] = selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=0.00001, mode="box")
            )
        else:
            schema_dict[
                vol.Optional(name_key, default="", description=name_lbl)
            ] = str
            schema_dict[
                vol.Optional(start_key, default=DEFAULT_WINDOW_START, description=start_lbl)
            ] = selector.TimeSelector()
            schema_dict[
                vol.Optional(end_key, default=DEFAULT_WINDOW_END, description=end_lbl)
            ] = selector.TimeSelector()
            schema_dict[
                vol.Optional(
                    cost_key,
                    default=0,
                    description=cost_lbl,
                )
            ] = selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=100, step=0.00001, mode="box")
            )
    return vol.Schema(schema_dict)


def _parse_cost(v: Any) -> float:
    """Parse cost_per_kwh from user input; return 0 if missing or invalid."""
    if v is None:
        return 0.0
    try:
        return max(0.0, float(v))
    except (TypeError, ValueError):
        return 0.0


def _collect_windows_from_input(data: dict, num_rows: int, use_simple_keys: bool = False) -> list[dict[str, Any]]:
    """Collect windows from form data for rows 0..num_rows-1 where start < end."""
    windows = []
    for i in range(num_rows):
        if use_simple_keys and i == 0:
            start = _time_to_str(data.get("start") or "00:00")
            end = _time_to_str(data.get("end") or "00:00")
            name = (data.get("name") or "").strip()
            cost = _parse_cost(data.get(CONF_COST_PER_KWH))
        else:
            start = _time_to_str(data.get(f"w{i}_start", "00:00"))
            end = _time_to_str(data.get(f"w{i}_end", "00:00"))
            name = (data.get(f"w{i}_name") or "").strip()
            cost = _parse_cost(data.get(f"w{i}_{CONF_COST_PER_KWH}"))
        if start >= end:
            continue
        windows.append(
            {
                CONF_WINDOW_START: start,
                CONF_WINDOW_END: end,
                CONF_WINDOW_NAME: name or None,
                CONF_COST_PER_KWH: cost,
            }
        )
    return windows


def _get_window_rows_from_input(data: dict, num_rows: int, use_simple_keys: bool = False) -> list[dict[str, Any]]:
    """Get all row data from input for re-showing form after validation error."""
    rows = []
    for i in range(num_rows):
        if use_simple_keys and i == 0:
            rows.append({
                CONF_WINDOW_NAME: data.get("name") or "",
                CONF_WINDOW_START: _time_to_str(data.get("start") or "00:00"),
                CONF_WINDOW_END: _time_to_str(data.get("end") or "00:00"),
                CONF_COST_PER_KWH: _parse_cost(data.get(CONF_COST_PER_KWH)),
            })
        else:
            rows.append({
                CONF_WINDOW_NAME: data.get(f"w{i}_name") or "",
                CONF_WINDOW_START: _time_to_str(data.get(f"w{i}_start", "00:00")),
                CONF_WINDOW_END: _time_to_str(data.get(f"w{i}_end", "00:00")),
                CONF_COST_PER_KWH: _parse_cost(data.get(f"w{i}_{CONF_COST_PER_KWH}")),
            })
    return rows


class EnergyWindowConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Energy Window Tracker."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow."""
        self._source_entity: str | None = None
        self._pending_entry_title: str | None = None
        self._pending_sources: list[dict[str, Any]] | None = None
        self._edit_index: int = 0

    def _get_pending_source(self) -> dict[str, Any]:
        """Get the single pending source (during initial flow before entry exists)."""
        if not self._pending_sources or not isinstance(self._pending_sources[0], dict):
            raise ValueError("No pending source")
        return self._pending_sources[0]

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Step 1: energy source only."""
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
            windows = _collect_windows_from_input(user_input, num_rows=1, use_simple_keys=True)
            if not windows:
                errors["base"] = "at_least_one_window"
                return self.async_show_form(
                    step_id="windows",
                    data_schema=_build_windows_schema(
                        self.hass,
                        source_entity,
                        _get_window_rows_from_input(user_input, 1, use_simple_keys=True),
                        default_source_name=user_input.get("source_name") or _get_entity_friendly_name(self.hass, source_entity),
                        use_simple_keys=True,
                    ),
                    errors=errors,
                )
            start = _time_to_str(user_input.get("start") or "00:00")
            end = _time_to_str(user_input.get("end") or "00:00")
            if start >= end:
                errors["base"] = "window_start_after_end"
                return self.async_show_form(
                    step_id="windows",
                    data_schema=_build_windows_schema(
                        self.hass,
                        source_entity,
                        _get_window_rows_from_input(user_input, 1, use_simple_keys=True),
                        default_source_name=user_input.get("source_name") or _get_entity_friendly_name(self.hass, source_entity),
                        use_simple_keys=True,
                    ),
                    errors=errors,
                )
            source_name = (user_input.get("source_name") or "").strip() or _get_entity_friendly_name(self.hass, source_entity)
            source_name = (source_name or "Energy Window Tracker").strip()[:200]
            entry_title = source_name or "Energy Window Tracker"
            # Create entry immediately so submitted values are saved
            return self.async_create_entry(
                title=entry_title,
                data={
                    CONF_SOURCES: [
                        {
                            CONF_NAME: source_name,
                            CONF_SOURCE_ENTITY: source_entity,
                            CONF_WINDOWS: windows,
                        }
                    ]
                },
            )

        return self.async_show_form(
            step_id="windows",
            data_schema=_build_windows_schema(
                self.hass,
                source_entity,
                default_source_name=_get_entity_friendly_name(self.hass, source_entity),
                use_simple_keys=True,
            ),
            errors=errors,
        )

    async def async_step_configure_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Show Configure Energy Window Tracker menu (after first window, before Done)."""
        if user_input is not None:
            next_step = user_input.get("next_step_id")
            if next_step == "done":
                return self.async_create_entry(
                    title=self._pending_entry_title or "Energy Window Tracker",
                    data={CONF_SOURCES: self._pending_sources or []},
                )
            if next_step in ("add_window", "list_windows", "source_entity"):
                return await getattr(self, f"async_step_{next_step}")(None)
        return self._async_show_configure_menu()

    def _async_show_configure_menu(self) -> config_entries.FlowResult:
        """Show the Configure Energy Window Tracker menu (config flow)."""
        return {
            "type": data_entry_flow.FlowResultType.MENU,
            "flow_id": self.flow_id,
            "handler": self.handler,
            "step_id": "configure_menu",
            "menu_options": _build_configure_menu_options_with_done(),
            "title": "Configure Energy Window Tracker",
        }

    async def async_step_done(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Create entry and finish (from Configure menu Done)."""
        return self.async_create_entry(
            title=self._pending_entry_title or "Energy Window Tracker",
            data={CONF_SOURCES: self._pending_sources or []},
        )

    async def async_step_add_window(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Add a window (config flow, pending entry)."""
        src = self._get_pending_source()
        source_entity = str(src.get(CONF_SOURCE_ENTITY) or "")
        if user_input is not None and "start" in user_input:
            start, end = _get_start_end_from_input(user_input)
            if start >= end:
                return self.async_show_form(
                    step_id="add_window",
                    data_schema=_build_single_window_schema({
                        CONF_WINDOW_NAME: user_input.get(CONF_WINDOW_NAME, ""),
                        "start": start,
                        "end": end,
                        CONF_COST_PER_KWH: _parse_cost(user_input.get(CONF_COST_PER_KWH)),
                    }),
                    errors={"base": "window_start_after_end"},
                )
            new_window = {
                CONF_WINDOW_NAME: (user_input.get(CONF_WINDOW_NAME) or "").strip() or None,
                CONF_WINDOW_START: start,
                CONF_WINDOW_END: end,
                CONF_COST_PER_KWH: _parse_cost(user_input.get(CONF_COST_PER_KWH)),
            }
            if not self._pending_sources:
                return await self.async_step_configure_menu(None)
            self._pending_sources[0].setdefault(CONF_WINDOWS, []).append(new_window)
            return await self.async_step_configure_menu(None)
        return self.async_show_form(
            step_id="add_window",
            data_schema=_build_single_window_schema(),
        )

    async def async_step_manage_windows_empty(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """No windows yet in config flow; submit returns to Configure menu."""
        if user_input is not None:
            return await self.async_step_configure_menu(None)
        return self.async_show_form(
            step_id="manage_windows_empty",
            data_schema=vol.Schema({}),
        )

    async def async_step_list_windows(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Manage windows list (config flow, pending entry)."""
        src = self._get_pending_source()
        windows = _normalize_windows_for_schema(src.get(CONF_WINDOWS) or [])
        if not windows:
            return await self.async_step_manage_windows_empty(None)
        if user_input is not None and "window_index" in user_input:
            raw = user_input.get("window_index")
            idx = int(raw[0] if isinstance(raw, list) else raw, 10)
            self._edit_index = idx
            return await self.async_step_edit_window(None)
        return self.async_show_form(
            step_id="list_windows",
            data_schema=_build_select_window_schema(windows),
        )

    async def async_step_edit_window(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Edit one window (config flow, pending entry)."""
        src = self._get_pending_source()
        windows = _normalize_windows_for_schema(src.get(CONF_WINDOWS) or [])
        idx = self._edit_index
        if idx < 0 or idx >= len(windows):
            return await self.async_step_configure_menu(None)
        if user_input is not None:
            if user_input.get("delete_this_window"):
                windows.pop(idx)
                self._pending_sources[0][CONF_WINDOWS] = windows
                return await self.async_step_configure_menu(None)
            start, end = _get_start_end_from_input(user_input)
            if start >= end:
                return self.async_show_form(
                    step_id="edit_window",
                    data_schema=_build_single_window_schema(windows[idx], include_delete=True),
                    errors={"base": "window_start_after_end"},
                )
            windows[idx] = {
                CONF_WINDOW_NAME: (user_input.get(CONF_WINDOW_NAME) or "").strip() or None,
                CONF_WINDOW_START: start,
                CONF_WINDOW_END: end,
            }
            self._pending_sources[0][CONF_WINDOWS] = windows
            return await self.async_step_configure_menu(None)
        return self.async_show_form(
            step_id="edit_window",
            data_schema=_build_single_window_schema(windows[idx], include_delete=True),
        )

    async def async_step_source_entity(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Update energy source (config flow, pending entry)."""
        if user_input is not None and CONF_SOURCE_ENTITY in user_input:
            new_entity = user_input.get(CONF_SOURCE_ENTITY) or ""
            if new_entity and self._pending_sources:
                name = (user_input.get(CONF_NAME) or "").strip() or _get_entity_friendly_name(self.hass, new_entity)
                self._pending_sources[0][CONF_SOURCE_ENTITY] = new_entity
                self._pending_sources[0][CONF_NAME] = (name or "Energy Window Tracker").strip()[:200]
                if self._pending_entry_title:
                    self._pending_entry_title = self._pending_sources[0][CONF_NAME]
            return await self.async_step_configure_menu(None)
        src = self._get_pending_source()
        source_entity = str(src.get(CONF_SOURCE_ENTITY) or DEFAULT_SOURCE_ENTITY)
        current_name = str(src.get(CONF_NAME) or "") or _get_entity_friendly_name(self.hass, source_entity)
        return self.async_show_form(
            step_id="source_entity",
            data_schema=_build_source_entity_schema(source_entity, current_name),
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


def _build_configure_menu_options_with_done() -> dict[str, str]:
    """Same as init menu plus Done (for config flow after first window)."""
    return {
        **_build_init_menu_options(),
        "done": "Done",
    }


def _window_display_name(w: dict[str, Any], index: int) -> str:
    """Display name for a window (for list/dropdown labels)."""
    name = (w.get(CONF_WINDOW_NAME) or "").strip()
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


def _build_source_entity_schema(source_entity: str, current_source_name: str = "") -> vol.Schema:
    """Build schema for changing the source entity and optional source name."""
    return vol.Schema(
        {
            vol.Required(
                CONF_SOURCE_ENTITY,
                default=source_entity or DEFAULT_SOURCE_ENTITY,
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor")),
            vol.Optional(
                CONF_NAME,
                default=current_source_name or "",
                description="Source name",
            ): str,
        }
    )


def _get_start_end_from_input(user_input: dict[str, Any]) -> tuple[str, str]:
    """Get start and end time strings from form input (keys 'start'/'end')."""
    start = _time_to_str(user_input.get("start") or "00:00")
    end = _time_to_str(user_input.get("end") or "00:00")
    return start, end


def _build_single_window_schema(
    window: dict[str, Any] | None = None,
    include_delete: bool = False,
) -> vol.Schema:
    """Build schema for add/edit single window. include_delete=True adds 'Delete this window' (edit only)."""
    w = window or {}
    name_val = str(w.get(CONF_WINDOW_NAME, ""))[:200]
    start_val = _time_to_str(w.get(CONF_WINDOW_START) or DEFAULT_WINDOW_START)
    end_val = _time_to_str(w.get(CONF_WINDOW_END) or DEFAULT_WINDOW_END)
    cost_val = 0.0
    if CONF_COST_PER_KWH in w and w[CONF_COST_PER_KWH] is not None:
        try:
            cost_val = max(0.0, float(w[CONF_COST_PER_KWH]))
        except (TypeError, ValueError):
            pass
    schema_dict: dict[Any, Any] = {
        vol.Optional(
            CONF_WINDOW_NAME, default=name_val, description="Window name"
        ): str,
        vol.Optional("start", default=start_val, description="Start time"): selector.TimeSelector(),
        vol.Optional("end", default=end_val, description="End time"): selector.TimeSelector(),
        vol.Optional(
            CONF_COST_PER_KWH,
            default=cost_val,
            description="Cost per kWh ($)",
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=100, step=0.00001, mode="box")
        ),
    }
    if include_delete:
        schema_dict[
            vol.Optional("delete_this_window", default=False, description="❌ Delete?")
        ] = bool
    return vol.Schema(schema_dict)


class EnergyWindowOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow: Configure Energy Window Tracker — add/edit/delete windows, change source."""

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

    def _save_source(
        self,
        source_entity: str,
        windows: list[dict[str, Any]],
        source_name: str | None = None,
    ) -> None:
        """Persist source and windows to config entry."""
        if source_name is None or not source_name.strip():
            source_name = _get_entity_friendly_name(self.hass, source_entity)
        else:
            source_name = source_name.strip()[:200]
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
        """Configure Energy Window Tracker: show menu (Add new window, Manage windows, Update energy source)."""
        try:
            return await self._async_step_manage_impl(user_input)
        except Exception as err:
            _LOGGER.exception(
                "Energy Window Tracker options flow failed: %s",
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
        """Show Configure Energy Window Tracker menu."""
        src = self._get_current_source()
        source_entity = str(src.get(CONF_SOURCE_ENTITY) or DEFAULT_SOURCE_ENTITY)
        windows = _normalize_windows_for_schema(src.get(CONF_WINDOWS) or [])

        menu_options = _build_init_menu_options()
        return self._async_show_menu(
            step_id="init",
            menu_options=menu_options,
            description_placeholders={"windows_list": ""},
            title="Configure Energy Window Tracker",
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

    async def async_step_manage_windows_empty(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """No windows yet; submit returns to menu."""
        if user_input is not None:
            return await self._async_step_manage_impl(None)
        return self.async_show_form(
            step_id="manage_windows_empty",
            data_schema=vol.Schema({}),
        )

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
        window_name = (windows[idx].get(CONF_WINDOW_NAME) or "").strip() or f"Window {idx + 1}"
        if user_input is not None:
            new_windows = [w for i, w in enumerate(windows) if i != idx]
            current_name = src.get(CONF_NAME) or None
            self._save_source(source_entity, new_windows, source_name=current_name)
            # Remove the sensor entity for the deleted window (stable unique_id)
            unique_id = f"{self._config_entry.entry_id}_source_0_{idx}"
            registry = er.async_get(self.hass)
            if entity_id := registry.async_get_entity_id("sensor", DOMAIN, unique_id):
                registry.async_remove(entity_id)
            return await self._async_step_manage_windows_impl(None)
        return self.async_show_form(
            step_id="confirm_delete",
            data_schema=vol.Schema({}),
            description_placeholders={"window_name": window_name},
        )

    async def async_step_source_entity_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Confirm before changing source: historical data will be deleted."""
        if user_input is not None:
            src = self._get_current_source()
            source_entity = str(src.get(CONF_SOURCE_ENTITY) or DEFAULT_SOURCE_ENTITY)
            current_name = str(src.get(CONF_NAME) or "") or _get_entity_friendly_name(
                self.hass, source_entity
            )
            return self.async_show_form(
                step_id="source_entity",
                data_schema=_build_source_entity_schema(source_entity, current_name),
            )
        return self.async_show_form(
            step_id="source_entity_confirm",
            data_schema=vol.Schema({}),
        )

    async def async_step_source_entity(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Change the source entity (form). Asks for confirmation first."""
        src = self._get_current_source()
        source_entity = str(src.get(CONF_SOURCE_ENTITY) or DEFAULT_SOURCE_ENTITY)
        windows = _normalize_windows_for_schema(src.get(CONF_WINDOWS) or [])

        if user_input is not None and CONF_SOURCE_ENTITY in user_input:
            new_entity = user_input.get(CONF_SOURCE_ENTITY) or source_entity
            if not new_entity:
                current_name = str(src.get(CONF_NAME) or "") or _get_entity_friendly_name(
                    self.hass, source_entity
                )
                return self.async_show_form(
                    step_id="source_entity",
                    data_schema=_build_source_entity_schema(source_entity, current_name),
                )
            custom_name = (user_input.get(CONF_NAME) or "").strip()
            source_name = custom_name or _get_entity_friendly_name(self.hass, new_entity)

            # Remove all sensor entities for this config entry (old source)
            registry = er.async_get(self.hass)
            for entity_entry in registry.entities.get_entries_for_config_entry_id(
                self._config_entry.entry_id
            ):
                if entity_entry.domain == "sensor" and entity_entry.platform == DOMAIN:
                    registry.async_remove(entity_entry.entity_id)

            # Clear historical snapshot storage for the old source
            old_slug = (
                source_entity.replace(".", "_").replace(":", "_")[:64]
                if source_entity
                else "source_0"
            )
            store = Store(
                self.hass,
                STORAGE_VERSION,
                f"{STORAGE_KEY}_{self._config_entry.entry_id}_{old_slug}",
            )
            await store.async_save({})

            self._save_source(new_entity, windows, source_name=source_name)
            await self.hass.config_entries.async_reload(self._config_entry.entry_id)
            return await self._async_step_manage_impl(None)

        # First time: show confirmation step
        return self.async_show_form(
            step_id="source_entity_confirm",
            data_schema=vol.Schema({}),
        )

    async def async_step_source_entity_updated(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Show info that the previous entity was not deleted, then return to menu."""
        if user_input is not None:
            return await self._async_step_manage_impl(None)
        return self.async_show_form(
            step_id="source_entity_updated",
            data_schema=vol.Schema({}),
        )

    async def async_step_add_window(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Add a new window."""
        src = self._get_current_source()
        source_entity = str(src.get(CONF_SOURCE_ENTITY) or DEFAULT_SOURCE_ENTITY)
        windows = _normalize_windows_for_schema(src.get(CONF_WINDOWS) or [])

        if user_input is not None:
            start, end = _get_start_end_from_input(user_input)
            if start >= end:
                return self.async_show_form(
                    step_id="add_window",
                    data_schema=_build_single_window_schema(
                        {
                            CONF_WINDOW_NAME: user_input.get(CONF_WINDOW_NAME, ""),
                            "start": start,
                            "end": end,
                            CONF_COST_PER_KWH: _parse_cost(user_input.get(CONF_COST_PER_KWH)),
                        }
                    ),
                    errors={"base": "window_start_after_end"},
                )
            name = (user_input.get(CONF_WINDOW_NAME) or "").strip() or None
            new_window = {
                CONF_WINDOW_START: start,
                CONF_WINDOW_END: end,
                CONF_WINDOW_NAME: name,
                CONF_COST_PER_KWH: _parse_cost(user_input.get(CONF_COST_PER_KWH)),
            }
            windows.append(new_window)
            current_name = src.get(CONF_NAME) or None
            self._save_source(source_entity, windows, source_name=current_name)
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
            start, end = _get_start_end_from_input(user_input)
            if start >= end:
                return self.async_show_form(
                    step_id="edit_window",
                    data_schema=_build_single_window_schema(
                        {
                            CONF_WINDOW_NAME: user_input.get(CONF_WINDOW_NAME, ""),
                            "start": start,
                            "end": end,
                            CONF_COST_PER_KWH: _parse_cost(user_input.get(CONF_COST_PER_KWH)),
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
                CONF_COST_PER_KWH: _parse_cost(user_input.get(CONF_COST_PER_KWH)),
            }
            current_name = src.get(CONF_NAME) or None
            self._save_source(source_entity, windows, source_name=current_name)
            return await self._async_step_manage_windows_impl(None)

        return self.async_show_form(
            step_id="edit_window",
            data_schema=_build_single_window_schema(
                windows[edit_index], include_delete=True
            ),
        )
