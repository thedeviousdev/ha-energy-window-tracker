"""Sensor platform for Energy Window Tracker."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_change,
)
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_COST,
    ATTR_SOURCE_ENTITY,
    ATTR_STATUS,
    CONF_COST_PER_KWH,
    CONF_NAME,
    CONF_SOURCE_ENTITY,
    CONF_SOURCES,
    CONF_WINDOW_END,
    CONF_WINDOW_NAME,
    CONF_WINDOW_START,
    CONF_WINDOWS,
    DOMAIN,
    STORAGE_KEY,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class WindowConfig:
    """Configuration for a single window."""

    start_h: int
    start_m: int
    end_h: int
    end_m: int
    name: str
    index: int
    cost_per_kwh: float = 0.0


@dataclass
class WindowSnapshots:
    """Snapshot data for a single window."""

    snapshot_start: float | None
    snapshot_end: float | None


def _parse_hhmm(time_str: str) -> tuple[int, int]:
    """Parse 'HH:MM' or 'HH:MM:SS' into (hour, minute)."""
    parts = str(time_str).split(":")
    return int(parts[0]), int(parts[1])


def _time_str(h: int, m: int) -> str:
    """Format hour and minute as HH:MM."""
    return f"{h:02d}:{m:02d}"


def _parse_windows(config: dict[str, Any]) -> list[WindowConfig]:
    """Parse window config from entry data."""
    windows_data = config.get(CONF_WINDOWS) or []
    windows = []
    for i, p in enumerate(windows_data):
        start_h, start_m = _parse_hhmm(p.get(CONF_WINDOW_START) or "11:00")
        end_h, end_m = _parse_hhmm(p.get(CONF_WINDOW_END) or "14:00")
        name = p.get(CONF_WINDOW_NAME) or f"Window {i + 1}"
        cost_per_kwh = 0.0
        if CONF_COST_PER_KWH in p and p[CONF_COST_PER_KWH] is not None:
            try:
                cost_per_kwh = max(0.0, float(p[CONF_COST_PER_KWH]))
            except (TypeError, ValueError):
                pass
        windows.append(
            WindowConfig(
                start_h=start_h,
                start_m=start_m,
                end_h=end_h,
                end_m=end_m,
                name=name,
                index=i,
                cost_per_kwh=cost_per_kwh,
            )
        )
    return windows


class WindowData:
    """Shared snapshot data and time handlers for all window sensors."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        source_entity: str,
        windows: list[WindowConfig],
        store: Store,
    ) -> None:
        self.hass = hass
        self._entry_id = entry_id
        self._source_entity = source_entity
        self._windows = windows
        self._store = store
        self._snapshots: dict[int, WindowSnapshots] = {
            w.index: WindowSnapshots(snapshot_start=None, snapshot_end=None)
            for w in windows
        }
        self._snapshot_date: str | None = None
        self._update_callbacks: list[callback] = []

    def add_update_callback(self, cb: callback) -> None:
        """Register a callback to run when snapshots change."""
        self._update_callbacks.append(cb)

    def _notify_update(self) -> None:
        """Notify all sensors to update."""
        for cb in self._update_callbacks:
            cb()

    def get_source_value(self) -> float | None:
        """Get current source entity value."""
        state = self.hass.states.get(self._source_entity)
        if state is None or state.state in ("unknown", "unavailable"):
            return None
        try:
            return float(state.state)
        except (ValueError, TypeError):
            return None

    def get_window_value(self, window: WindowConfig) -> tuple[float | None, str]:
        """Get energy value and status for a window."""
        total = self.get_source_value()
        now = dt_util.now()
        current_minutes = now.hour * 60 + now.minute
        snap = self._snapshots.get(window.index)
        start_min = window.start_h * 60 + window.start_m
        end_min = window.end_h * 60 + window.end_m
        in_window = start_min <= current_minutes < end_min
        window_ended = end_min <= current_minutes

        if total is None:
            return None, "unavailable"

        if not in_window and not window_ended:
            return 0.0, "before_window"
        if in_window:
            if snap and snap.snapshot_start is not None:
                value = max(0.0, total - snap.snapshot_start)
                return round(value, 3), "during_window"
            return 0.0, "during_window (no snapshot)"
        if (
            window_ended
            and snap
            and snap.snapshot_start is not None
            and snap.snapshot_end is not None
        ):
            value = max(0.0, snap.snapshot_end - snap.snapshot_start)
            return round(value, 3), "after_window"
        if window_ended and snap and snap.snapshot_start is not None:
            return max(
                0.0, total - snap.snapshot_start
            ), "after_window (missing end snapshot)"
        return 0.0, "after_window (no snapshots)"

    def take_late_start_snapshot(self, window_index: int) -> bool:
        """If we're during the window with no start snapshot, use current value as start (e.g. missed event)."""
        value = self.get_source_value()
        if value is None:
            return False
        snap = self._snapshots.get(window_index) or WindowSnapshots(None, None)
        if snap.snapshot_start is not None:
            return False
        now = dt_util.now()
        current_minutes = now.hour * 60 + now.minute
        for w in self._windows:
            if w.index != window_index:
                continue
            start_min = w.start_h * 60 + w.start_m
            end_min = w.end_h * 60 + w.end_m
            if not (start_min <= current_minutes < end_min):
                return False
            if not self._snapshot_date:
                self._snapshot_date = now.date().isoformat()
            self._snapshots[window_index] = WindowSnapshots(
                snapshot_start=value,
                snapshot_end=None,
            )
            self._schedule_save()
            return True
        return False

    async def load(self) -> None:
        """Load snapshots from storage."""
        stored = await self._store.async_load()
        if stored:
            self._snapshot_date = stored.get("snapshot_date")
            snapshots_data = stored.get("windows") or {}
            for w in self._windows:
                if str(w.index) in snapshots_data:
                    sd = snapshots_data[str(w.index)]
                    self._snapshots[w.index] = WindowSnapshots(
                        snapshot_start=sd.get("snapshot_start"),
                        snapshot_end=sd.get("snapshot_end"),
                    )

    async def save(self) -> None:
        """Persist snapshots to storage."""
        snapshots_data = {
            str(idx): {
                "snapshot_start": s.snapshot_start,
                "snapshot_end": s.snapshot_end,
            }
            for idx, s in self._snapshots.items()
        }
        await self._store.async_save(
            {"windows": snapshots_data, "snapshot_date": self._snapshot_date}
        )

    def _handle_window_start(self, window: WindowConfig, now: datetime) -> None:
        """Snapshot at window start."""
        today = dt_util.now().date().isoformat()
        self._snapshot_date = today
        value = self.get_source_value()
        if value is not None:
            self._snapshots[window.index] = WindowSnapshots(
                snapshot_start=value,
                snapshot_end=None,
            )
            _LOGGER.debug("Window '%s' start: %.3f kWh", window.name, value)
            self._schedule_save()
        self._notify_update()

    def _handle_window_end(self, window: WindowConfig, now: datetime) -> None:
        """Snapshot at window end."""
        value = self.get_source_value()
        if value is not None:
            snap = self._snapshots.get(window.index) or WindowSnapshots(None, None)
            self._snapshots[window.index] = WindowSnapshots(
                snapshot_start=snap.snapshot_start,
                snapshot_end=value,
            )
            _LOGGER.debug("Window '%s' end: %.3f kWh", window.name, value)
            self._schedule_save()
        self._notify_update()

    def _handle_midnight(self, now: datetime) -> None:
        """Reset snapshots at midnight."""
        self._snapshots = {
            w.index: WindowSnapshots(snapshot_start=None, snapshot_end=None)
            for w in self._windows
        }
        self._snapshot_date = dt_util.now().date().isoformat()
        self._schedule_save()
        self._notify_update()

    def _schedule_save(self) -> None:
        """Schedule save() on the event loop (time handlers may run from a thread)."""
        self.hass.loop.call_soon_threadsafe(
            lambda: self.hass.async_create_task(self.save())
        )


def _source_slug(source_entity: str, source_index: int) -> str:
    """Stable key for a source (storage and unique_id)."""
    if source_entity:
        return source_entity.replace(".", "_").replace(":", "_")[:64]
    return f"source_{source_index}"


def _get_sources_from_config(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the single source from config (one entry = one source)."""
    raw = config.get(CONF_SOURCES)
    if isinstance(raw, list) and raw:
        return [raw[0]]  # Only first source; one entry = one source
    return []


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform (one or more sources under this entry)."""
    config = {**entry.data, **entry.options}
    sources = _get_sources_from_config(config)
    if not sources:
        _LOGGER.debug("async_setup_entry: no sources in config")
        return

    hass.data.setdefault(DOMAIN, {})
    entry_data: dict[str, WindowData] = {}
    hass.data[DOMAIN][entry.entry_id] = entry_data
    all_sensors: list[WindowEnergySensor] = []

    for source_index, source_config in enumerate(sources):
        if not isinstance(source_config, dict):
            _LOGGER.warning("async_setup_entry: source %s is not a dict", source_index)
            continue
        source_entity = source_config.get(CONF_SOURCE_ENTITY)
        if not source_entity:
            _LOGGER.warning("async_setup_entry: source %s has no source_entity", source_index)
            continue
        if not isinstance(source_entity, str):
            _LOGGER.warning(
                "async_setup_entry: source %s source_entity type=%s, coercing to str",
                source_index,
                type(source_entity).__name__,
            )
            source_entity = source_entity[0] if isinstance(source_entity, list) and source_entity else str(source_entity)
        source_name = source_config.get(CONF_NAME) or "Window"
        windows = _parse_windows(source_config)
        if not windows:
            continue

        slug = _source_slug(source_entity, source_index)
        store = Store(
            hass,
            STORAGE_VERSION,
            f"{STORAGE_KEY}_{entry.entry_id}_{slug}",
        )
        data = WindowData(
            hass=hass,
            entry_id=entry.entry_id,
            source_entity=source_entity,
            windows=windows,
            store=store,
        )
        await data.load()
        entry_data[slug] = data

        for i, window in enumerate(windows):
            sensor = WindowEnergySensor(
                hass=hass,
                entry_id=entry.entry_id,
                config_name=source_name,
                window=window,
                data=data,
                windows=windows,
                is_first=(i == 0),
                source_slug=slug,
                source_index=source_index,
                window_index=i,
            )
            all_sensors.append(sensor)

    # Remove entities for windows that no longer exist (e.g. after user deleted a window)
    current_unique_ids = {sensor.unique_id for sensor in all_sensors}
    registry = er.async_get(hass)
    for entity_entry in registry.entities.get_entries_for_config_entry_id(
        entry.entry_id
    ):
        if (
            entity_entry.domain == "sensor"
            and entity_entry.unique_id not in current_unique_ids
        ):
            _LOGGER.debug(
                "Removing orphaned sensor entity %s (unique_id: %s)",
                entity_entry.entity_id,
                entity_entry.unique_id,
            )
            registry.async_remove(entity_entry.entity_id)

    _LOGGER.info(
        "async_setup_entry: entry_id=%s, added %s sensor(s)",
        entry.entry_id,
        len(all_sensors),
    )
    async_add_entities(all_sensors, update_before_add=True)


class WindowEnergySensor(RestoreSensor):
    """Sensor that shows energy consumed during a specific time window."""

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_icon = "mdi:clock-outline"
    _attr_should_poll = True
    _attr_scan_interval = timedelta(seconds=30)

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        config_name: str,
        window: WindowConfig,
        data: WindowData,
        windows: list[WindowConfig],
        is_first: bool = False,
        source_slug: str | None = None,
        source_index: int = 0,
        window_index: int = 0,
    ) -> None:
        self.hass = hass
        self._entry_id = entry_id
        self._window = window
        self._data = data
        self._windows = windows
        self._is_first = is_first
        # Name used at registration so entity_id includes source (e.g. sensor.sensor_today_load_peak).
        # Friendly name is set to window name only in async_added_to_hass.
        self._attr_name = f"{source_slug} {window.name}" if source_slug else window.name
        # Stable unique_id by entry + source slot + window index so entity_id is preserved
        # when the user updates the energy source (same entry, same slot, same window).
        self._attr_unique_id = f"{entry_id}_source_{source_index}_{window_index}"
        self._last_source_value: float | None = None
        self._last_status: str | None = None

    async def async_added_to_hass(self) -> None:
        """Restore state and register listeners."""
        await super().async_added_to_hass()

        # Friendly name is window name only (entity_id already includes source from __init__ name).
        self._attr_name = self._window.name

        if (last := await self.async_get_last_sensor_data()) is not None:
            self._attr_native_value = last.native_value

        self._data.add_update_callback(self._handle_data_update)

        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self._data._source_entity],
                lambda e: self._handle_data_update(),
            )
        )

        if self._is_first:
            unsubs = []
            for w in self._windows:
                unsubs.append(
                    async_track_time_change(
                        self.hass,
                        lambda t, window=w: self._data._handle_window_start(window, t),
                        hour=w.start_h,
                        minute=w.start_m,
                        second=0,
                    )
                )
                unsubs.append(
                    async_track_time_change(
                        self.hass,
                        lambda t, window=w: self._data._handle_window_end(window, t),
                        hour=w.end_h,
                        minute=w.end_m,
                        second=0,
                    )
                )
            unsubs.append(
                async_track_time_change(
                    self.hass,
                    self._data._handle_midnight,
                    hour=0,
                    minute=0,
                    second=2,
                )
            )
            for unsub in unsubs:
                self.async_on_remove(unsub)

        self._update_value()
        if self.entity_id:
            self.async_write_ha_state()

    async def async_update(self) -> None:
        """Poll source and refresh displayed value; write only if value or status changed."""
        old_value = self._attr_native_value
        old_status = self._last_status
        self._update_value()
        if self.entity_id and (old_value != self._attr_native_value or old_status != self._last_status):
            self.async_write_ha_state()

    @callback
    def _handle_data_update(self) -> None:
        """Update value when source entity state or snapshot data changes; write only if value/status changed."""
        old_value = self._attr_native_value
        old_status = self._last_status
        self._update_value()
        if self.entity_id and (old_value != self._attr_native_value or old_status != self._last_status):
            # Must run on event loop; callback can be invoked from another thread (e.g. time_change)
            self.hass.add_job(self.async_write_ha_state)

    def _update_value(self) -> None:
        value, status = self._data.get_window_value(self._window)
        if status == "during_window (no snapshot)":
            if self._data.take_late_start_snapshot(self._window.index):
                value, status = self._data.get_window_value(self._window)
        self._attr_native_value = value
        attrs: dict[str, Any] = {
            ATTR_SOURCE_ENTITY: self._data._source_entity,
            ATTR_STATUS: status,
            "start": _time_str(self._window.start_h, self._window.start_m),
            "end": _time_str(self._window.end_h, self._window.end_m),
        }
        if self._window.cost_per_kwh > 0 and value is not None:
            try:
                cost = round(float(value) * self._window.cost_per_kwh, 2)
                attrs[ATTR_COST] = cost
            except (TypeError, ValueError):
                pass
        self._attr_extra_state_attributes = attrs
        self._last_source_value = self._data.get_source_value()
        self._last_status = status

