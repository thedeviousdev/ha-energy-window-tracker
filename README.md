# Energy Window Tracker

Tracks energy over custom time windows in Home Assistant. Snapshots at window start and end are stored so sensors survive restarts.

| When           | Sensor value                    |
| -------------- | ------------------------------- |
| Before window  | 0 kWh                           |
| During window  | Energy so far (live)            |
| After window   | Final energy for that window   |

## Installation

### HACS (recommended)

1. Open HACS → Integrations → ⋮ → Custom repositories
2. Add this repo URL, category **Integration**
3. Install **Energy Window Tracker**
4. Restart Home Assistant

### Manual

1. Copy the `custom_components/energy_window_tracker/` folder into your HA `config/custom_components/` directory
2. Restart Home Assistant

After any update, restart HA. Some versions of the plugin have been [yanked](YANKED.md).

## Setup

One entry = one energy source + many windows. You can add multiple entries (e.g. same sensor, different window sets).

1. **Settings → Devices & Services → Add Integration** → Energy Window Tracker
2. **Step 1:** Pick a daily cumulative sensor that resets (e.g. at midnight)
3. **Step 2:** One **Window name**, one **Cost per kWh**, and one or more time ranges:
   - Each range is shown as **Range #1**, **Range #2**, … with **Start time** and **End time**. Use **Add another time range** to add more, then submit to save.
   - All ranges with the same name are combined into one sensor (e.g. Off-peak 00:00–07:00 and 23:00–23:59).
   - Windows are **same-day only** (start &lt; end). For “end of day” use e.g. 23:00–23:59.
   - **Add ranges in chronological order (earliest first).** Each range’s start time must be at or after the previous range’s end time—no overlapping. For example: 00:00–07:00, then 07:00–10:00, then 23:00–23:59 is valid; 00:00–12:00 then 10:00–14:00 is invalid (overlap).
   - You can add more named windows later via **⚙️ Configure**.

**Configure menu (⚙️ on the entry):**

- **✚ Add new window** — One window name, one cost per kWh, then **Range #1** (Start time / End time). Use **Add another time range** for more; submit to save. Add ranges in chronological order (earliest first); no overlapping. New windows appear under the entry’s entities right away.
- **✏️ Manage windows** — One option per **unique window name** (not per range). Choosing a name opens the edit form for **all** ranges with that name; you can change times, add/remove ranges with **Add another time range**, or **Delete** that window. Saving **replaces** every range for that name with the new set. Changes apply immediately.
- **⚡️ Update energy source** — New sensor + optional friendly name. Checkbox: remove old entities and data or keep them and clean up manually. Changing the source will create new entity IDs. 

## Sensors

Each **window name** is one sensor (all time ranges with that name are summed). Friendly name = window name. Entity ID includes the source (e.g. `sensor.today_load_peak`). Find them under the entry’s **Entities** tab or **Settings → Entities** filtered by the integration.

| Attribute       | Meaning |
| --------------- | ------- |
| `source_entity` | Source sensor |
| `ranges`        | List of `{start, end}` for this window (e.g. `[{"start": "00:00", "end": "07:00"}, {"start": "23:00", "end": "23:59"}]`) |
| `status`        | before_window, during_window, after_window, etc. |
| `cost`          | Energy × cost per kWh (if set), 2 decimals. Use e.g. `{{ state_attr('sensor.x', 'cost') }}` |

## Form labels (translations)

The text next to each field in the config/options flow (e.g. **Range #1 - Start time**, **Window name**) comes from:

- **strings.json** and **translations/en.json** under `config.step.<step_id>.data` and `options.step.<step_id>.data`. Each step that has the window form (windows, add_window, edit_window) has entries only for the building blocks: `window_name`, `cost_per_kwh`, `time_range_n` ("Range #{n}"), `start_suffix`, `end_suffix`, `add_another`, and for edit_window `delete_this_window`. There are no per-field keys for `start`, `end`, or `start_1`…`end_9`.
- **Python** in `config_flow.py`: `_get_window_form_labels()` loads those strings and builds labels like "Range #2 - Start time" for each range slot; those are passed as the schema field `description`, which the UI uses as the label. All range labels are dynamic (built from `time_range_n` and the suffixes).

To change the "Range #N" wording, edit `time_range_n` in the JSON files (and the fallback in `_get_window_form_labels()`).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for tests and CI.

## FAQ

**What kind of energy sensor do I need?**  
The source must be a **daily cumulative total** that resets (e.g. at midnight).

**What happens if Home Assistant restarts during a window?**  
The start snapshot is restored from storage, and the end snapshot is taken at the window end time. Your data is preserved.

**How many sources and windows can I have?**  
Each integration entry has **one energy source** and can have **any number of time windows**. You can create multiple entries but they cannot use the same sensor.

**Why do I get “Each range must start at or after the previous range’s end time”?**  
Ranges must be added in **chronological order** (earliest first) and cannot overlap. For example, 07:00–10:00 then 10:00–14:00 is valid; 07:00–12:00 then 10:00–14:00 is invalid because 10:00 is before 12:00.

**How do I get more detail when something fails?**  
When the integration loads or unloads you’ll see a **WARNING** in the log: `[energy_window_tracker] Integration loaded entry_id=...` (or `Entry removed/unloading...`). All integration messages are at **WARNING** level so they show with the default logger. To see them, add (optional if your default is already warning or lower):

```yaml
logger:
  logs:
    custom_components.energy_window_tracker: warning
```

This single logger covers setup, config flow, options flow, and sensor updates.

2. **Show this integration’s logs in the log viewer:** open **Settings → System → Logs**. The log viewer often shows only “Home Assistant core” by default. Use the **search** box and type `energy_window_tracker`, or clear the integration filter, so messages from this integration are visible.
