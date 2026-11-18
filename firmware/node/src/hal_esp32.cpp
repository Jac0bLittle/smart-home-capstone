// ESP32 implementation of hal.h (Arduino core 2.0.x; 3.x LEDC calls handled too).
#ifdef ARDUINO_ARCH_ESP32
#include <Arduino.h>
#include <WiFi.h>
#include "node.h"
#include "hal.h"

#if __has_include("secrets.h")
  #include "secrets.h"
#else
  #error "Copy include/secrets.example.h to include/secrets.h and fill it in"
#endif

#if defined(NODE_CLIMATE)
  #define MQTT_PASS MQTT_PASS_CLIMATE
#elif defined(NODE_ALARM)
  #define MQTT_PASS MQTT_PASS_ALARM
#elif defined(NODE_LIGHTING)
  #define MQTT_PASS MQTT_PASS_LIGHTING
#else
  #define MQTT_PASS MQTT_PASS_SOLAR
#endif

static WiFiClient wifiClient;
static const int LED_CH = 0, SERVO_CH0 = 2;

static void pwmSetup(int pin, int ch, int freq, int bits) {
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  (void)ch; ledcAttach(pin, freq, bits);
#else
  ledcSetup(ch, freq, bits); ledcAttachPin(pin, ch);
#endif
}
static void pwmWrite(int pin, int ch, uint32_t duty) {
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  (void)ch; ledcWrite(pin, duty);
#else
  (void)pin; ledcWrite(ch, duty);
#endif
}

void halInit() {
  pinMode(PIN_BOOT_BTN, INPUT_PULLUP);
  pwmSetup(PIN_LED, LED_CH, 5000, 8);
#ifdef NODE_SOLAR
  pwmSetup(PIN_SERVO_PAN, SERVO_CH0, 50, 16);
  pwmSetup(PIN_SERVO_TILT, SERVO_CH0 + 1, 50, 16);
#endif
  analogReadResolution(12);
}

bool halBootButton() { return digitalRead(PIN_BOOT_BTN) == LOW; }
bool halDigital(int pin) { return digitalRead(pin) == HIGH; }
void halInputPulldown(int pin) { pinMode(pin, INPUT_PULLDOWN); }
int halAnalogMv(int pin) { return (int)analogReadMilliVolts(pin); }
void halLed(int pct) { pwmWrite(PIN_LED, LED_CH, (uint32_t)clampi(pct, 0, 100) * 255 / 100); }
uint32_t halFreeHeap() { return ESP.getFreeHeap(); }

void halServo(int idx, int deg) {
  // 500-2500 us pulse in a 20 ms frame. TUNE to the servo model's datasheet.
  uint32_t us = 500 + (uint32_t)clampi(deg, 0, 180) * 2000 / 180;
  uint32_t duty = us * 65535UL / 20000UL;
  pwmWrite(idx == 0 ? PIN_SERVO_PAN : PIN_SERVO_TILT, SERVO_CH0 + idx, duty);
}

void netBegin(const char *hostname) {
  WiFi.mode(WIFI_STA);
  WiFi.setHostname(hostname);
  WiFi.setSleep(false);          // modem sleep adds 100+ ms latency; off for testing
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
}
bool netWifiUp() { return WiFi.status() == WL_CONNECTED; }
void netWifiRetry() { WiFi.reconnect(); }   // fallback; the core also auto-reconnects
int netRssi() { return netWifiUp() ? WiFi.RSSI() : 0; }
// Turn off Nagle on our side too. Without it, the pong waits behind the PUBACK for
// the ping until the Pi's delayed ACK (~40 ms) arrives. Only works once connected.
void netOnConnected() { wifiClient.setNoDelay(true); }
void netForceDrop() { wifiClient.stop(); }  // drops the MQTT socket only; power-cycle the router to test Wi-Fi loss
Client &netClient() { return wifiClient; }
const char *netMqttHost() { return MQTT_HOST; }
int netMqttPort() { return MQTT_PORT; }
const char *netMqttPass() { return MQTT_PASS; }

#endif
