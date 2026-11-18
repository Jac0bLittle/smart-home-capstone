// Lighting node: auto mode turns the light on when it is dark and someone moved
// recently (hold timer); manual mode follows the dashboard.
// Sim: "sim lux <n>", BOOT button or "sim motion"; LED brightness = light level.
#include "node.h"
#ifdef NODE_LIGHTING
#include <math.h>
#include "hal.h"

// ---- TUNE ----
static const uint32_t HOLD_MS        = 120000UL; // stay on 2 min after the last motion
static const bool     NEED_MOTION    = true;     // false = auto is light-level only
static const float    DARK_HYST      = 1.10f;    // "light" again above threshold x 1.1
static const uint32_t LUX_TELE_MS    = 10000UL;
static const float    LUX_CHANGE     = 0.10f;    // publish early on >10 % change
static const uint32_t LUX_MIN_GAP_MS = 1000UL;
static const uint32_t MOTION_GAP_MS  = 2000UL;

static bool power = false;
static int brightness = 80;
static String color = "#FFFFFF";
static String mode = "auto";
static int luxThreshold = 50;
static float lux = 300.0f, luxSent = -1;
static bool dark = false;
static uint32_t lastMotion = 0, lastLuxPub = 0;
static bool everMotion = false, lastBtn = false, lastPin = false, simMotion = false;

static void apply() { halLed(power ? brightness : 0); }   // WS2812 driver goes here later

static void setPower(bool on) {
  if (on == power) return;
  power = on;
  apply();
  pubState("power", on ? "1" : "0");
  nlog("light %s", on ? "ON" : "off");
}

static void toManual() {
  if (mode == "manual") return;
  mode = "manual";
  pubState("mode", mode);
}

static void readInputs(uint32_t now) {
#if SIM_POT
  lux = 1000.0f * clampf(halAnalogMv(PIN_POT) / 3100.0f, 0, 1);
#endif
  bool pin = halDigital(PIN_MOTION), btn = halBootButton();
  bool edge = (pin && !lastPin) || (btn && !lastBtn) || simMotion;
  lastPin = pin; lastBtn = btn; simMotion = false;
  if (edge && (!everMotion || now - lastMotion >= MOTION_GAP_MS)) {
    lastMotion = now; everMotion = true;
    pubEvent("motion", "1");
  }
  if (!dark && lux < luxThreshold) dark = true;
  else if (dark && lux > luxThreshold * DARK_HYST) dark = false;
}

void nodeSetup() {
  halInputPulldown(PIN_MOTION);
  apply();
}

void nodeLoop(uint32_t now) {
  readInputs(now);
  if (mode == "auto") {
    bool recent = everMotion && now - lastMotion < HOLD_MS;
    setPower(dark && (recent || !NEED_MOTION));
  }
  if (mqttUp()) {
    bool big = luxSent < 0 || fabsf(lux - luxSent) > LUX_CHANGE * (luxSent > 20 ? luxSent : 20);
    if (now - lastLuxPub >= LUX_TELE_MS || (big && now - lastLuxPub >= LUX_MIN_GAP_MS)) {
      pubTele("lux", String((int)lroundf(lux)));
      luxSent = lux; lastLuxPub = now;
    }
  }
}

void nodeCommand(const String &name, const String &p) {
  if (name == "mode") {
    if (p != "auto" && p != "manual") return;
    mode = p;
    pubState("mode", mode);
  } else if (name == "power") {
    toManual();
    setPower(isOn(p));
  } else if (name == "brightness") {
    brightness = clampi(p.toInt(), 0, 100);
    apply();
    pubState("brightness", String(brightness));
  } else if (name == "color") {
    if (p.length() != 7 || p[0] != '#') return;
    color = p; color.toUpperCase();
    pubState("color", color);
  } else if (name == "lux_threshold") {
    luxThreshold = clampi(p.toInt(), 0, 1000);
    pubState("lux_threshold", String(luxThreshold));
  }
}

void nodeRestore(const String &name, const String &p) {
  if (name == "brightness") brightness = clampi(p.toInt(), 0, 100);
  else if (name == "color" && p.length() == 7) color = p;
  else if (name == "mode" && (p == "auto" || p == "manual")) mode = p;
  else if (name == "lux_threshold") luxThreshold = clampi(p.toInt(), 0, 1000);
  else if (name == "power" && mode == "manual") power = isOn(p);
  apply();
}

void nodePublishAll() {
  pubState("mode", mode);
  pubState("power", power ? "1" : "0");
  pubState("brightness", String(brightness));
  pubState("color", color);
  pubState("lux_threshold", String(luxThreshold));
  luxSent = -1;
}

bool nodeSim(const String &line) {
  if (line == "motion") { simMotion = true; return true; }
  if (line.startsWith("lux ")) { lux = line.substring(4).toFloat(); return true; }
  return false;
}

void nodePrintStatus() {
  nlog("lighting: mode %s, power %d, brightness %d, color %s, lux %.0f (thr %d, dark %d), last motion %lus ago",
       mode.c_str(), power, brightness, color.c_str(), lux, luxThreshold, dark,
       (unsigned long)(everMotion ? (millis() - lastMotion) / 1000 : 0));
}

#endif
