#!/usr/bin/env bash
# Run all four virtual nodes (PC build of the firmware) against a broker.
#   PASS_CLIMATE=.. PASS_ALARM=.. PASS_LIGHTING=.. PASS_SOLAR=.. MQTT_HOST=192.168.0.10 ./run_all.sh
# Logs go to build/<node>.log; stop with: pkill -f build/node_
set -euo pipefail
cd "$(dirname "$0")"
for sub in climate alarm lighting solar; do
  [[ -x build/node_$sub ]] || ./build.sh $sub
  var="PASS_$(echo $sub | tr a-z A-Z)"
  [[ -n "${!var:-}" ]] || { echo "set $var"; exit 1; }
  MQTT_PASS="${!var}" nohup ./build/node_$sub < /dev/null > build/$sub.log 2>&1 &
  echo "started $sub-node1 (log: build/$sub.log)"
done
