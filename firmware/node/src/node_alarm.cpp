// Alarm node: arm/disarm, two-detection confirm before triggering, buzzer,
// MQ-2 gas with warm-up and baseline. The node decides "triggered" itself so the
// alarm still sounds if the hub is down; the hub only sends the alerts.
// Sim: BOOT button or "sim motion" = PIR; "sim door 1/0"; "sim gas <raw>";
// GPIO27/26 also accept the Nano simulator (through a 5 V -> 3.3 V divider).
#include "node.h"
#ifdef NODE_ALARM
#include "hal.h"

// ---- TUNE ----
static const uint32_t EXIT_DELAY_MS   = 10000UL;  // time to leave after arming
static const uint32_t CONFIRM_MS      = 30000UL;  // two detections within this window trigger
static const int      CONFIRM_COUNT   = 2;        // 1 = any single sensor triggers
static const uint32_t MOTION_GAP_MS   = 2000UL;   // PIR re-trigger hold-off
static const uint32_t BUZZER_MAX_MS   = 180000UL; // auto-silence after 3 min
static const uint32_t GAS_WARMUP_MS   = 20000UL;  // sim value; real MQ-2: 60-180 s after power-up
static const int      GAS_DELTA       = 800;      // counts above baseline = gas
static const int      GAS_HYST        = 200;
static const int      GAS_CONFIRM     = 3;        // samples (1 s apart) over threshold
static const uint32_t GAS_TELE_MS     = 10000UL;

static String mode = "disarmed";      // disarmed / armed / triggered
static uint32_t armedAt = 0;
static bool door = false, buzzer = false, gas = false;
static uint32_t buzzerSince = 0;
static uint32_t detections[4] = {0, 0, 0, 0};
static int detIdx = 0;
static uint32_t lastMotion = 0;
static bool lastMotionPin = false, lastBtn = false;
static bool simDoor = false, simMotion = false;
static int gasRaw = 400, gasBase = 0, gasOverCount = 0;
static long gasSum = 0; static int gasN = 0;
static bool gasReady = false;
static uint32_t lastGasSample = 0, lastGasTele = 0;

static void setMode(const String &m) {
  if (m == mode) return;
  mode = m;
  pubState("mode", mode);
  nlog("alarm mode -> %s", mode.c_str());
}

static void setBuzzer(bool on, uint32_t now) {
  if (on == buzzer) return;
  buzzer = on;
  if (on) buzzerSince = now;
  if (!on) halLed(0);
  pubState("buzzer", on ? "1" : "0");
}

static void detection(const char *what, uint32_t now) {
  if (mode != "armed" || now - armedAt < EXIT_DELAY_MS) return;
  detections[detIdx] = now;
  detIdx = (detIdx + 1) % 4;
  int n = 0;
  for (int i = 0; i < 4; i++) if (detections[i] && now - detections[i] <= CONFIRM_MS) n++;
  nlog("detection: %s (%d in window)", what, n);
  if (n >= CONFIRM_COUNT) {
    pubEvent("trigger", what);
    setMode("triggered");
    setBuzzer(true, now);
  }
}

static void readMotion(uint32_t now) {
  bool pin = halDigital(PIN_MOTION);
  bool btn = halBootButton();
  bool edge = (pin && !lastMotionPin) || (btn && !lastBtn) || simMotion;
  lastMotionPin = pin; lastBtn = btn; simMotion = false;
  if (!edge || now - lastMotion < MOTION_GAP_MS) return;
  lastMotion = now;
  pubEvent("motion", "1");
  detection("motion", now);
}

static void readDoor(uint32_t now) {
  static uint32_t changedAt = 0;
  static bool raw = false;
  bool r = halDigital(PIN_DOOR) || simDoor;   // HIGH = open
  if (r != raw) { raw = r; changedAt = now; }
  if (raw != door && now - changedAt >= 50) {  // 50 ms debounce
    door = raw;
    pubState("door", door ? "1" : "0");
    if (door) detection("door", now);
  }
}

static void readGas(uint32_t now) {
  if (now - lastGasSample < 1000) return;
  lastGasSample = now;
#if SIM_POT
  gasRaw = (int)(halAnalogMv(PIN_POT) * 4095L / 3300);
#endif
  if (!gasReady) {                       // warm-up: learn clean-air baseline
    gasSum += gasRaw; gasN++;
    if (now >= GAS_WARMUP_MS) {
      gasBase = (int)(gasSum / (gasN ? gasN : 1));
      gasReady = true;
      nlog("gas baseline %d, threshold %d", gasBase, gasBase + GAS_DELTA);
      pubEvent("gas_ready", String(gasBase));
    }
    return;
  }
  int thr = gasBase + GAS_DELTA;
  if (gasRaw > thr) gasOverCount++; else gasOverCount = 0;
  bool g = gas;
  if (!gas && gasOverCount >= GAS_CONFIRM) g = true;
  if (gas && gasRaw < thr - GAS_HYST) g = false;
  if (g != gas) {
    gas = g;
    pubState("gas", gas ? "1" : "0");
    nlog("GAS %s (raw %d)", gas ? "DETECTED" : "clear", gasRaw);
    if (gas) setBuzzer(true, now);
  }
}

void nodeSetup() {
  halInputPulldown(PIN_MOTION);
  halInputPulldown(PIN_DOOR);
  halLed(0);
}

void nodeLoop(uint32_t now) {
  readMotion(now);
  readDoor(now);
  readGas(now);
  if (buzzer) {
    halLed((now / 150) % 2 ? 100 : 0);  // fast blink = buzzer
    if (now - buzzerSince > BUZZER_MAX_MS) { setBuzzer(false, now); nlog("buzzer auto-silenced"); }
  }
  if (mqttUp() && gasReady && now - lastGasTele >= GAS_TELE_MS) {
    pubTele("gas_raw", String(gasRaw));
    lastGasTele = now;
  }
}

void nodeCommand(const String &name, const String &p) {
  uint32_t now = millis();
  if (name == "mode") {
    if (p == "armed" || p == "arm") {
      armedAt = now;
      for (int i = 0; i < 4; i++) detections[i] = 0;
      setMode("armed");
    } else if (p == "disarmed" || p == "disarm") {
      setMode("disarmed");
      if (!gas) setBuzzer(false, now);
    }
  } else if (name == "silence") {
    if (isOn(p)) setBuzzer(false, now);
  }
}

void nodeRestore(const String &name, const String &p) {
  if (name == "mode") {
    if (p == "armed" || p == "triggered") { mode = "armed"; armedAt = millis(); }
    else if (p == "disarmed") mode = "disarmed";
  }
}

void nodePublishAll() {
  pubState("mode", mode);
  pubState("door", door ? "1" : "0");
  pubState("gas", gas ? "1" : "0");
  pubState("buzzer", buzzer ? "1" : "0");
}

bool nodeSim(const String &line) {
  if (line == "motion") { simMotion = true; return true; }
  if (line == "door 1" || line == "door open") { simDoor = true; return true; }
  if (line == "door 0" || line == "door closed") { simDoor = false; return true; }
  if (line.startsWith("gas ")) { gasRaw = clampi(line.substring(4).toInt(), 0, 4095); return true; }
  return false;
}

void nodePrintStatus() {
  nlog("alarm: mode %s, door %d, gas %d (raw %d, base %d, ready %d), buzzer %d", mode.c_str(), door,
       gas, gasRaw, gasBase, gasReady, buzzer);
}

#endif
