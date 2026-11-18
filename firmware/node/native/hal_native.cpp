// PC implementation of hal.h: real TCP sockets to the broker, fake pins.
// Settings come from environment variables:
//   MQTT_HOST (default 127.0.0.1), MQTT_PORT (1883), MQTT_PASS (required)
#include "Arduino.h"   // first: the system socket headers define a conflicting INADDR_NONE macro
#include "hal.h"
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <netdb.h>
#include <netinet/tcp.h>
#include <poll.h>
#include <signal.h>
#include <stdio.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>

// ------------------------------------------------------------ time
static uint64_t t0 = 0;
static uint64_t nowMs() {
  timespec ts; clock_gettime(CLOCK_MONOTONIC, &ts);
  return (uint64_t)ts.tv_sec * 1000 + ts.tv_nsec / 1000000;
}
unsigned long millis() { if (!t0) t0 = nowMs() - 1; return (unsigned long)(uint32_t)(nowMs() - t0); }
unsigned long micros() { return millis() * 1000UL; }
void delay(unsigned long ms) { usleep(ms * 1000); }
void yield() {}
long random(long hi) { return hi ? rand() % hi : 0; }
long random(long lo, long hi) { return lo + random(hi - lo); }
void randomSeed(unsigned long s) { srand(s); }

// ------------------------------------------------------------ serial = stdin/stdout
NativeSerial Serial;
static int peeked = -1;
static bool stdinClosed = false;
int NativeSerial::available() {
  if (peeked >= 0) return 1;
  if (stdinClosed) return 0;
  pollfd p = {0, POLLIN, 0};
  if (poll(&p, 1, 0) <= 0 || !(p.revents & (POLLIN | POLLHUP))) return 0;
  unsigned char c;
  if (::read(0, &c, 1) != 1) { stdinClosed = true; return 0; }   // EOF: run without a console
  peeked = c;
  return 1;
}
int NativeSerial::read() {
  if (!available()) return -1;
  int c = peeked; peeked = -1; return c;
}
int NativeSerial::peek() { return available() ? peeked : -1; }
size_t NativeSerial::write(uint8_t c) { fputc(c, stdout); if (c == '\n') fflush(stdout); return 1; }

// ------------------------------------------------------------ TCP client
class SockClient : public Client {
  int fd = -1;
  int pk = -1;
 public:
  int connect(IPAddress ip, uint16_t port) override { return connect(ip.toString().c_str(), port); }
  int connect(const char *host, uint16_t port) override {
    stop();
    addrinfo hints = {}, *res = nullptr;
    hints.ai_family = AF_INET; hints.ai_socktype = SOCK_STREAM;
    char ps[8]; snprintf(ps, sizeof ps, "%u", port);
    if (getaddrinfo(host, ps, &hints, &res) != 0) return 0;
    fd = socket(res->ai_family, res->ai_socktype, 0);
    int ok = fd >= 0 && ::connect(fd, res->ai_addr, res->ai_addrlen) == 0;
    freeaddrinfo(res);
    if (!ok) { stop(); return 0; }
    int one = 1; setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, &one, sizeof one);
    fcntl(fd, F_SETFL, fcntl(fd, F_GETFL) | O_NONBLOCK);
    return 1;
  }
  size_t write(uint8_t b) override { return write(&b, 1); }
  size_t write(const uint8_t *buf, size_t n) override {
    if (fd < 0) return 0;
    size_t done = 0;
    while (done < n) {
      ssize_t w = ::send(fd, buf + done, n - done, MSG_NOSIGNAL);
      if (w > 0) { done += w; continue; }
      if (w < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) { usleep(500); continue; }
      stop(); break;
    }
    return done;
  }
  int available() override {
    if (fd < 0) return 0;
    if (pk >= 0) return 1;
    unsigned char c; ssize_t r = ::recv(fd, &c, 1, 0);
    if (r == 1) { pk = c; return 1; }
    if (r == 0 || (r < 0 && errno != EAGAIN && errno != EWOULDBLOCK)) stop();
    return 0;
  }
  int read() override { if (!available()) return -1; int c = pk; pk = -1; return c; }
  int read(uint8_t *buf, size_t n) override {
    size_t got = 0;
    while (got < n && available()) buf[got++] = (uint8_t)read();
    return (int)got;
  }
  int peek() override { return available() ? pk : -1; }
  void flush() override {}
  void stop() override { if (fd >= 0) ::close(fd); fd = -1; pk = -1; }
  uint8_t connected() override { if (fd < 0) return 0; if (pk < 0) available(); return fd >= 0; }
  operator bool() override { return fd >= 0; }
};
static SockClient sock;

// ------------------------------------------------------------ fake hardware
static int ledPct = -1;
void halInit() { signal(SIGPIPE, SIG_IGN); setvbuf(stdout, nullptr, _IOLBF, 0); }
bool halBootButton() { return false; }
bool halDigital(int) { return false; }
void halInputPulldown(int) {}
int halAnalogMv(int) { return 0; }
void halLed(int pct) { if (pct != ledPct && (pct == 0 || pct == 100 || ledPct <= 0)) {} ledPct = pct; }
void halServo(int, int) {}
uint32_t halFreeHeap() { return 200000; }

static const char *env(const char *k, const char *d) { const char *v = getenv(k); return v && *v ? v : d; }
void netBegin(const char *) {}
bool netWifiUp() { return true; }
void netWifiRetry() {}
int netRssi() { return -55; }
void netOnConnected() {}
void netForceDrop() { sock.stop(); }
Client &netClient() { return sock; }
const char *netMqttHost() { return env("MQTT_HOST", "127.0.0.1"); }
int netMqttPort() { return atoi(env("MQTT_PORT", "1883")); }
const char *netMqttPass() { return env("MQTT_PASS", ""); }

// ------------------------------------------------------------ entry point
void setup();
void loop();
int main() {
  setup();
  for (;;) { loop(); usleep(2000); }
}
