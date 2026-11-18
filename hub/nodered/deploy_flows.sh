#!/usr/bin/env bash
# Deploys flows.json to the local Node-RED with the hub MQTT login filled in on the
# "jarvis broker" node (id sh0001). The password is read from /etc/smarthome/hub.env on
# the Pi and never printed. Run as root:   sudo bash ~/hub/nodered/deploy_flows.sh
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo "Run with sudo"; exit 1; }
FLOWS="${1:-$(dirname "$(readlink -f "$0")")/flows.json}"
NR_USER=${SUDO_USER:-jacob}
SETTINGS="$(getent passwd "$NR_USER" | cut -d: -f6)/.node-red/settings.js"

if [[ -f "$SETTINGS" ]] && grep -qE '^[[:space:]]*adminAuth[[:space:]]*:' "$SETTINGS"; then
  echo "adminAuth is enabled in $SETTINGS - this script only handles an open local admin API."; exit 2
fi

python3 -I - "$FLOWS" <<'EOF'
import json, sys, urllib.request, urllib.error
env = {}
for line in open("/etc/smarthome/hub.env"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
pw = env.get("MQTT_PASS", "")
if not pw:
    sys.exit("MQTT_PASS is empty in hub.env")
flows = json.load(open(sys.argv[1]))
hits = [n for n in flows if n.get("id") == "sh0001" and n.get("type") == "mqtt-broker"]
if len(hits) != 1:
    sys.exit("broker node sh0001 not found in flows.json")
hits[0]["credentials"] = {"user": "hub", "password": pw}
req = urllib.request.Request("http://127.0.0.1:1880/flows", data=json.dumps(flows).encode(),
    headers={"Content-Type": "application/json", "Node-RED-Deployment-Type": "full"}, method="POST")
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print("HTTP", r.status)
except urllib.error.HTTPError as e:
    print("HTTP", e.code); sys.exit(1)
EOF
