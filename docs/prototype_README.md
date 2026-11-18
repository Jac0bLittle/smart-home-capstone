# Smart Home Model: bench prototype code

Hub (Raspberry Pi), ESP32 node firmware, a Nano sensor simulator and test bench
scripts for the Nov 9 board tests. Settings follow the Device Configuration Sheet
(topic map, logins, rates). Passwords never go in these files.

```
hub/
  install.sh              one-shot Pi setup: Mosquitto, logger, alerter, Node-RED, Dashboard 2.0
  mosquitto/              smarthome.conf, smarthome.acl, make_passwords.sh
  services/               mqtt_logger.py (SQLite, 30-day), alerter.py (ntfy + Gmail), hubcommon.py
  systemd/                services for the logger and alerter
  nodered/flows.json      dashboard: Overview, Climate, Alarm, Lighting, Solar, System
  nodered/build_flows.py  source for flows.json (edit layout here, see below)
  hub.env.example         settings file template (/etc/smarthome/hub.env)
firmware/node/            ONE PlatformIO project, four envs: climate, alarm, lighting, solar
  native/                 builds the same firmware as a PC program ("virtual nodes")
firmware/nano_sim/        Arduino Nano v3 sensor simulator (motion, door, analog, reaction timer)
testbench/                system_check, latency_test, reconnect_watch, acl_test
```

## Already checked (Nov 8, without boards)

Run in a container against Mosquitto 2.0.18 with this exact config and ACL:

| Check | Result |
|---|---|
| Firmware compiles (all 4 nodes, PC build with the real 256dpi/MQTT 2.5.3 library, `-Wall -Wextra`) | no errors, no warnings |
| Nano simulator compiles (avr-gcc, ATmega328P) | 5.7 kB flash (17.5%), 260 B RAM |
| `system_check.py` on 4 virtual nodes + alerter (DRY_RUN) | 50/50 |
| `acl_test.py` | 21/21 |
| Ping/pong round trip on localhost | median 1.4 ms, p95 2.6 ms (was 43 ms before `set_tcp_nodelay true`) |
| Broker restart | nodes back in about 2 s |
| Node restart | setpoint and mode restored from retained state |
| Hub offline with heater on in manual mode | heater cut off after 60 s, `heater_cutoff hub_lost` sent |
| Node-RED import | 0 invalid nodes; all 6 pages render with live data |

Not checked yet (needs the boards): the ESP32-only code in `hal_esp32.cpp` (Wi-Fi,
PWM, ADC). PlatformIO's download server was blocked in the container, so the first
real ESP32 build happens on your laptop. The calls were checked against the
Arduino-ESP32 2.0.17 headers.

## Tomorrow, in order

**1. Router (AX21).** 2.4 GHz SSID and password, WPA2-Personal, DHCP reservations
for the Pi (192.168.0.10) and the test Pi (192.168.0.11). Sheet section 1.

**2. Hub (Pi 5 8 GB as a stand-in for jarvis).** Flash Raspberry Pi OS Lite 64-bit
with Imager (hostname `jarvis`, your user, SSH key). Plug it into the router by
Ethernet, then from your laptop:

```bash
scp -r hub <user>@jarvis.local:~/
ssh <user>@jarvis.local
sudo bash ~/hub/install.sh        # asks for the 6 MQTT passwords once
```

Then open `http://jarvis.local:1880`, choose Menu, then Import, and pick `hub/nodered/flows.json`.
Double-click the **jarvis broker** config node, go to Security, enter user `hub` and its password, then Deploy.
Dashboard: `http://jarvis.local:1880/dashboard`.

Alerts: put `NTFY_TOPIC` (long random name) and the Gmail app password in
`/etc/smarthome/hub.env`, set `DRY_RUN=0`, then `sudo systemctl restart smarthome-alerter`.
The Send test alert button on the Alarm page tests both channels.

**3. ESP32.** Open `firmware/node` in VSCodium with PlatformIO. Copy
`include/secrets.example.h` to `include/secrets.h` and fill it in. Pick the env in
the status bar (start with `climate`), then Upload and Monitor. Type `status` in the
monitor. Re-flash with another env to test the next node; one board can be every node.

**4. Test bench (Pi 4B or laptop).** Needs `python3-paho-mqtt` (apt) or `pip install paho-mqtt`.

```bash
export TB_HOST=192.168.0.10 TB_PASS=<tester password>
python3 testbench/system_check.py              # logic checks on every online node
python3 testbench/latency_test.py --node climate --count 200
python3 testbench/reconnect_watch.py           # leave running, then power-cycle the router
python3 testbench/acl_test.py                  # asks for each node password
```

Each script writes a CSV next to where it runs. The alerter's 5-minute cooldown
blocks repeat alerts, so for back-to-back `system_check` runs set
`ALERT_COOLDOWN_S=5` in hub.env while testing.

**5. Nano (optional).** `firmware/nano_sim`: Upload, then Monitor, then type `?`. Every Nano to
ESP32 wire needs a divider (1 k in series, 2 k to GND) because the Nano is 5 V.
Wiring is at the top of `src/main.cpp`. The scenarios `s1` to `s4` run the intruder,
false-alarm, walk-by and dusk tests. `react_ms` shows how long the ESP32 took to react
(stimulus to LED) with no network involved.

## Node commands

Serial monitor (115200): `status`, `drop` (closes the MQTT socket so you can time a reconnect), `sim <...>`.
The same sim commands work over MQTT on `home/<sub>/node1/cmd/sim` (tester or hub login):

| Node | Sim commands | On-board LED shows |
|---|---|---|
| climate | `temp 28.5`, `temp auto`, `hum 55` | heater |
| alarm | `motion` (or BOOT button), `door 1` / `door 0`, `gas 3000` | buzzer (fast blink) |
| lighting | `lux 20`, `motion` (or BOOT button) | light level (PWM) |
| solar | `sun 120 45`, `sun sweep`, `light 0.1` | (servo PWM on GPIO18/19) |

Every node also answers `cmd/ping` with `event/pong` (latency), reports
`event/boot_ms` and `event/reconnect_ms`, and sends `tele/uptime_s` every 10 s and
`tele/rssi_dbm` / `tele/free_heap` every 60 s. Set `SIM_INPUTS=0` in
`platformio.ini` for the final build; set `SIM_POT=1` if a pot (or the Nano's analog
output) is wired to GPIO34.

Tuning values (hysteresis, exit delay, hold timer, dead band, limits) are at the top
of each `src/node_<sub>.cpp`, marked TUNE.

## Virtual nodes (no ESP32 needed)

`firmware/node/native/` builds the same firmware as a Linux program, which is useful
for trying the dashboard before flashing anything:

```bash
git clone --depth 1 https://github.com/arduino/ArduinoCore-API vendor/ArduinoCore-API
git clone --depth 1 https://github.com/256dpi/arduino-mqtt vendor/arduino-mqtt
sudo apt install g++
firmware/node/native/build.sh
PASS_CLIMATE=.. PASS_ALARM=.. PASS_LIGHTING=.. PASS_SOLAR=.. MQTT_HOST=192.168.0.10 firmware/node/native/run_all.sh
```

Stop a real ESP32 before running its virtual twin, since they share a client ID.

## Editing the dashboard

Either edit in the Node-RED editor and export, or change `build_flows.py`, run it
(writes `flows_minimal.json`), import that into Node-RED, and export the result as
`flows.json`. Dashboard 2.0's text widget shows the raw payload, so units and ON/OFF
labels come from small "format" function nodes in front of each text row.

## Fitting into the team repo

`github-repo/smart-home-capstone` has stub folders `firmware/climate`, `alarm`, and so on.
This code uses one shared project with four envs instead, because all four nodes share
95% of the code. Either replace the four stubs with `firmware/node`, or keep the stubs
and point each at the shared `src`. The repo's stub ACL uses a `nodered` login and
`pattern readwrite home/%u/#`. This one uses a `hub` login (as in the device sheet),
and each node can also read `home/hub/jarvis/status`.
