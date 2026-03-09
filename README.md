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
   - Each range is shown as **Time range #1**, **Time range #2**, … with **Start time** and **End time** under it. Use **Add another time range** to add more, then submit to save.
   - All ranges with the same name are combined into one sensor (e.g. Off-peak 00:00–07:00 and 23:00–23:59).
   - Windows are **same-day only** (start &lt; end). For “end of day” use e.g. 23:00–23:59.
   - You can add more named windows later via **⚙️ Configure**.

**Configure menu (⚙️ on the entry):**

- **✚ Add new window** — One window name, one cost per kWh, then **Time range #1** (Start time / End time). Use **Add another time range** for more; submit to save. New windows appear under the entry’s entities right away.
- **✏️ Manage windows** — One option per **unique window name** (not per range). Choosing a name opens the edit form for **all** ranges with that name; you can change times, add/remove ranges with **Add another time range**, or **Delete** that window. Saving **replaces** every range for that name with the new set. Changes apply immediately.
- **⚡️ Update energy source** — New sensor + optional friendly name. Checkbox: remove old entities and data or keep them and clean up manually. Changing the source will create new entity IDs. 

## Sensors

Each **window name** is one sensor (all time ranges with that name are summed). Friendly name = window name. Entity ID includes the source (e.g. `sensor.today_load_peak`). Find them under the entry’s **Entities** tab or **Settings → Entities** filtered by the integration.

| Attribute       | Meaning |
| --------------- | ------- |
| `source_entity` | Source sensor |
| `ranges`        | List of `{start, end}` for this window (e.g. `[{"start": "00:00", "end": "07:00"}, {"start": "23:00", "end": "23:59"}]`) |
| `start` / `end` | First range’s times (for backward compatibility) |
| `status`        | before_window, during_window, after_window, etc. |
| `cost`          | Energy × cost per kWh (if set), 2 decimals. Use e.g. `{{ state_attr('sensor.x', 'cost') }}` |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for tests and CI.

## FAQ

**What kind of energy sensor do I need?**  
The source must be a **daily cumulative total** that resets (e.g. at midnight).

**What happens if Home Assistant restarts during a window?**  
The start snapshot is restored from storage, and the end snapshot is taken at the window end time. Your data is preserved.

**How many sources and windows can I have?**  
Each integration entry has **one energy source** and can have **any number of time windows**. You can create multiple entries but they cannot use the same sensor.

**How do I get more detail when something fails?**  
When the integration loads you should see a **WARNING** line in the log: `[energy_window_tracker] Integration loaded entry_id=...`. If you only see that line and no other messages from the integration:

1. **Add the loggers** to your `configuration.yaml` and restart Home Assistant:

```yaml
logger:
  logs:
    custom_components.energy_window_tracker: debug
    custom_components.energy_window_tracker.config_flow: debug
```

The first line enables the main integration logger (setup, options form submissions). The second enables the config/options flow logger so you see step-by-step messages when adding a new entry or using Configure.

2. **Show this integration’s logs in the log viewer:** open **Settings → System → Logs**. The log viewer often shows only “Home Assistant core” by default. Use the **search** box and type `energy_window_tracker`, or clear the integration filter, so messages from this integration are visible.

For even more detail (step entry/exit, config reads), use **trace** by setting the level to `5`:

```yaml
logger:
  logs:
    custom_components.energy_window_tracker: 5
```
