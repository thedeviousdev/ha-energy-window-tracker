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

## Configuration

1. Go to **Settings → Devices & Services → + Add Integration**
2. Search for **Energy Window Tracker**
3. Fill in the single form and submit:
   - **Sensor name** — Defaults to the energy sensor’s name if left empty
   - **Energy sensor** — Your daily cumulative kWh sensor (e.g. `sensor.today_energy_import`)
   - **Window name** — Label for this window (e.g. Morning peak)
   - **Start time** and **End time** — When this window starts and ends

Each entry creates one sensor. Add the integration again for each extra window you want.

---

## Updating after setup

To change the sensor name, window name, or times for an entry:

1. Go to **Settings → Devices & Services**
2. Find **Energy Window Tracker** and click the relevant device/entry
3. Click **CONFIGURE**
4. Edit the fields and submit.

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
