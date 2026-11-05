# Smart Home Model Capstone

ENEE capstone, UTC. An ESP32 and Raspberry Pi 5 redesign of the 2019 myRIO/LabVIEW smart home model.

**Team:** Gage Boggess, Jacob Little, Brady Mullaly, Jacob Pickett · **Sponsor:** Dr. Abdul Ofoli

## How it fits together

Four ESP32 nodes (climate, alarm, lighting, solar tracker) talk over Wi-Fi to the hub, a Raspberry Pi 5
named `jarvis`. The hub runs a Mosquitto MQTT broker (one login per node) and Node-RED with
FlowFuse Dashboard 2.0 at `http://jarvis.local:1880/dashboard`.

## Repo layout

| Folder | What's in it |
|---|---|
| `firmware/climate`, `alarm`, `lighting`, `solar` | One PlatformIO project per ESP32 node |
| `firmware/common` | Code shared by every node (Wi-Fi and MQTT connection) |
| `hub/mosquitto` | Broker config and access rules (no passwords) |
| `hub/node-red` | Exported flows and dashboard |
| `docs` | Topic map, wiring notes, reports |
| `hardware` | Schematics and wiring diagrams |

## Building a node

1. Open the node's folder (for example `firmware/climate`) in VSCodium with the PlatformIO extension.
2. Copy `include/secrets.example.h` to `include/secrets.h` and fill in the Wi-Fi and MQTT logins.
   `secrets.h` is git-ignored, so it never leaves your laptop.
3. Click **Build**, then **Upload** with the board plugged in.

## Secrets

Never commit passwords. Wi-Fi and MQTT logins live only in each node's `include/secrets.h`;
the Mosquitto `passwd` file and Node-RED's `flows_cred.json` stay on the hub. If a password is ever
committed by mistake, change that password; deleting the commit is not enough.
