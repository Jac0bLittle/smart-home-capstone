// Shared Wi-Fi + MQTT connection for every node.
// Each node defines NODE_NAME in platformio.ini and the logins in include/secrets.h.
#pragma once
#include <WiFi.h>
#include <PubSubClient.h>
#include "secrets.h"

namespace homenet {

inline WiFiClient wifiClient;
inline PubSubClient mqtt(wifiClient);

inline void connectWifi() {
  if (WiFi.status() == WL_CONNECTED) return;
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print('.'); }
  Serial.printf(" connected, IP %s\n", WiFi.localIP().toString().c_str());
}

inline void connectMqtt() {
  while (!mqtt.connected()) {
    String status = String("home/") + NODE_NAME + "/status";
    // Last will marks the node offline if it drops off.
    if (mqtt.connect(NODE_NAME, MQTT_USER, MQTT_PASSWORD, status.c_str(), 1, true, "offline")) {
      mqtt.publish(status.c_str(), "online", true);
      Serial.println("MQTT connected");
    } else {
      Serial.printf("MQTT failed (rc=%d), retrying\n", mqtt.state());
      delay(2000);
    }
  }
}

inline void begin() {
  connectWifi();
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  connectMqtt();
}

inline void loop() {
  connectWifi();
  connectMqtt();
  mqtt.loop();
}

}  // namespace homenet
