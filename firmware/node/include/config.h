// Smart Home Model - shared node settings. Values marked TUNE are starting
// points from the Device Configuration Sheet; adjust them during testing.
#pragma once

#if defined(NODE_CLIMATE)
  #define NODE_SUB "climate"
#elif defined(NODE_ALARM)
  #define NODE_SUB "alarm"
#elif defined(NODE_LIGHTING)
  #define NODE_SUB "lighting"
#elif defined(NODE_SOLAR)
  #define NODE_SUB "solar"
#else
  #error "Pick a node: build with -DNODE_CLIMATE, -DNODE_ALARM, -DNODE_LIGHTING or -DNODE_SOLAR"
#endif

#ifndef SIM_INPUTS
  #define SIM_INPUTS 1
#endif
#ifndef SIM_POT
  #define SIM_POT 0
#endif

// ---- MQTT (sheet section 4) ----
#define NODE_ID           "node1"
#define TOPIC_PREFIX      "home/" NODE_SUB "/" NODE_ID "/"
#define CLIENT_ID         NODE_SUB "-" NODE_ID      // fixed client ID, e.g. climate-node1
#define HUB_STATUS_TOPIC  "home/hub/jarvis/status"
#define MQTT_KEEPALIVE_S  15        // broker marks node offline ~1.5 x this after a drop
#define MQTT_TIMEOUT_MS   2000      // max wait for CONNACK / PUBACK
#define MQTT_BUF_BYTES    512

// ---- Rates (sheet 4.2) ----
#define HEARTBEAT_MS      10000UL   // tele/uptime_s
#define SLOW_TELE_MS      60000UL   // tele/rssi_dbm, tele/free_heap

// ---- Reconnect backoff ----
#define WIFI_RETRY_MIN_MS 5000UL
#define WIFI_RETRY_MAX_MS 30000UL
#define MQTT_RETRY_MIN_MS 1000UL
#define MQTT_RETRY_MAX_MS 16000UL
#define RESTORE_WINDOW_MS 1500UL    // time to collect retained state after first connect

// ---- Pins (ESP32-WROOM-32 DevKit) ----
// Analog inputs on ADC1 only (GPIO32-39): ADC2 does not work while Wi-Fi is on.
#define PIN_LED        2    // on-board LED: heater / buzzer / light level in sim
#define PIN_BOOT_BTN   0    // BOOT button, active low: motion in sim
#define PIN_POT        34   // optional pot (SIM_POT=1)
#define PIN_MOTION     27   // PIR (or Nano simulator D2 through a divider)
#define PIN_DOOR       26   // reed switch (or Nano simulator D3 through a divider)
#define PIN_SERVO_PAN  18
#define PIN_SERVO_TILT 19
