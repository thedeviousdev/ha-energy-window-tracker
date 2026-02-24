# Energy Tracker

A Home Assistant custom integration that tracks energy consumed **during** specific time windows. Each window has its own sensor showing energy used in that window.

---

## How It Works

| Time period   | Sensor behaviour                           |
| ------------- | ------------------------------------------ |
| Before window | Value is 0 kWh                             |
| During window | Tracks energy consumed so far (live)       |
| After window  | Shows final energy used during that window |

Snapshots are taken at the **start** and **end** of each window and persisted to HA storage, so sensors survive restarts.

---

## Installation

### HACS (recommended)

1. Open HACS → Integrations → ⋮ → Custom repositories
2. Add this repo URL, category **Integration**
3. Install **Energy Tracker**
4. Restart Home Assistant

### Manual

1. Copy the `custom_components/energy_offpeak/` folder into your HA `config/custom_components/` directory
2. Restart Home Assistant

---

## Updating

After updating the integration (via HACS or by replacing files), **restart Home Assistant** for the new version to load.

---

## Icon showing as "icon not available"

The UI loads the integration icon from **https://brands.home-assistant.io**. To fix "icon not available", the icon must be added to the [Home Assistant brands repository](https://github.com/home-assistant/brands). Use the files in the **`brands/energy_offpeak/`** folder in this repo and follow the steps in **`brands/README.md`** to open a PR there. Once merged, the icon will appear everywhere.

---

## Configuration

Each integration entry has **one energy source** and can have **many time windows**.

> **No duplicate sensors.** You cannot have two Energy Tracker entries that use the same energy sensor. Each sensor can only be linked to one entry. To add more windows for that sensor, use **⚙️ CONFIGURE** on its entry.

### Initial setup

1. Go to **Settings → Devices & Services → + Add Integration**
2. Search for **Energy Tracker**
3. **Step 1 — Select energy source:** Choose a daily cumulative energy sensor that resets (e.g. `sensor.today_energy_import`). If that sensor is already used by another entry, setup will show an error — edit the existing entry instead.
4. **Step 2 — First window:** Name the window and set start and end times. Add more windows or change settings later via **⚙️ CONFIGURE**.

### ⚙️ CONFIGURE (add, edit, remove windows or change source)

1. Go to **Settings → Devices & Services**, find **Energy Tracker** and open the entry.
2. Click **⚙️ CONFIGURE** — the **Configure Energy Tracker** menu opens:
   - **✚ Add new window** — Add a window (name, start time, end time). Save returns you to the menu.
   - **✏️ Manage windows** — Choose a window from the dropdown, then **Select**. The edit form opens (name, start, end; optional **❌ Delete?**). Save or delete (with confirmation) then returns to the window list.
   - **⚡️ Update energy source** — Pick a different energy sensor, then returns to the menu.

Close the dialog with **×** when done.

---

## Sensor Attributes

| Attribute     | Description                                                    |
| ------------- | -------------------------------------------------------------- |
| source_entity | The tracked source sensor                                      |
| start / end   | Window times for this sensor                                   |
| status        | Current mode: before_window, during_window, after_window, etc. |

---

## FAQ

**What kind of energy sensor do I need?**  
The source must be a **daily cumulative total** that resets (e.g. at midnight) — for example from a Shelly, Fronius, SolarEdge, or similar integration.

**What happens if Home Assistant restarts during a window?**  
The start snapshot is restored from storage, and the end snapshot is taken at the window end time. Your data is preserved.

**How many sources and windows can I have?**  
Each integration entry has **one energy source** and can have **any number of time windows**. **You cannot use the same sensor in more than one entry** — there are no duplicate entries per sensor. To add or change windows for a sensor, use ⚙️ CONFIGURE on that entry.
