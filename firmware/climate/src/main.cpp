#include <Arduino.h>
#include "secrets.h"
#include "HomeNet.h"

void setup() {
  Serial.begin(115200);
  homenet::begin();
}

void loop() {
  homenet::loop();
  // Node logic goes here.
}
