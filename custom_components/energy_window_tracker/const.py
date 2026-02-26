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

# Translation keys for config.defaults (entry_title, window_name, window_fallback)
DEFAULT_ENTRY_TITLE_KEY = "config.defaults.entry_title"
DEFAULT_NAME_KEY = "config.defaults.window_name"
DEFAULT_WINDOW_FALLBACK_KEY = "config.defaults.window_fallback"
# Translation keys for dynamic window row labels (config.step.windows.row_templates.*)
ROW_TEMPLATE_NAME_KEY = "step.windows.row_templates.name"
ROW_TEMPLATE_START_KEY = "step.windows.row_templates.start"
ROW_TEMPLATE_END_KEY = "step.windows.row_templates.end"
ROW_TEMPLATE_COST_KEY = "step.windows.row_templates.cost_per_kwh"
DEFAULT_SOURCE_ENTITY = "sensor.today_load"
DEFAULT_WINDOW_START = "11:00"
DEFAULT_WINDOW_END = "14:00"

STORAGE_VERSION = 1
STORAGE_KEY = "energy_window_tracker_snapshots"

ATTR_SOURCE_ENTITY = "source_entity"
ATTR_STATUS = "status"
ATTR_COST = "cost"
