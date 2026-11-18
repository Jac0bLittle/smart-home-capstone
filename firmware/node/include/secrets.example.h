// Copy this file to include/secrets.h and fill it in. secrets.h is git-ignored.
// Passwords are the ones set with make_passwords.sh on the hub.
#pragma once

#define WIFI_SSID   "SmartHome-IoT"      // 2.4 GHz SSID on the project router
#define WIFI_PASS   "change-me"
#define MQTT_HOST   "192.168.0.10"       // jarvis (use your test Pi's IP tomorrow)
#define MQTT_PORT   1883

// One login per node (sheet section 2). Only the one for the env you build is used.
#define MQTT_PASS_CLIMATE   "change-me"
#define MQTT_PASS_ALARM     "change-me"
#define MQTT_PASS_LIGHTING  "change-me"
#define MQTT_PASS_SOLAR     "change-me"
