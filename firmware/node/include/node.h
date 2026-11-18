// Interface between the shared runtime (main.cpp) and one subsystem file.
#pragma once
#include <Arduino.h>
#include "config.h"

// ---- Provided by main.cpp ----
void pubTele(const char *name, const String &v);    // QoS 0, not retained
void pubState(const char *name, const String &v);   // QoS 1, retained
void pubEvent(const char *name, const String &v);   // QoS 1, not retained
bool mqttUp();
uint32_t hubLostMs();      // 0 while the broker and the hub are both reachable
void nlog(const char *fmt, ...);

// ---- Provided by the node_<sub>.cpp that matches NODE_SUB ----
void nodeSetup();
void nodeLoop(uint32_t now);
void nodeCommand(const String &name, const String &payload);  // cmd/<name>
void nodeRestore(const String &name, const String &payload);  // retained state/<name> after boot
void nodePublishAll();                                        // after every (re)connect
bool nodeSim(const String &line);                             // "temp 28", "motion", ...
void nodePrintStatus();

// ---- Small helpers (avoid min/max macros that differ between cores) ----
static inline float clampf(float v, float lo, float hi) { return v < lo ? lo : (v > hi ? hi : v); }
static inline int clampi(int v, int lo, int hi) { return v < lo ? lo : (v > hi ? hi : v); }
static inline String f1(float v) { return String(v, 1); }
static inline bool isOn(const String &p) { return p == "1" || p == "on" || p == "true"; }
