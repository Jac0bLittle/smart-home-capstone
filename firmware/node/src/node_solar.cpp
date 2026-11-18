// Solar tracker node: four LDRs behind a cross-shaped shade divider; the node
// turns pan/tilt toward the brighter side, with a dead band, step limit, travel
// limits and a low-light hold/park (Weissbach [19], Guo [18], Chenchireddy notes).
// Sim (SIM_INPUTS=1): a virtual sun lights virtual LDRs, so the control loop and
// the tracked-vs-fixed power chart work on a bare board. Servo PWM still goes to
// GPIO18/19, so real servos can be plugged in to watch them move.
#include "node.h"
#ifdef NODE_SOLAR
#include <math.h>
#include "hal.h"

// ---- TUNE ----
static const float    DEAD_BAND   = 0.05f;  // ignore < 5 % left/right imbalance
static const float    GAIN_DEG    = 20.0f;  // degrees per unit imbalance, per step
static const float    MAX_STEP    = 2.0f;   // degrees per control step
static const uint32_t STEP_MS     = 100UL;  // control loop period
static const int      LOW_LIGHT   = 600;    // sum of 4 LDRs (0-16380) below = too dark to track
static const uint32_t LOW_HOLD_MS = 10000UL;// dark this long -> hold
static const uint32_t PARK_MS     = 60000UL;// dark this long -> park
static const int PAN_MIN = 10, PAN_MAX = 170, TILT_MIN = 10, TILT_MAX = 90;
static const int PARK_PAN = 90, PARK_TILT = 45;
static const float FIXED_AZ = 90, FIXED_EL = 45;   // reference panel orientation
static const float PMAX_MW = 500;                  // sim: full-sun panel power
static const uint32_t TELE_MS = 5000UL;

static String mode = "track";          // track / park / manual
static float pan = 90, tilt = 45;
static int panSent = -1, tiltSent = -1;
static uint32_t lastAnglePub = 0, lastStep = 0, lastTele = 0, darkSince = 0;
static bool lowLight = false;
static int ldr[4];                     // TL, TR, BL, BR (0-4095)

// virtual sun
static float sunAz = 120, sunEl = 50, light = 1.0f;
static bool sweep = false;
static uint32_t sweepStart = 0;

static float rad(float d) { return d * 0.0174533f; }

static void readLdrs(uint32_t now) {
#if SIM_INPUTS
  if (sweep) {   // 30 -> 150 deg azimuth over 5 minutes, elevation arcs 20 -> 60 -> 20
    float t = ((now - sweepStart) % 300000UL) / 300000.0f;
    sunAz = 30 + 120 * t;
    sunEl = 20 + 40 * sinf(3.14159f * t);
  }
  float dP = clampf(sinf(rad(sunAz - pan)) * 1.5f, -0.9f, 0.9f);   // + = sun to the right
  float dT = clampf(sinf(rad(sunEl - tilt)) * 1.5f, -0.9f, 0.9f);  // + = sun higher
  float base = 3000.0f * light;
  ldr[0] = (int)(base * (1 - dP) * (1 + dT) / 1.9f);
  ldr[1] = (int)(base * (1 + dP) * (1 + dT) / 1.9f);
  ldr[2] = (int)(base * (1 - dP) * (1 - dT) / 1.9f);
  ldr[3] = (int)(base * (1 + dP) * (1 - dT) / 1.9f);
#else
  // Real LDR dividers on ADC1 pins (0.2-1.9 V usable window, sheet section 3).
  static const int pins[4] = {32, 33, 35, 39};
  for (int i = 0; i < 4; i++) ldr[i] = halAnalogMv(pins[i]) * 4095L / 3300;
#endif
}

static void moveTo(float p, float t) {
  pan = clampf(p, PAN_MIN, PAN_MAX);
  tilt = clampf(t, TILT_MIN, TILT_MAX);
  halServo(0, (int)lroundf(pan));
  halServo(1, (int)lroundf(tilt));
}

static void track(uint32_t now) {
  long sum = (long)ldr[0] + ldr[1] + ldr[2] + ldr[3];
  if (sum < LOW_LIGHT) {
    if (!darkSince) darkSince = now;
    uint32_t d = now - darkSince;
    if (d > LOW_HOLD_MS && !lowLight) { lowLight = true; pubEvent("low_light", "1"); }
    if (d > PARK_MS) moveTo(PARK_PAN, PARK_TILT);
    return;
  }
  if (lowLight) { lowLight = false; pubEvent("low_light", "0"); }
  darkSince = 0;
  float right = ldr[1] + ldr[3], left = ldr[0] + ldr[2];
  float top = ldr[0] + ldr[1], bottom = ldr[2] + ldr[3];
  float ePan = (right - left) / (right + left);
  float eTilt = (top - bottom) / (top + bottom);
  float sp = fabsf(ePan) < DEAD_BAND ? 0 : clampf(ePan * GAIN_DEG, -MAX_STEP, MAX_STEP);
  float st = fabsf(eTilt) < DEAD_BAND ? 0 : clampf(eTilt * GAIN_DEG, -MAX_STEP, MAX_STEP);
  if (sp != 0 || st != 0) moveTo(pan + sp, tilt + st);
}

#if SIM_INPUTS
static float panelMw(float az, float el) {
  float c = cosf(rad(sunAz - az)) * cosf(rad(sunEl - el));
  return c > 0 ? PMAX_MW * light * c : 0;
}
#endif

void nodeSetup() { moveTo(pan, tilt); }

void nodeLoop(uint32_t now) {
  if (now - lastStep >= STEP_MS) {
    lastStep = now;
    readLdrs(now);
    if (mode == "track") track(now);
    else if (mode == "park") moveTo(PARK_PAN, PARK_TILT);
  }
  int p = (int)lroundf(pan), t = (int)lroundf(tilt);
  if ((p != panSent || t != tiltSent) && now - lastAnglePub >= 1000) {   // on change, max 1/s
    if (p != panSent) pubState("pan_deg", String(p));
    if (t != tiltSent) pubState("tilt_deg", String(t));
    panSent = p; tiltSent = t; lastAnglePub = now;
  }
  if (mqttUp() && now - lastTele >= TELE_MS) {
    lastTele = now;
#if SIM_INPUTS
    float mw = panelMw(pan, tilt), ref = panelMw(FIXED_AZ, FIXED_EL);
    pubTele("panel_mw", String((int)lroundf(mw)));
    pubTele("panel_v", String(mw > 0 ? 5.0f : 0.0f, 2));
    pubTele("panel_ma", f1(mw / 5.0f));
    pubTele("ref_mw", String((int)lroundf(ref)));
#endif
    // Real INA219 readings (tracking + reference panel) go here.
  }
}

void nodeCommand(const String &name, const String &p) {
  if (name == "mode") {
    if (p != "track" && p != "park" && p != "manual") return;
    mode = p;
    pubState("mode", mode);
  } else if (name == "pan_deg" || name == "tilt_deg") {
    if (mode != "manual") { mode = "manual"; pubState("mode", mode); }
    if (name == "pan_deg") moveTo(p.toFloat(), tilt);
    else moveTo(pan, p.toFloat());
  }
}

void nodeRestore(const String &name, const String &p) {
  if (name == "mode" && (p == "track" || p == "park" || p == "manual")) mode = p;
  else if (name == "pan_deg") moveTo(p.toFloat(), tilt);
  else if (name == "tilt_deg") moveTo(pan, p.toFloat());
}

void nodePublishAll() {
  pubState("mode", mode);
  panSent = tiltSent = -1;
  lastAnglePub = 0;
  lastTele = 0;
}

bool nodeSim(const String &line) {
  if (line == "sun sweep") { sweep = true; sweepStart = millis(); return true; }
  if (line.startsWith("sun ")) {          // "sun <az> <el>"
    int sp = line.indexOf(' ', 4);
    if (sp < 0) return false;
    sweep = false;
    sunAz = line.substring(4, sp).toFloat();
    sunEl = line.substring(sp + 1).toFloat();
    return true;
  }
  if (line.startsWith("light ")) { light = clampf(line.substring(6).toFloat(), 0, 1); return true; }
  return false;
}

void nodePrintStatus() {
  nlog("solar: mode %s, pan %.1f tilt %.1f, sun %.0f/%.0f light %.2f, LDR %d %d %d %d, lowLight %d",
       mode.c_str(), pan, tilt, sunAz, sunEl, light, ldr[0], ldr[1], ldr[2], ldr[3], lowLight);
}

#endif
