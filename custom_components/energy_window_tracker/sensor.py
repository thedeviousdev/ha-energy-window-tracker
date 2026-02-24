"""Sensor platform for Energy Window Tracker."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
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
    ATTR_SOURCE_ENTITY,
    ATTR_STATUS,
    CONF_NAME,
    CONF_SOURCES,
    CONF_WINDOWS,
    CONF_WINDOW_END,
    CONF_WINDOW_NAME,
    CONF_WINDOW_START,
    CONF_SOURCE_ENTITY,
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
        windows.append(
            WindowConfig(
                start_h=start_h,
                start_m=start_m,
                end_h=end_h,
                end_m=end_m,
                name=name,
                index=i,
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
        return

    hass.data.setdefault(DOMAIN, {})
    entry_data: dict[str, WindowData] = {}
    hass.data[DOMAIN][entry.entry_id] = entry_data
    all_sensors: list[WindowEnergySensor] = []

    for source_index, source_config in enumerate(sources):
        if not isinstance(source_config, dict):
            continue
        source_entity = source_config.get(CONF_SOURCE_ENTITY)
        if not source_entity:
            continue
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
        self._attr_name = f"{config_name} - {window.name}"
        # Stable unique_id by entry + source slot + window index so entity_id is preserved
        # when the user updates the energy source (same entry, same slot, same window).
        self._attr_unique_id = f"{entry_id}_source_{source_index}_{window_index}"

    async def async_added_to_hass(self) -> None:
        """Restore state and register listeners."""
        await super().async_added_to_hass()

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
        """Poll source and refresh displayed value for live updates."""
        self._update_value()
        if self.entity_id:
            self.async_write_ha_state()

    @callback
    def _handle_data_update(self) -> None:
        self._update_value()
        if self.entity_id:
            # Must run on event loop; callback can be invoked from another thread (e.g. time_change)
            self.hass.loop.call_soon_threadsafe(self.async_write_ha_state)

    def _update_value(self) -> None:
        value, status = self._data.get_window_value(self._window)
        self._attr_native_value = value
        self._attr_extra_state_attributes = {
            ATTR_SOURCE_ENTITY: self._data._source_entity,
            ATTR_STATUS: status,
            "start": _time_str(self._window.start_h, self._window.start_m),
            "end": _time_str(self._window.end_h, self._window.end_m),
        }
