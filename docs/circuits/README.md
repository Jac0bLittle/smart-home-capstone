# Circuit diagrams

Report-ready circuit diagrams for the Smart Home Model, drawn from the Nov 19 order list, the node firmware pin map (`config.h`), and the Nov 16–17 bench test.

| Diagram | PNG | SVG |
|---|---|---|
| Power distribution (5 V 10 A rail, fuse, Wago buses, current budget) | [png](01_power_distribution.png) | [svg](01_power_distribution.svg) |
| Hub and network (router, Pi 5, nodes, voice) | [png](02_hub_network.png) | [svg](02_hub_network.svg) |
| Climate node (BME680, SHT40, heater + KSD9700, fan) | [png](03_climate_node.png) | [svg](03_climate_node.svg) |
| Alarm node (PIR, reed switch, buzzer) | [png](04_alarm_node.png) | [svg](04_alarm_node.svg) |
| Lighting node (WS2812B ×2, 74AHCT125, BH1750, PIR) | [png](05_lighting_node.png) | [svg](05_lighting_node.svg) |
| Solar tracker node (4 LDRs, 2× MG90S, 2× INA219) | [png](06_solar_tracker_node.png) | [svg](06_solar_tracker_node.svg) |

[Smart_Home_Circuit_Diagrams.pdf](Smart_Home_Circuit_Diagrams.pdf) has all six plus a pin map and a list of parts the order list is missing.

## Pin map

| Node | GPIO | Connects to |
|---|---|---|
| All | VIN / GND | +5V rail / GND bus; EN has 10 µF to GND |
| Climate | 21 / 22 | I2C: BME680 (0x77), SHT40 (0x44) |
| Climate | 25 / 26 | D4184 → heater (via KSD9700) / D4184 → fan |
| Alarm | 27 / 26 / 25 | PIR / reed (pull-up, HIGH = open) / D4184 → buzzer |
| Lighting | 27 / 16 / 21-22 | PIR / 74AHCT125 → strip DIN / BH1750 (0x23) |
| Solar | 32, 33, 35, 39 | LDR TL, TR, BL, BR (10 kΩ to GND) |
| Solar | 18 / 19 / 21-22 | pan / tilt servo / INA219 0x40 + 0x41 |

## Regenerating

```
pip install schemdraw matplotlib reportlab pillow
cd src && python build.py   # writes into src/out/
```
