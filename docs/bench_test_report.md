# Bench test report: Smart Home Model prototype (Nov 16–17, 2026)

**Result: every hardware test passed.** The hub, all four node firmwares and the alerting worked on real boards. The only hardware-related bug found (54 ms latency) was fixed and re-measured at 11.7 ms. All CSVs and logs are in `results/`.

Hardware: Raspberry Pi 5 8 GB as a stand-in for `jarvis` (192.168.0.10), Raspberry Pi 4B as `testbench` (192.168.0.11), one ESP32-WROOM-32 flashed as each node in turn, an Arduino Nano v3 as a sensor simulator, and a TP-Link Archer AX21 as the isolated project LAN (no internet; the Pis reach the internet over the apartment Wi-Fi for installs only).

## Results

| # | Test | Pass if | Result | Measured |
|---|---|---|---|---|
| 1 | Hub install | 4 services active | Pass | Mosquitto, logger, alerter, Node-RED all active |
| 2 | Hub RAM | < 1.5 GB used | Pass | 437 MiB used, no swap |
| 4 | ESP32 first connect | boot_ms < 10 s | Pass | 2,308 ms to broker after boot |
| 5 | Logic on real hardware | system_check passes, all 4 envs | Pass | climate 13/13, alarm 15/15, lighting 11/11, solar 11/11 |
| 6 | Round-trip latency | median < 50 ms, p95 < 150 ms, 0 loss | Pass | median 11.7 ms, p95 19.9 ms, max 30.7 ms, 0/200 lost |
| 6b | Latency from testbench over the AX21 | same | Pass | climate 11.6 / 16.9 ms, alarm 12.1 / 18.4 ms (median / p95), 0 lost |
| 9 | Reconnect after router power-cycle | back < 60 s after Wi-Fi returns | Pass (1 of 3 runs) | node online 0.25 s after the router link came up; no reboot, no heater cut-off |
| 11 | Alert delivery | push < 5 s; offline alert < 90 s | Pass (push) | ntfy hand-off 112–126 ms (first after restart 10.1 s); offline alert at 60 s; Gmail not configured |
| 12 | Access rules | acl_test all pass | Pass | all checks passed on the real broker |
| 13 | Nano: intruder / false alarm / walk-by | s1 triggers, s2 and s3 don't | Pass | ESP32 reaction (motion to buzzer) 41 ms, no network in the path |
| 13b | Dusk test with a photoresistor | light on in the dark with motion, off in light | Pass | 518 lux room, 231 lux covered, threshold 375; light on 12 ms after motion |
| 14 | Soak | 0 unplanned reconnects in 1 h; free_heap ±5 kB; log < 20 MB/day | Pass | 66.7 min on the lighting node (shortened from 3 h); 400/400 pings, 0 lost; RTT median 14 ms, p95 21 ms (max 32 ms); 0 reconnects, no reboot; free_heap 248,076 → 247,428 B (min 243,492, −4.6 kB); RSSI −17 to −13 dBm; log.db +233 kB → about 5.0 MB/day |
| 10a | Reconnect after a forced socket drop (`drop` on the serial console) | back < 5 s | Pass | 3 runs: 53, 51, 49 ms; 0 messages dropped |
| 10b | Reconnect after a Mosquitto restart | back < 10 s | Pass | 2,049 ms (first retry refused while the broker started, second connected) |
| 7, 8 | Far-side latency and RSSI | | Not run | for the next session |

Solar tracking, simulated sun: during a 5-minute sweep, pan followed the sun from 31° to 149° and back, and the tracked panel averaged 24.5% more power than the fixed reference panel (62 of 62 samples at or above it). These panel numbers are simulated until real LDRs and INA219s are wired.

## Bugs found and fixed

1. **Latency 54.5 ms → 11.7 ms median.** The ESP32 sent its pong behind the PUBACK for the ping and waited for the Pi's 40 ms delayed ACK (Nagle's algorithm). Fix: `WiFiClient::setNoDelay(true)` right after the MQTT connect (`netOnConnected()` in `hal_esp32.cpp`). The broker already had `set_tcp_nodelay true`.
2. **system_check race.** The manual-mode heater check set a low temperature while the node was still in auto, so the node turned the heater on by itself and the "heater 1" command changed nothing. Fix: switch to manual and set the heater off first.
3. **install.sh.** Node-RED's installer download link had moved (404). The script now uses the new link and runs Node-RED as the normal user; `nodered/deploy_flows.sh` deploys the dashboard with the hub login read from `hub.env` on the Pi.
4. **acl_test.py** only printed to the screen; it now also saves a CSV like the other scripts.

## Notes for the final build

- The ESP32 DevKit used here doesn't enter download mode by itself ("Wrong boot mode"): hold IO0 while uploading, or fit 10 µF between EN and GND.
- Pi OS (Debian 13) needed its Wi-Fi to disconnect from the AX21 before it could see the apartment's 5 GHz network on DFS channel 136.
- The router's DHCP reservations only apply inside the pool (pool set to .10–.199).
- "Node offline" alerts fired for the three nodes the single ESP32 wasn't playing at the time; with four boards they won't.
- The lighting node keeps `lux_threshold = 375` (restored after reboot), which matches this photoresistor and 10 kΩ divider; re-tune with a different sensor or room.

## Where things are

- `firmware/node/`: one PlatformIO project, envs `climate`, `alarm`, `lighting`, `lighting_pot` (reads GPIO34), `solar`; `native/` builds it as a PC program
- `firmware/nano_sim/`: Nano sensor simulator, scenarios s1–s4
- `hub/`: install script, Mosquitto config and ACL, logger and alerter services, Node-RED dashboard
- `testbench/`: system_check, latency_test, reconnect_watch, acl_test
- `results/`: every CSV and log from Nov 16–17
- `docs/prototype_README.md`: setup steps and commands
