// Hardware layer. hal_esp32.cpp implements it on the board; native/hal_native.cpp
// implements it on a PC so the same node logic can run against a real broker.
#pragma once
#include <Arduino.h>
#include <Client.h>

void     halInit();
bool     halBootButton();             // true while BOOT is held
bool     halDigital(int pin);         // input with pull-down
void     halInputPulldown(int pin);
int      halAnalogMv(int pin);        // millivolts, ADC1 pins only
void     halLed(int pct);             // on-board LED, 0-100 %
void     halServo(int idx, int deg);  // idx 0 = pan, 1 = tilt
uint32_t halFreeHeap();

void     netBegin(const char *hostname);
bool     netWifiUp();
void     netWifiRetry();
int      netRssi();
void     netOnConnected();            // called right after the MQTT socket opens
void     netForceDrop();              // test hook: close the MQTT socket to measure reconnect
Client  &netClient();
const char *netMqttHost();
int      netMqttPort();
const char *netMqttPass();
