// Minimal Arduino environment for running node firmware on a PC (Linux/macOS/RPi).
// Uses ArduinoCore-API for String/Print/Stream/Client; see native/build.sh.
#pragma once
#include "api/ArduinoAPI.h"
#include "api/Client.h"
using namespace arduino;

class NativeSerial : public Stream {
 public:
  void begin(unsigned long) {}
  int available() override;
  int read() override;
  int peek() override;
  size_t write(uint8_t c) override;
  using Print::write;
};
extern NativeSerial Serial;
