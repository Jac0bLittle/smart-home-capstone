#!/usr/bin/env bash
# Build the node firmware as a PC program (no ESP32 needed) to check it compiles
# and to run "virtual nodes" against a real broker.
#   ./build.sh climate        -> build/node_climate
#   MQTT_PASS=... ./build/node_climate
# Needs: g++, and two source checkouts next to the repo (or set the paths):
#   git clone --depth 1 https://github.com/arduino/ArduinoCore-API
#   git clone --depth 1 https://github.com/256dpi/arduino-mqtt
set -euo pipefail
cd "$(dirname "$0")"
API=${ARDUINO_API:-../../../vendor/ArduinoCore-API}
MQ=${ARDUINO_MQTT:-../../../vendor/arduino-mqtt}
OUT=build; mkdir -p $OUT
for sub in ${@:-climate alarm lighting solar}; do
  def=NODE_$(echo "$sub" | tr a-z A-Z)
  objs=()
  for c in "$MQ"/src/lwmqtt/*.c; do
    o=$OUT/$(basename "$c" .c).o; gcc -O1 -c "$c" -o "$o"; objs+=("$o")
  done
  g++ -std=gnu++17 -O1 -Wall -Wextra -Wno-unused-parameter -D$def -DSIM_INPUTS=1 -DSIM_POT=0 -DHOST \
      -I. -I../include -I"$API" -I"$MQ/src" \
      ../src/main.cpp ../src/node_$sub.cpp hal_native.cpp \
      "$MQ"/src/MQTTClient.cpp \
      "$API"/api/String.cpp "$API"/api/Print.cpp "$API"/api/Stream.cpp "$API"/api/IPAddress.cpp \
      "$API"/api/Common.cpp "$API"/test/src/itoa.cpp "$API"/test/src/dtostrf.cpp \
      "${objs[@]}" -o $OUT/node_$sub
  echo "built $OUT/node_$sub"
done
