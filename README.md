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

After updating the integration (via HACS or by replacing files), **restart Home Assistant** for the new version to load.

## Configuration

Each integration entry has **one energy source** and can have **many time windows**. You can create multiple entries that use the same sensor (e.g. different window sets or names).

### Initial setup

1. Go to **Settings → Devices & Services → + Add Integration**
2. Search for **Energy Window Tracker**
3. **Step 1 — Select energy source:** Choose a daily cumulative energy sensor that resets (e.g. `sensor.today_load`).
4. **Step 2 — Add window:** Optionally set an **Energy source name** (defaults to the sensor’s name). Then name the window and set start and end times. Submit opens **Configure Energy Window Tracker** (same menu as ⚙️ Configure): add more windows, manage or edit windows, update the source, or click **Done** to finish.

### ⚙️ Configure (add, edit, remove windows or change source)

1. Go to **Settings → Devices & Services**, find **Energy Window Tracker** and open the entry.
2. Click **⚙️ Configure** — the **Configure Energy Window Tracker** menu opens:
   - **✚ Add new window** — Add a window (name, start time, end time). Save returns you to the menu.
   - **✏️ Manage windows** — Choose a window from the dropdown, then **Select**. The edit form opens (name, start, end; optional **❌ Delete?**). Save or delete (with confirmation) then returns to the window list.
   - **⚡️ Update energy source** — Pick a different energy sensor and optionally set a **Source name** (defaults to the sensor’s name). Returns to the menu.

Use **Submit**, **Select**, or **Save** as appropriate when done.

## Sensor Attributes

| Attribute       | Description                                                    |
| --------------- | -------------------------------------------------------------- |
| `source_entity` | The tracked source sensor                                      |
| `start` / `end` | Window times for this sensor                                   |
| `status`        | Current mode: before_window, during_window, after_window, etc. |

## FAQ

**What kind of energy sensor do I need?**  
The source must be a **daily cumulative total** that resets (e.g. at midnight) — for example from a Shelly, Fronius, SolarEdge, or similar integration.

**What happens if Home Assistant restarts during a window?**  
The start snapshot is restored from storage, and the end snapshot is taken at the window end time. Your data is preserved.

**How many sources and windows can I have?**  
Each integration entry has **one energy source** and can have **any number of time windows**. You can create multiple entries that use the same sensor (e.g. different window sets). To add or change windows for an entry, use ⚙️ Configure on that entry.
