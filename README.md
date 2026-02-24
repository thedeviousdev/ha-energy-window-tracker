# Energy Window Tracker

A Home Assistant custom integration that tracks energy consumed **during** specific time windows. Each window gets its own sensor showing energy used in that window.

---

## How It Works

| Time period    | Sensor behaviour                                |
| ---            | ---                                             |
| Before window  | Value is 0 kWh                                  |
| During window  | Tracks energy consumed so far (live)             |
| After window   | Shows final energy used during that window       |

Snapshots are taken at the **start** and **end** of each window and persisted to HA storage, so sensors survive restarts.

---

## Installation

### HACS (recommended)
1. Open HACS → Integrations → ⋮ → Custom repositories
2. Add this repo URL, category **Integration**
3. Install **Energy Window Tracker**
4. Restart Home Assistant

### Manual
1. Copy the `custom_components/energy_offpeak/` folder into your HA `config/custom_components/` directory
2. Restart Home Assistant

---

## Updating

After updating the integration (via HACS or by replacing files), **you need to restart Home Assistant manually** for the new version to load.

---

## Configuration

There is **one integration entry** for Energy Window Tracker. Each entry has **one energy source** (sensor) but can have **many time windows**.

1. Go to **Settings → Devices & Services → + Add Integration**
2. Search for **Energy Window Tracker**
3. **Step 1** — Select your **energy sensor** (daily cumulative kWh, e.g. `sensor.today_energy_import`). Submit.
4. **Step 2** — Add **one window** (name, start time, end time). Submit.

You now have one source with one window. Use **CONFIGURE** to add more windows or change the sensor.

---

## Configure Windows (Configure)

To edit the source sensor or add, edit, or remove windows:

1. Go to **Settings → Devices & Services**
2. Find **Energy Window Tracker** and click the entry
3. Click **CONFIGURE** — the **Configure Windows** dialog opens with three options. Changes are saved as you go; close the dialog with **Back** when you’re done.
4. Main menu options:
   - **Add new window** — Opens the form to add a new window (name, start time, end time). After saving you return to the main menu.
   - **Manage windows** — Opens a second screen where each window is shown as a **header** (its name), with **Edit** and **Delete** under it. Click **Edit** to change that window; click **Delete** to remove it (you’ll be asked to confirm). After editing or deleting you return to this screen. If you have no windows yet, a message is shown and you can go back and use **Add new window**.
   - **Change source entity** — Opens a form to pick a different energy sensor, then returns you to the main menu.

---

## Sensor Attributes

| Attribute        | Description                                                       |
| ---              | ---                                                                |
| source_entity    | The tracked source sensor                                          |
| start / end      | Window times for this sensor                                       |
| status           | Current mode: before_window, during_window, after_window, etc.     |

---

## Notes

- The source sensor **must** be a daily cumulative total that resets at midnight (e.g. from a Shelly, Fronius, SolarEdge, or similar device)
- If HA restarts during a window, the start snapshot is restored from storage and the end snapshot will be captured at the window end time
- One entry = one energy source; each source can have many time windows
