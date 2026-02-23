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

1. Go to **Settings → Devices & Services → + Add Integration**
2. Search for **Energy Window Tracker**
3. **Step 1** — Enter **sensor name** (optional; defaults to the energy sensor’s name) and select your **energy sensor** (daily cumulative kWh, e.g. `sensor.today_energy_import`). Submit.
4. **Step 2** — Set **source name** and add **one window**: window name, start time, end time. Submit.

Each entry starts with one window and one sensor. Add more windows later via CONFIGURE. You can also add the integration again for another energy sensor or grouping.

---

## Updating after setup

To change the source name or add/remove windows:

1. Go to **Settings → Devices & Services**
2. Find **Energy Window Tracker** and click the relevant device/entry
3. Click **CONFIGURE**
4. The form shows the source name and all current windows plus one empty row. To **add** a window: fill the new row with a name and a time range (start before end). To **remove** a window: set its start time equal to end time (e.g. 00:00–00:00) or leave that row empty. Submit; the integration reloads automatically.

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
- You can configure multiple instances for different sensors or window sets
