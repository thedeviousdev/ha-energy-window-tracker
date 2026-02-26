# Energy Window Tracker

Custom integration for Home Assistant that allows tracking custom windows of energy.

## How It Works

Snapshots of the current energy consumption are taken at the **start** and **end** of each window and persisted to HA storage, so sensors survive restarts.

| Time period   | Sensor behaviour                           |
| ------------- | ------------------------------------------ |
| Before window | Value is 0 kWh                             |
| During window | Tracks energy consumed so far (live)       |
| After window  | Shows final energy used during that window |

## Installation

### HACS (recommended)

1. Open HACS → Integrations → ⋮ → Custom repositories
2. Add this repo URL, category **Integration**
3. Install **Energy Window Tracker**
4. Restart Home Assistant

### Manual

1. Copy the `custom_components/energy_window_tracker/` folder into your HA `config/custom_components/` directory
2. Restart Home Assistant

## Updating

After updating the integration (via HACS or by replacing files), **restart Home Assistant** for the new version to load. Some older versions are [yanked](YANKED.md).

## Configuration

Each integration entry has **one energy source** and can have **many time windows**. You can create multiple entries that use the same sensor (e.g. different window sets or names).

### Initial setup

1. Go to **Settings → Devices & Services → + Add Integration**
2. Search for **Energy Window Tracker**
3. **Step 1 — Select sensor:** Choose a daily cumulative energy sensor that resets (e.g. `sensor.today_load`). You must select a sensor to continue.
4. **Step 2 — Add window:** Optionally set a **Friendly name** for the energy source (defaults to the sensor’s name). Enter a **Window name** and set **Start time** and **End time**. Optionally set **Cost per kWh ($)** (e.g. `0.15`, up to 3 decimal places) to track cost for this window. **Submit** creates the entry; add more windows or change settings later via **⚙️ Configure** on the entry.

### ⚙️ Configure (add, edit, remove windows or change source)

1. Go to **Settings → Devices & Services**, find **Energy Window Tracker** and open the entry.
2. Click **⚙️ Configure** — the **Configure Energy Window Tracker** menu opens:
   - **✚ Add new window** — Add a window (name, start time, end time, optional **Cost per kWh ($)**). Save returns you to the menu.
   - **✏️ Manage windows** — Choose a window from the list, then click **Select**. The edit form opens (name, start, end, optional **Cost per kWh ($)**; optional **❌ Delete?**). Save or delete (with confirmation) then returns to the window list.
   - **⚡️ Update energy source** — Opens a form to pick a new sensor and optional **Friendly name**. A checkbox **"Remove the previous associated entries? Otherwise you will need to manually delete these later."** (value **❌ Yes**) controls what happens to the old sensor entities: if checked, they are removed and old snapshot data is cleared; if unchecked, they are kept and you can delete them manually later. Entity IDs are based on the current source (e.g. `sensor.sensor_today_import_peak` after switching to `sensor.today_import`), so changing the source creates new entities with new IDs. **Update** applies the change and returns to the menu.

Use **Submit**, **Select**, **Save**, or **Update** as appropriate when done.

## Sensors

Each window is exposed as a sensor. The **friendly name** is the window name (e.g. "Peak"). Entity IDs include the current energy source (e.g. `sensor.sensor_today_load_peak` or `sensor.sensor_today_import_peak`), so if you change the source via **⚡️ Update energy source**, new entities are created with new IDs. To find entity IDs: open **Settings → Devices & Services → Energy Window Tracker**, then open your device/entry and use the **Entities** tab; or go to **Settings → Devices & Services → Entities** and filter by the integration.

| Attribute       | Description                                                                 |
| --------------- | --------------------------------------------------------------------------- |
| `source_entity` | The tracked source sensor                                                   |
| `start` / `end` | Window times for this sensor                                                |
| `status`        | Current mode: before_window, during_window, after_window, etc.              |
| `cost`          | Cost so far in $ (only present if **Cost per kWh ($)** is set for the window). Equals energy (kWh) × cost per kWh, rounded to 2 decimal places. |

Use the cost in templates or dashboards, e.g. `{{ state_attr('sensor.your_window_entity_id', 'cost') }}`.

## Contributing

To run tests, lint, and set up the GitHub Actions pipeline, see **[CONTRIBUTING.md](CONTRIBUTING.md)**.

## FAQ

**What kind of energy sensor do I need?**  
The source must be a **daily cumulative total** that resets (e.g. at midnight) — for example from a Shelly, Fronius, SolarEdge, or similar integration.

**What happens if Home Assistant restarts during a window?**  
The start snapshot is restored from storage, and the end snapshot is taken at the window end time. Your data is preserved.

**How many sources and windows can I have?**  
Each integration entry has **one energy source** and can have **any number of time windows**. You can create multiple entries that use the same sensor (e.g. different window sets). To add or change windows for an entry, use **⚙️ Configure** on that entry.

**I get "Unknown error" or 400 when adding the integration or when updating the energy source.**  
When adding: ensure you select a sensor in Step 1. Restart Home Assistant and try again. If it still fails, enable debug logging (see below) and check the log for the exact error and traceback.

**How do I get more detail when something fails?**  
Enable debug logging: **Settings → System → Logging** → set **Logger** to `custom_components.energy_window_tracker` and **Level** to **Debug**, then reproduce the issue. In **Settings → System → Logs** (or your log file), look for entries from `custom_components.energy_window_tracker`; the config flow logs step transitions and entity selector values to help trace errors.
