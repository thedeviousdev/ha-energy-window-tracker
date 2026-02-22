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
3. **Step 1** — Enter:
   - **Sensor name prefix** — e.g. `Energy Import` (each sensor will be `Energy Import - Window Name`)
   - **Source energy sensor** — your daily cumulative kWh sensor (e.g. `sensor.today_energy_import`)
4. **Step 2** — Add one or more windows:
   - **Window start time** — e.g. `11:00`
   - **Window end time** — e.g. `14:00`
   - **Window name (optional)** — e.g. `Morning Peak` (defaults to Window 1, Window 2, etc.)
   - Check **Add another window** to add more, then click **Submit**
5. Click **Submit** when done adding windows

Each window creates a separate sensor (e.g. `Energy Import - Morning Peak`). Windows may overlap.

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
