// Smart Home Model - shared node runtime.
// Wi-Fi + MQTT with backoff, Last Will, heartbeat, ping/pong for latency tests,
// reconnect timing, and restoring settings from the node's own retained state.
// The subsystem logic lives in node_<sub>.cpp.

#include <Arduino.h>
#include <MQTT.h>
#include <stdarg.h>
#include "config.h"
#include "hal.h"
#include "node.h"

static MQTTClient mqtt(MQTT_BUF_BYTES);

// Messages are queued in the callback and handled in loop(): the MQTT library
// does not allow publishing from inside its own callback.
struct Msg { String topic; String payload; };
static const int QLEN = 16;
static Msg queue[QLEN];
static int qHead = 0, qTail = 0;
static uint32_t qDropped = 0;

static uint32_t bootMs = 0;
static uint32_t lastWifiTry = 0, wifiBackoff = WIFI_RETRY_MIN_MS;
static uint32_t lastMqttTry = 0, mqttBackoff = MQTT_RETRY_MIN_MS;   // first try is immediate (see setup)
static uint32_t downSince = 0;        // when the link was first seen down (0 = up)
static uint32_t lostSince = 0;        // when broker-or-hub was first seen missing (0 = fine)
static uint32_t reconnects = 0;
static bool everConnected = false;
static bool hubUp = false;
static bool restoring = false, restored = false;
static uint32_t restoreUntil = 0;
static uint32_t lastBeat = 0, lastSlow = 0;
static bool wasUp = false;

// ---------------------------------------------------------------- logging
void nlog(const char *fmt, ...) {
  char buf[160];
  va_list ap;
  va_start(ap, fmt);
  vsnprintf(buf, sizeof(buf), fmt, ap);
  va_end(ap);
  Serial.print("[");
  Serial.print(millis() / 1000.0, 1);
  Serial.print("] ");
  Serial.println(buf);
}

// ---------------------------------------------------------------- publish helpers
static bool pub(const String &topic, const String &v, bool retain, int qos) {
  if (!mqtt.connected()) return false;
  bool ok = mqtt.publish(topic, v, retain, qos);
  if (!ok) nlog("publish failed %s (err %d)", topic.c_str(), (int)mqtt.lastError());
  return ok;
}
void pubTele(const char *name, const String &v)  { pub(String(TOPIC_PREFIX "tele/") + name, v, false, 0); }
void pubState(const char *name, const String &v) { pub(String(TOPIC_PREFIX "state/") + name, v, true, 1); }
void pubEvent(const char *name, const String &v) { pub(String(TOPIC_PREFIX "event/") + name, v, false, 1); }
bool mqttUp() { return mqtt.connected(); }

uint32_t hubLostMs() { return lostSince ? millis() - lostSince : 0; }

static void updateLost() {
  bool ok = mqtt.connected() && hubUp;
  if (ok) lostSince = 0;
  else if (!lostSince) lostSince = millis() ? millis() : 1;
}

// ---------------------------------------------------------------- inbound
static void onMessage(String &topic, String &payload) {
  int next = (qHead + 1) % QLEN;
  if (next == qTail) { qTail = (qTail + 1) % QLEN; qDropped++; }   // drop oldest
  queue[qHead].topic = topic;
  queue[qHead].payload = payload;
  qHead = next;
}

static void publishHeartbeat(bool slowToo) {
  pubTele("uptime_s", String((millis() - bootMs) / 1000));
  if (slowToo) {
    pubTele("rssi_dbm", String(netRssi()));
    pubTele("free_heap", String(halFreeHeap()));
  }
}

static void handle(const String &topic, const String &payload) {
  static const String pre = TOPIC_PREFIX;
  if (topic == HUB_STATUS_TOPIC) {
    hubUp = (payload == "online");
    nlog("hub is %s", payload.c_str());
    return;
  }
  if (!topic.startsWith(pre)) return;
  String rest = topic.substring(pre.length());

  if (rest.startsWith("state/")) {          // our own retained state, only read once after boot
    if (restoring) {
      String name = rest.substring(6);
      nlog("restore %s = %s", name.c_str(), payload.c_str());
      nodeRestore(name, payload);
    }
    return;
  }
  if (!rest.startsWith("cmd/")) return;
  String name = rest.substring(4);

  if (name == "ping") {                     // latency test: echo straight back
    pubEvent("pong", payload);
    return;
  }
  if (name == "publish_all") { nodePublishAll(); publishHeartbeat(true); return; }
#if SIM_INPUTS
  if (name == "sim") {
    if (payload == "drop") { netForceDrop(); return; }
    if (!nodeSim(payload)) nlog("unknown sim command: %s", payload.c_str());
    return;
  }
#endif
  nlog("cmd %s = %s", name.c_str(), payload.c_str());
  nodeCommand(name, payload);
}

static void drainQueue() {
  while (qTail != qHead) {
    Msg m = queue[qTail];
    qTail = (qTail + 1) % QLEN;
    handle(m.topic, m.payload);
  }
}

// ---------------------------------------------------------------- connection
static void markDown(uint32_t now) {
  if (wasUp) nlog("link down (wifi %s)", netWifiUp() ? "up" : "down");
  wasUp = false;
  if (!downSince) downSince = now ? now : 1;
}

static void tryMqtt(uint32_t now) {
  lastMqttTry = now;
  nlog("MQTT connect to %s:%d as %s ...", netMqttHost(), netMqttPort(), NODE_SUB);
  if (!mqtt.connect(CLIENT_ID, NODE_SUB, netMqttPass())) {
    nlog("MQTT connect failed: err %d, rc %d; retry in %lu ms", (int)mqtt.lastError(),
         (int)mqtt.returnCode(), (unsigned long)mqttBackoff);
    mqttBackoff = mqttBackoff * 2 > MQTT_RETRY_MAX_MS ? MQTT_RETRY_MAX_MS : mqttBackoff * 2;
    return;
  }
  netOnConnected();
  mqttBackoff = MQTT_RETRY_MIN_MS;
  wasUp = true;
  pub(TOPIC_PREFIX "status", "online", true, 1);
  mqtt.subscribe(TOPIC_PREFIX "cmd/#", 1);
  mqtt.subscribe(HUB_STATUS_TOPIC, 1);

  uint32_t t = millis();
  if (everConnected && downSince) {
    reconnects++;
    pubEvent("reconnect_ms", String(t - downSince));
    nlog("reconnected after %lu ms (#%lu)", (unsigned long)(t - downSince), (unsigned long)reconnects);
  } else {
    nlog("connected %lu ms after boot", (unsigned long)(t - bootMs));
    pubEvent("boot_ms", String(t - bootMs));
  }
  everConnected = true;
  downSince = 0;

  if (!restored) {          // first connect since boot: read back our last settings
    restoring = true;
    restoreUntil = t + RESTORE_WINDOW_MS;
    mqtt.subscribe(TOPIC_PREFIX "state/#", 1);
  } else {
    nodePublishAll();
  }
  publishHeartbeat(true);
  pubTele("reconnects", String(reconnects));
}

static void serviceLink(uint32_t now) {
  if (!netWifiUp()) {
    markDown(now);
    if (now - lastWifiTry >= wifiBackoff) {
      lastWifiTry = now;
      nlog("Wi-Fi retry (next in %lu ms)", (unsigned long)wifiBackoff);
      netWifiRetry();
      wifiBackoff = wifiBackoff * 2 > WIFI_RETRY_MAX_MS ? WIFI_RETRY_MAX_MS : wifiBackoff * 2;
    }
    return;
  }
  wifiBackoff = WIFI_RETRY_MIN_MS;
  if (!mqtt.connected()) {
    markDown(now);
    if (now - lastMqttTry >= mqttBackoff) tryMqtt(now);
    return;
  }
  mqtt.loop();
}

// ---------------------------------------------------------------- serial console
static void serialConsole() {
  static String line;
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\r') continue;
    if (c != '\n') { if (line.length() < 80) line += c; continue; }
    line.trim();
    if (line == "status") {
      nlog("%s wifi=%d mqtt=%d hub=%d rssi=%d reconnects=%lu dropped=%lu heap=%lu", CLIENT_ID,
           netWifiUp(), mqtt.connected(), hubUp, netRssi(), (unsigned long)reconnects,
           (unsigned long)qDropped, (unsigned long)halFreeHeap());
      nodePrintStatus();
    } else if (line == "drop") {
      netForceDrop();
#if SIM_INPUTS
    } else if (line.startsWith("sim ")) {
      if (!nodeSim(line.substring(4))) nlog("unknown sim command");
#endif
    } else if (line.length()) {
      nlog("commands: status | drop | sim <...>  (see README)");
    }
    line = "";
  }
}

// ---------------------------------------------------------------- setup / loop
void setup() {
  Serial.begin(115200);
  bootMs = millis();
  halInit();
  nlog("Smart Home node %s starting", CLIENT_ID);
  nodeSetup();
  netBegin(CLIENT_ID);
  mqtt.begin(netMqttHost(), netMqttPort(), netClient());
  mqtt.setKeepAlive(MQTT_KEEPALIVE_S);
  mqtt.setCleanSession(true);
  mqtt.setTimeout(MQTT_TIMEOUT_MS);
  mqtt.setWill(TOPIC_PREFIX "status", "offline", true, 1);
  mqtt.onMessage(onMessage);
  downSince = millis() ? millis() : 1;
  lostSince = downSince;
  lastMqttTry = millis() - MQTT_RETRY_MIN_MS;   // try the broker on the first loop
}

void loop() {
  uint32_t now = millis();
  serialConsole();
  serviceLink(now);
  drainQueue();
  updateLost();

  if (restoring && (int32_t)(millis() - restoreUntil) >= 0) {
    restoring = false;
    restored = true;
    mqtt.unsubscribe(TOPIC_PREFIX "state/#");
    nodePublishAll();
  }

  if (!restoring) nodeLoop(millis());   // hold control for the 1.5 s restore window

  if (mqtt.connected()) {
    now = millis();
    if (now - lastBeat >= HEARTBEAT_MS) {
      bool slow = now - lastSlow >= SLOW_TELE_MS;
      publishHeartbeat(slow);
      lastBeat = now;
      if (slow) lastSlow = now;
    }
  }
}
