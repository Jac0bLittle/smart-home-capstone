# Solar tracker subsystem: overview

*Smart Home Model capstone · as of Nov 19, 2026 · owners: Jacob L., Gage (charter)*

## 1. What it does

A small dual-axis tracker on the model's roof points a 6 V mini panel at the brightest light. Four photoresistors (LDRs) behind a cross-shaped shade tell the ESP32 which way the light is, and two MG90S servos turn the panel (pan = left/right, tilt = up/down). A second, identical panel stays fixed. Two INA219 sensors measure both panels, so the dashboard can show how much more energy tracking collects. That comparison is the subsystem's measurable result for the report.

It improves on the 2019 LabVIEW model by running on its own wireless ESP32 node, reporting real measured power, and handling low light (hold, then park) rather than chasing noise.

## 2. Parts

| Part | Qty used | Source | Role |
|---|---|---|---|
| ESP32-WROOM-32 DevKit + 38-pin screw-terminal breakout | 1 | order list (6 bought) | controller, Wi-Fi/MQTT |
| MG90S metal-gear micro servo | 2 (4-pack) | order list | pan and tilt |
| GL5528 photoresistor | 4 (20-pack) | order list | light direction sensing |
| 10 kΩ resistor | 4 | on hand | LDR divider bottom half |
| Mini solar panel, 6 V 1–2 W (~110 × 60 mm) | 2 | order list | tracked + fixed reference |
| INA219 current/voltage sensor | 2 (4-pack) | order list | panel V, mA, mW |
| 22 Ω 3 W resistor (20–27 Ω, ≥ 2 W) | 2 | on hand | fixed panel load so power is real |
| 470 µF 10 V electrolytic (C2) | 1 | on hand | absorbs servo start-up spikes |
| 10 µF electrolytic (EN–GND) | 1 | on hand | auto upload-mode fix from the bench test |
| 3D-printed tracker: base, yoke, panel plate with LDR seat + cross divider, 2 tilt ears | 5 prints | `hardware/3d-prints/` | mechanism (replaces the $30 bracket kit) |
| M3 × 8/12 screws, nuts, nyloc, washers; M2 self-tappers (servo bags) | – | lab / servo bags | assembly |
| 18 AWG red/black pair from the Wago bus; 22 AWG hook-up; JST-XH leads | – | order list | power and signals |

The **pan/tilt bracket kit ($30)** is still on the order list but is no longer needed now that the mount is 3D-printed.

## 3. Wiring and power

Full schematic: [`docs/circuits/06_solar_tracker_node.png`](../circuits/06_solar_tracker_node.png).

| ESP32 pin | Connects to |
|---|---|
| VIN / GND | +5V and GND from the fused 10 A rail (Wago bus, 18 AWG) |
| 3V3 | LDR divider tops, INA219 VCC |
| GPIO32 / 33 / 35 / 39 | LDR TL / TR / BL / BR, each 3V3 → LDR → pin → 10 kΩ → GND (ADC1 only, works with Wi-Fi on) |
| GPIO18 / GPIO19 | pan / tilt servo signal (3.3 V drives MG90S fine) |
| GPIO21 SDA / GPIO22 SCL | INA219 #1 at 0x40 (tracked), #2 at 0x41 (reference, A0 bridged) |
| EN | 10 µF to GND |

- **Servo power** comes from the +5V rail, not the ESP32. C2 (470 µF) at the servo power terminal stops stall/start spikes (~0.7 A each) from browning out the board. Servos are budgeted at 1 A peak of the rail's ~6.5 A.
- **Panel measurement:** panel + → INA219 VIN+ → VIN− → 22 Ω load → GND; panel − to common GND. Both panels see the same load, so the comparison is fair. A 6 V, ~330 mA panel stays well inside the INA219's default 32 V / 3.2 A range; use its 32 V / 400 mA calibration for finer mA resolution.
- **LDR range:** brighter = higher voltage. The ESP32 ADC is most linear between about 0.2 and 1.9 V (Maier et al.). If a bright lamp saturates the readings, drop the 10 kΩ to 4.7 kΩ.

## 4. Mechanism (3D-printed)

- Pan servo stands upright in `tracker_base`; `tracker_yoke` sits on its horn and carries the tilt servo on the left arm and an M3 pivot on the right.
- `tracker_panel_plate` holds the panel (foam tape) and, at one end outside the panel's shadow, the 4-LDR seat with 22 mm cross-shaped divider walls. Weissbach & Aunkst found a divider raises the left/right signal from 0.9 % to 7.9 % at 10° off-sun.
- Collision check: the plate sweeps −75° to +75° tilt with no contact. Keep tilt within about ±65° of level.
- Print `tracker_base` first to check the servo fit (servo dimensions are datasheet values).

## 5. Control logic (`firmware/node/src/node_solar.cpp`)

Loop every **100 ms**:

1. **Read LDRs** (TL, TR, BL, BR; 0–4095).
2. **Low light check:** if the sum of all four is below 600 (out of 16 380), start a dark timer. After 10 s publish `event/low_light 1` and hold still; after 60 s **park** at pan 90°, tilt 45°. When light returns, publish `low_light 0` and resume. This follows Hafez (LDR trackers fail on cloudy days) and Chenchireddy (park when there's no sun).
3. **Error signals:** `ePan = (right − left) / (right + left)`, `eTilt = (top − bottom) / (top + bottom)`. Normalising by the total makes them independent of overall brightness.
4. **Dead band:** ignore errors under 5 %. This stops servo jitter; Mousazadeh shows 10° off-sun still gives 98.5 % of output.
5. **Proportional step:** move `error × 20°`, capped at **2° per step** (≤ 20°/s), so motion is smooth and current spikes stay small.
6. **Travel limits:** pan 10–170°, tilt 10–90° (servo degrees). Servo pulse 500–2500 µs over 0–180°.

Modes (`cmd/mode`): **track** (above), **park** (hold 90/45), **manual** (dashboard sliders; sending an angle switches to manual automatically). After a reboot the node restores mode and angles from its retained state topics.

Telemetry every 5 s: `panel_v`, `panel_ma`, `panel_mw` (tracked), `ref_mw` (fixed). **Today these values are simulated**; the INA219 reads are a marked TODO in the code. The fixed reference panel is modelled facing az 90°, el 45°.

**Simulation mode** (`SIM_INPUTS=1`): a virtual sun lights virtual LDRs so the loop runs on a bare board. Serial or MQTT commands: `sun <az> <el>`, `sun sweep` (30→150° over 5 min), `light <0–1>`.

## 6. MQTT and dashboard

Prefix `home/solar/node1/`; login `solar`, allowed only `home/solar/#`.

| Topic | Payload | When |
|---|---|---|
| `status` | online / offline (Last Will) | connect / drop |
| `tele/panel_v`, `panel_ma`, `panel_mw`, `ref_mw` | numbers | every 5 s |
| `state/pan_deg`, `state/tilt_deg` | 0–180 | on change, max 1/s |
| `state/mode` | track / park / manual | on change |
| `event/low_light` | 1 / 0 | after 10 s dark / on recovery |
| `cmd/mode`, `cmd/pan_deg`, `cmd/tilt_deg` | from dashboard | user action |

Node-RED **Solar** tab: mode, pan and tilt readouts; mode dropdown; manual pan/tilt sliders; a "Tracked vs fixed panel" line chart (mW). The Overview tab shows live solar power.

## 7. Test status

- **Logic on real hardware:** `system_check` solar 11/11 passed (tracks to pan ~150 / tilt ~70, holds in the dead band, stops at the 170° limit, low-light event in 10 s, park → 90°, manual pan 30 switches to manual).
- **Simulated sun sweep:** pan followed 31° → 149° and back. Tracked panel averaged **+24.5 %** vs fixed (62/62 samples at or above). Simulated until real LDRs and INA219s are wired.
- Network figures shared by all nodes: median 11.7 ms round trip, reconnect 0.25 s after the router comes back.

## 8. Open items

1. **Write the INA219 driver** (two sensors, 0x40/0x41) and replace the simulated telemetry; set `SIM_INPUTS=0` for this node.
2. **Check the servo-angle mapping at assembly:** the firmware's tilt range is 10–90 servo degrees with park at 45. Mount the tilt horn so that range stays within ±65° of level (the 3D-print clearance). Adjust `TILT_MIN/MAX` and `PARK_TILT` to match.
3. **Calibrate:** check each LDR's raw reading under even light and add per-channel offsets if they differ. Tune `LOW_LIGHT` (600) in the real room, and `DEAD_BAND` / `GAIN_DEG` if it hunts or lags.
4. **Set the reference panel's real orientation** (the sim assumes az 90°, el 45°) and mount it beside the tracker.
5. **Test outdoors** in spring, after the Feb 1 mounting date. Guo et al. lost November/December test days to weather. Bench-test with a lamp first.
6. **Remove the $30 pan/tilt bracket** from the order list.
7. Optional: add a daily energy (Wh) total for each panel in Node-RED. It's a stronger report figure than instantaneous mW.

## References (from research/references.md)

Hafez et al. 2018 [14] (dual-axis, 4 LDR + 2 motors); Weissbach & Aunkst 2007 [19] (shade divider); Mousazadeh et al. 2009 [13] (10° off-sun = 98.5 %); Chenchireddy et al. 2025 [15] (cross LDRs, travel limits, park); Guo et al. 2009 [18] (test season); Maier et al. 2017 [5] (ESP32 ADC window).
