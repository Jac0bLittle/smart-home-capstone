// Smart Home Model - Nano v3 sensor simulator (bench test tool, not in the final build).
//
// Pretends to be the alarm/lighting sensors so the ESP32's real GPIO inputs,
// debouncing and timing can be tested before the parts arrive, and times how
// fast the ESP32 reacts (stimulus -> on-board LED) without any network in the way.
//
// WIRING (Nano is 5 V, ESP32 is 3.3 V: every Nano -> ESP32 line needs a divider,
// e.g. 1 k from the Nano pin to the ESP32 pin and 2 k from the ESP32 pin to GND):
//   Nano D2  --div-->  ESP32 GPIO27   motion (PIR-like 2 s HIGH pulse)
//   Nano D3  --div-->  ESP32 GPIO26   door (HIGH = open)
//   Nano D5  --div--RC->  ESP32 GPIO34   analog level (PWM + 10 k / 10 uF filter), SIM_POT=1
//   Nano D7  <-------  ESP32 GPIO2    ESP32 on-board LED (3.3 V reads HIGH on the Nano)
//   Nano GND  -------  ESP32 GND      (always connect grounds)
//
// SERIAL (115200, newline): ? for help.
#include <Arduino.h>

static const uint8_t PIN_MOTION = 2, PIN_DOOR = 3, PIN_ANALOG = 5, PIN_SENSE = 7, PIN_LED = 13;
static const unsigned long PULSE_MS = 2000;

static bool door = false;
static unsigned long pulseEnd = 0;
static uint8_t analogPct = 0;

// reaction timing
static unsigned long stimAt = 0;
static bool waitingEdge = false, lastSense = false;
static const char *stimName = "";

// scenarios
static uint8_t scenario = 0;
static unsigned long scStart = 0, scLast = 0;
static uint8_t scStep = 0;

static void stimulus(const char *name) {
  stimAt = millis();
  stimName = name;
  waitingEdge = !digitalRead(PIN_SENSE);   // only time a rising edge
}

static void motionPulse() {
  digitalWrite(PIN_MOTION, HIGH);
  digitalWrite(PIN_LED, HIGH);
  pulseEnd = millis() + PULSE_MS;
  Serial.print(F("t=")); Serial.print(millis()); Serial.println(F(" motion pulse"));
  stimulus("motion");
}

static void setDoor(bool open) {
  door = open;
  digitalWrite(PIN_DOOR, open ? HIGH : LOW);
  Serial.print(F("t=")); Serial.print(millis()); Serial.println(open ? F(" door OPEN") : F(" door closed"));
  if (open) stimulus("door");
}

static void setAnalog(int pct) {
  analogPct = constrain(pct, 0, 100);
  analogWrite(PIN_ANALOG, (int)analogPct * 255 / 100);
}

static void help() {
  Serial.println(F("Nano sensor simulator"));
  Serial.println(F("  m        one motion pulse (2 s)"));
  Serial.println(F("  o / c    door open / closed      d  toggle door"));
  Serial.println(F("  a <0-100> analog level in %  (ESP32 SIM_POT=1: temp / gas / lux)"));
  Serial.println(F("  s1  intruder: door open, motion 3 s later, door closes at 15 s"));
  Serial.println(F("  s2  false alarm: one motion pulse every 40 s (alarm must NOT trigger)"));
  Serial.println(F("  s3  walk-by: motion every 5 s, 5 times (lighting hold timer)"));
  Serial.println(F("  s4  dusk: analog 100% -> 0% over 60 s (lighting threshold)"));
  Serial.println(F("  x   stop scenario, all idle      ?  help"));
  Serial.println(F("Reaction time (stimulus -> ESP32 LED on D7) prints as 'react_ms'."));
}

static void startScenario(uint8_t n) {
  scenario = n; scStart = millis(); scLast = 0; scStep = 0;
  Serial.print(F("scenario s")); Serial.print(n); Serial.println(F(" start"));
}

static void runScenario(unsigned long now) {
  unsigned long t = now - scStart;
  switch (scenario) {
    case 1:
      if (scStep == 0) { setDoor(true); scStep = 1; }
      else if (scStep == 1 && t >= 3000) { motionPulse(); scStep = 2; }
      else if (scStep == 2 && t >= 15000) { setDoor(false); scenario = 0; Serial.println(F("s1 done")); }
      break;
    case 2:
      if (scLast == 0 || now - scLast >= 40000UL) { motionPulse(); scLast = now; }
      break;
    case 3:
      if (scLast == 0 || now - scLast >= 5000UL) {
        motionPulse(); scLast = now;
        if (++scStep >= 5) { scenario = 0; Serial.println(F("s3 done")); }
      }
      break;
    case 4: {
      int pct = 100 - (int)(t / 600);
      if (pct <= 0) { setAnalog(0); scenario = 0; Serial.println(F("s4 done")); }
      else if (pct != analogPct) { setAnalog(pct); if (pct % 10 == 0) { Serial.print(F("analog ")); Serial.println(pct); } }
      break;
    }
  }
}

static void command(char *line) {
  while (*line == ' ') line++;
  switch (line[0]) {
    case 'm': motionPulse(); break;
    case 'o': setDoor(true); break;
    case 'c': setDoor(false); break;
    case 'd': setDoor(!door); break;
    case 'a': setAnalog(atoi(line + 1)); Serial.print(F("analog ")); Serial.println(analogPct); break;
    case 's': startScenario((uint8_t)atoi(line + 1)); break;
    case 'x': scenario = 0; setDoor(false); setAnalog(0); Serial.println(F("idle")); break;
    case '?': help(); break;
    case 0: break;
    default: Serial.println(F("? for help"));
  }
}

void setup() {
  pinMode(PIN_MOTION, OUTPUT);
  pinMode(PIN_DOOR, OUTPUT);
  pinMode(PIN_ANALOG, OUTPUT);
  pinMode(PIN_LED, OUTPUT);
  pinMode(PIN_SENSE, INPUT);
  Serial.begin(115200);
  help();
}

void loop() {
  static char buf[24];
  static uint8_t len = 0;
  unsigned long now = millis();

  while (Serial.available()) {
    char ch = Serial.read();
    if (ch == '\r') continue;
    if (ch == '\n') { buf[len] = 0; command(buf); len = 0; }
    else if (len < sizeof(buf) - 1) buf[len++] = ch;
  }
  if (pulseEnd && (long)(now - pulseEnd) >= 0) {
    digitalWrite(PIN_MOTION, LOW);
    digitalWrite(PIN_LED, LOW);
    pulseEnd = 0;
  }
  bool s = digitalRead(PIN_SENSE);
  if (s && !lastSense) {
    if (waitingEdge && now - stimAt < 10000UL) {
      Serial.print(F("react_ms ")); Serial.print(now - stimAt);
      Serial.print(F(" (")); Serial.print(stimName); Serial.println(F(" -> ESP32 LED on)"));
    }
    waitingEdge = false;
  }
  lastSense = s;
  if (scenario) runScenario(now);
}
