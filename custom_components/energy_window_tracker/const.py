"""Constants for the Energy Window Tracker integration."""

DOMAIN = "energy_window_tracker"

CONF_SOURCE_ENTITY = "source_entity"
CONF_SOURCES = "sources"
CONF_NAME = "name"
CONF_WINDOWS = "windows"
CONF_WINDOW_START = "start"
CONF_WINDOW_END = "end"
CONF_WINDOW_NAME = "name"
CONF_COST_PER_KWH = "cost_per_kwh"

DEFAULT_NAME = "Window"
DEFAULT_SOURCE_ENTITY = "sensor.today_load"
DEFAULT_WINDOW_START = "11:00"
DEFAULT_WINDOW_END = "14:00"

STORAGE_VERSION = 1
STORAGE_KEY = "energy_window_tracker_snapshots"

ATTR_SOURCE_ENTITY = "source_entity"
ATTR_STATUS = "status"
ATTR_COST = "cost"
