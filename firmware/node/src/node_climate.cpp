// Climate node: thermostat with hysteresis, fan, and heater safety cut-offs.
// Sim: temperature comes from "sim temp <C>" (or the pot when SIM_POT=1);
// the on-board LED shows the heater.
#include "node.h"
#ifdef NODE_CLIMATE
#include <math.h>
#include "hal.h"

// ---- TUNE ----
static const float HYST_C        = 0.5f;    // ±0.5 °C around the setpoint (Lu et al. / sheet notes)
static const float FAN_ON_ABOVE  = 1.5f;    // fan on when temp > setpoint + 1.5 °C
static const float FAN_OFF_BELOW = 1.0f;    // ... and off again below setpoint + 1.0 °C
static const float MAX_SAFE_C    = 40.0f;   // over-temp cut-off for the model's heater
static const float RESET_BELOW_C = 35.0f;   // over-temp lockout clears below this
static const uint32_t MAX_ON_MS  = 15UL * 60 * 1000;  // heater max continuous on-time
static const uint32_t REST_MS    = 5UL * 60 * 1000;   // rest after a max-on cut-off
static const uint32_t HUB_LOSS_MS = 60000UL;          // manual heater needs a live hub
static const uint32_t TELE_MS    = 30000UL;           // temp_c, humidity_pct
static const uint32_t SLOW_MS    = 60000UL;           // pressure_hpa, gas_kohm

// ---- settings (restored from retained state) ----
static float setpoint = 22.0f;
static String mode = "auto";             // auto / manual / off
// ---- outputs ----
static bool heater = false;
static int fan = 0;
static bool manHeater = false;
static int manFan = 0;
// ---- inputs ----
static float tempC = 22.0f, hum = 40.0f, pressHpa = 1013.2f, gasK = 50.0f;
static bool simTemp = false;
// ---- safety ----
static bool overTemp = false;
static uint32_t heaterOnSince = 0, restUntil = 0;
static bool hubCut = false;
static uint32_t lastTele = 0, lastSlow = 0;

static void readSensors() {
#if SIM_POT
  if (!simTemp) tempC = 15.0f + 20.0f * clampf(halAnalogMv(PIN_POT) / 3100.0f, 0, 1);
#endif
  // Real BME680 read goes here once the sensor is chosen (sheet section 3).
}

static void setHeater(bool on, uint32_t now) {
  if (on == heater) return;
  heater = on;
  if (on) heaterOnSince = now;
  halLed(on ? 100 : 0);
  pubState("heater", on ? "1" : "0");
  nlog("heater %s", on ? "ON" : "off");
}

static void setFan(int pct) {
  pct = clampi(pct, 0, 100);
  if (pct == fan) return;
  fan = pct;
  pubState("fan", String(fan));
}

static void cutoff(const char *reason) {
  pubEvent("heater_cutoff", reason);
  nlog("HEATER CUT-OFF: %s", reason);
}

static void control(uint32_t now) {
  bool want = heater;
  int wantFan = fan;

  if (mode == "off") {
    want = false; wantFan = 0;
  } else if (mode == "auto") {
    if (tempC < setpoint - HYST_C) want = true;
    else if (tempC > setpoint + HYST_C) want = false;
    if (tempC > setpoint + FAN_ON_ABOVE) wantFan = 100;
    else if (tempC < setpoint + FAN_OFF_BELOW) wantFan = 0;
  } else {  // manual: only while the hub is reachable
    want = manHeater; wantFan = manFan;
    if (hubLostMs() > HUB_LOSS_MS) {
      if (!hubCut && (manHeater || heater)) cutoff("hub_lost");
      hubCut = true;
      want = false; wantFan = 0;
    } else {
      hubCut = false;
    }
  }

  // Safety limits apply in every mode.
  if (tempC >= MAX_SAFE_C && !overTemp) { overTemp = true; cutoff("over_temp"); }
  if (overTemp && tempC < RESET_BELOW_C) { overTemp = false; nlog("over-temp lockout cleared"); }
  if (overTemp) { want = false; wantFan = 100; }
  if (heater && want && now - heaterOnSince > MAX_ON_MS) { cutoff("max_on_time"); restUntil = now + REST_MS; }
  if ((int32_t)(restUntil - now) > 0) want = false;

  setHeater(want, now);
  setFan(wantFan);
}

void nodeSetup() {
  halLed(0);
  nlog("climate: setpoint %.1f C, mode %s", setpoint, mode.c_str());
}

void nodeLoop(uint32_t now) {
  static uint32_t lastCtl = 0;
  if (now - lastCtl < 200) return;
  lastCtl = now;
  readSensors();
  control(now);
  if (mqttUp()) {
    if (now - lastTele >= TELE_MS || lastTele == 0) {
      pubTele("temp_c", f1(tempC));
      pubTele("humidity_pct", String((int)lroundf(hum)));
      lastTele = now;
    }
    if (now - lastSlow >= SLOW_MS || lastSlow == 0) {
      pubTele("pressure_hpa", f1(pressHpa));
      pubTele("gas_kohm", f1(gasK));
      lastSlow = now;
    }
  }
}

void nodeCommand(const String &name, const String &p) {
  if (name == "setpoint_c") {
    float v = p.toFloat();
    if (v < 18 || v > 30) { nlog("setpoint %s out of range 18-30", p.c_str()); return; }
    setpoint = roundf(v * 2) / 2;
    pubState("setpoint_c", f1(setpoint));
  } else if (name == "mode") {
    if (p != "auto" && p != "manual" && p != "off") return;
    mode = p;
    if (mode == "manual") { manHeater = heater; manFan = fan; }
    pubState("mode", mode);
  } else if (name == "heater") {
    if (mode != "manual") { nlog("heater command ignored: mode is %s", mode.c_str()); return; }
    manHeater = isOn(p);
  } else if (name == "fan") {
    if (mode != "manual") return;
    manFan = isOn(p) ? 100 : clampi(p.toInt(), 0, 100);
  }
}

void nodeRestore(const String &name, const String &p) {
  // The heater always boots off: manual heater/fan states are not restored.
  if (name == "setpoint_c") { float v = p.toFloat(); if (v >= 18 && v <= 30) setpoint = v; }
  else if (name == "mode" && (p == "auto" || p == "manual" || p == "off")) mode = p;
}

void nodePublishAll() {
  pubState("mode", mode);
  pubState("setpoint_c", f1(setpoint));
  pubState("heater", heater ? "1" : "0");
  pubState("fan", String(fan));
  lastTele = 0; lastSlow = 0;   // send fresh readings now
}

bool nodeSim(const String &line) {
  if (line == "temp auto") { simTemp = false; return true; }
  if (line.startsWith("temp ")) {
    tempC = line.substring(5).toFloat(); simTemp = true;
    pubTele("temp_c", f1(tempC));
    return true;
  }
  if (line.startsWith("hum ")) { hum = line.substring(4).toFloat(); return true; }
  return false;
}

void nodePrintStatus() {
  nlog("climate: temp %.1f C, setpoint %.1f, mode %s, heater %d, fan %d, overTemp %d, hubLost %lus",
       tempC, setpoint, mode.c_str(), heater, fan, overTemp, (unsigned long)(hubLostMs() / 1000));
}

#endif
