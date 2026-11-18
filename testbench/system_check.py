#!/usr/bin/env python3
"""End-to-end check of the node logic over MQTT, using the firmware's sim inputs.

Drives each online node with cmd/sim (fake temperature, motion, door, gas, lux,
sun position) and checks the node's state replies and the hub's alerts. Works
the same against the real ESP32 (built with SIM_INPUTS=1) or the PC build.

  python3 system_check.py                    # every node that is online
  python3 system_check.py --nodes climate    # just one
  python3 system_check.py --no-alerts        # alerter not running

Leaves each node back in its normal mode afterwards. About 1-2 min per node.
"""
import csv
import json
import threading
import time

from tb import SUBS, base_args, connect


class Bus:
    def __init__(self, c):
        self.c, self.msgs, self.last, self.lock = c, [], {}, threading.Lock()
        c.on_message = self.on_message
        c.subscribe("home/#", qos=1)

    def on_message(self, cl, userdata, m):
        with self.lock:
            v = m.payload.decode(errors="replace")
            self.msgs.append((time.time(), m.topic, v))
            self.last[m.topic] = v

    def mark(self):
        return time.time()

    def wait(self, topic, pred=None, timeout=5.0, since=None):
        """Wait for a message on topic (after `since`) whose payload satisfies pred."""
        since = since or 0
        end = time.time() + timeout
        while time.time() < end:
            with self.lock:
                for t, tp, v in self.msgs:
                    if t >= since and tp == topic and (pred is None or pred(v)):
                        return v
            time.sleep(0.05)
        return None

    def pub(self, topic, payload):
        self.c.publish(topic, payload, qos=1)


results = []


def check(node, name, ok, detail=""):
    results.append((node, name, bool(ok), detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail and not ok else ""))
    return ok


def climate(b, alerts):
    P = "home/climate/node1/"
    cmd = lambda n, v: b.pub(P + "cmd/" + n, v)
    sim = lambda v: b.pub(P + "cmd/sim", v)
    cmd("mode", "auto"); cmd("setpoint_c", "22"); sim("temp 22"); time.sleep(1.0)

    def step(temp, expect, label):
        m = b.mark(); sim(f"temp {temp}"); time.sleep(0.8)
        v = b.last.get(P + "state/heater")
        check("climate", f"{label}: {temp} C -> heater {expect}", v == expect, f"heater={v}")

    step(20.0, "1", "below band turns heater on")
    step(22.3, "1", "inside +/-0.5 band keeps it on")
    step(22.6, "0", "above band turns it off")
    step(21.8, "0", "inside band keeps it off")
    step(21.4, "1", "below band again turns it on")
    m = b.mark(); sim("temp 24")
    check("climate", "fan on above setpoint +1.5 C", b.wait(P + "state/fan", lambda v: v == "100", 3, m))
    m = b.mark(); sim("temp 41")
    v = b.wait(P + "event/heater_cutoff", None, 3, m)
    check("climate", "over-temp (41 C) publishes heater_cutoff", v == "over_temp", f"got {v}")
    if alerts:
        a = b.wait("home/hub/jarvis/event/alert", lambda v: "heater" in v.lower() or "temp" in v.lower(), 6, m)
        check("climate", "hub sends over-temp alert", a is not None)
    sim("temp 30"); time.sleep(0.6)
    m = b.mark(); cmd("setpoint_c", "35"); time.sleep(0.8)
    check("climate", "out-of-range setpoint (35) rejected", b.wait(P + "state/setpoint_c", None, 0.5, m) is None)
    m = b.mark(); cmd("setpoint_c", "23.5")
    check("climate", "setpoint 23.5 accepted", b.wait(P + "state/setpoint_c", lambda v: v == "23.5", 3, m))
    # Go manual with the heater off first: sending "temp 22.8" while still in auto
    # can let the node switch the heater on itself, and then "heater 1" changes nothing.
    cmd("mode", "manual"); cmd("heater", "0"); time.sleep(0.5)
    sim("temp 22.8"); time.sleep(0.3)
    m = b.mark(); cmd("heater", "1")
    check("climate", "manual mode: heater command works", b.wait(P + "state/heater", lambda v: v == "1", 3, m))
    m = b.mark(); cmd("heater", "0")
    b.wait(P + "state/heater", lambda v: v == "0", 3, m)
    cmd("mode", "auto"); cmd("setpoint_c", "22"); sim("temp auto")


def alarm(b, alerts):
    P = "home/alarm/node1/"
    cmd = lambda n, v: b.pub(P + "cmd/" + n, v)
    sim = lambda v: b.pub(P + "cmd/sim", v)
    cmd("mode", "disarmed"); sim("door 0"); sim("gas 400"); time.sleep(1)
    m = b.mark(); cmd("mode", "armed")
    check("alarm", "arm command -> state armed", b.wait(P + "state/mode", lambda v: v == "armed", 3, m))
    print("    waiting out the 10 s exit delay ...")
    time.sleep(10.5)
    m = b.mark(); sim("motion")
    check("alarm", "motion event published", b.wait(P + "event/motion", None, 3, m))
    time.sleep(1)
    check("alarm", "one detection alone does not trigger", b.last.get(P + "state/mode") == "armed")
    m = b.mark(); sim("door 1")
    check("alarm", "door open is published", b.wait(P + "state/door", lambda v: v == "1", 3, m))
    check("alarm", "second detection triggers the alarm", b.wait(P + "state/mode", lambda v: v == "triggered", 3, m))
    check("alarm", "buzzer on", b.wait(P + "state/buzzer", lambda v: v == "1", 3, m))
    if alerts:
        a = b.wait("home/hub/jarvis/event/alert", lambda v: "intru" in v.lower(), 6, m)
        check("alarm", "hub sends intruder alert", a is not None)
        if a:
            try:
                check("alarm", "alert record has push_ms", "push_ms" in json.loads(a), a)
            except ValueError:
                check("alarm", "alert record is JSON", False, a)
    m = b.mark(); cmd("silence", "1")
    check("alarm", "silence turns buzzer off", b.wait(P + "state/buzzer", lambda v: v == "0", 3, m))
    m = b.mark(); cmd("mode", "disarmed")
    check("alarm", "disarm", b.wait(P + "state/mode", lambda v: v == "disarmed", 3, m))
    sim("door 0")
    # gas
    ready = b.wait(P + "event/gas_ready", None, 0.2) or b.last.get(P + "tele/gas_raw")
    if not ready:
        print("    waiting for gas sensor warm-up ...")
        b.wait(P + "tele/gas_raw", None, 30)
    m = b.mark(); sim("gas 3000")
    check("alarm", "gas over threshold (3 samples) -> state/gas 1", b.wait(P + "state/gas", lambda v: v == "1", 8, m))
    if alerts:
        check("alarm", "hub sends gas alert", b.wait("home/hub/jarvis/event/alert", lambda v: "gas" in v.lower(), 6, m))
    m = b.mark(); sim("gas 400")
    check("alarm", "gas clears -> state/gas 0", b.wait(P + "state/gas", lambda v: v == "0", 5, m))
    cmd("silence", "1")


def lighting(b, alerts):
    P = "home/lighting/node1/"
    cmd = lambda n, v: b.pub(P + "cmd/" + n, v)
    sim = lambda v: b.pub(P + "cmd/sim", v)
    cmd("mode", "auto"); cmd("lux_threshold", "50"); sim("lux 300"); time.sleep(1.5)
    check("lighting", "bright room: light off", b.last.get(P + "state/power") == "0", b.last.get(P + "state/power"))
    m = b.mark(); sim("lux 20")
    check("lighting", "lux change >10% published early", b.wait(P + "tele/lux", lambda v: v == "20", 3, m))
    time.sleep(0.5)
    check("lighting", "dark but no motion: stays off", b.last.get(P + "state/power") == "0")
    m = b.mark(); sim("motion")
    check("lighting", "dark + motion: light on", b.wait(P + "state/power", lambda v: v == "1", 3, m))
    m = b.mark(); sim("lux 300")
    check("lighting", "bright again: light off", b.wait(P + "state/power", lambda v: v == "0", 3, m))
    m = b.mark(); cmd("power", "1")
    check("lighting", "power command switches to manual", b.wait(P + "state/mode", lambda v: v == "manual", 3, m))
    check("lighting", "manual power on", b.wait(P + "state/power", lambda v: v == "1", 3, m))
    m = b.mark(); cmd("brightness", "40")
    check("lighting", "brightness 40", b.wait(P + "state/brightness", lambda v: v == "40", 3, m))
    m = b.mark(); cmd("color", "#ff8800")
    check("lighting", "color #FF8800", b.wait(P + "state/color", lambda v: v == "#FF8800", 3, m))
    cmd("brightness", "80"); cmd("color", "#FFFFFF"); cmd("mode", "auto")


def solar(b, alerts):
    P = "home/solar/node1/"
    cmd = lambda n, v: b.pub(P + "cmd/" + n, v)
    sim = lambda v: b.pub(P + "cmd/sim", v)
    cmd("mode", "track"); sim("light 1"); sim("sun 150 70")
    ok = b.wait(P + "state/pan_deg", lambda v: abs(int(v) - 150) <= 6, 20)
    check("solar", "tracks sun to pan ~150", ok, b.last.get(P + "state/pan_deg"))
    ok = b.wait(P + "state/tilt_deg", lambda v: abs(int(v) - 70) <= 6, 10)
    check("solar", "tracks sun to tilt ~70", ok, b.last.get(P + "state/tilt_deg"))
    time.sleep(2.5)
    pan1 = b.last.get(P + "state/pan_deg"); time.sleep(2.5)
    check("solar", "holds still inside the dead band", b.last.get(P + "state/pan_deg") == pan1)
    m = b.mark(); sim("sun 175 40")
    ok = b.wait(P + "state/pan_deg", lambda v: int(v) == 170, 20, m)
    check("solar", "stops at travel limit (170)", ok, b.last.get(P + "state/pan_deg"))
    m = b.mark()
    tr = b.wait(P + "tele/panel_mw", None, 7, m)
    ref = b.wait(P + "tele/ref_mw", None, 7, m)
    check("solar", "power telemetry (tracked vs fixed)", tr is not None and ref is not None, f"{tr} vs {ref}")
    m = b.mark(); sim("light 0.05")
    check("solar", "low light -> event/low_light 1 (10 s)", b.wait(P + "event/low_light", lambda v: v == "1", 14, m))
    sim("light 1")
    m = b.mark(); cmd("mode", "park")
    ok = b.wait(P + "state/pan_deg", lambda v: v == "90", 4, m)
    check("solar", "park -> pan 90", ok, b.last.get(P + "state/pan_deg"))
    m = b.mark(); cmd("pan_deg", "30")
    check("solar", "manual pan 30", b.wait(P + "state/pan_deg", lambda v: v == "30", 4, m))
    check("solar", "manual angle switches mode to manual", b.last.get(P + "state/mode") == "manual")
    cmd("mode", "track"); sim("sun sweep")


def main():
    p = base_args(__doc__)
    p.add_argument("--nodes", default="", help="comma list; default = every online node")
    p.add_argument("--no-alerts", action="store_true", help="skip checks that need the alerter")
    p.add_argument("--csv", default=f"system_check_{time.strftime('%Y%m%d_%H%M%S')}.csv")
    a = p.parse_args()
    c, ok, rc = connect(a, f"system-check-{int(time.time())}")
    if not ok:
        raise SystemExit(f"connect failed (rc {rc})")
    b = Bus(c)
    time.sleep(1.0)
    online = [s for s in SUBS if b.last.get(f"home/{s}/node1/status") == "online"]
    wanted = [s for s in a.nodes.split(",") if s] or online
    alerts = not a.no_alerts and b.last.get("home/hub/jarvis/status") == "online"
    print(f"online: {online or 'none'}; testing: {wanted}; hub alerter {'on' if alerts else 'off'}")
    for s in wanted:
        print(f"\n[{s}]")
        if not check(s, "node online", s in online):
            continue
        m = b.mark(); t0 = time.time(); b.pub(f"home/{s}/node1/cmd/ping", "check")
        pong = b.wait(f"home/{s}/node1/event/pong", lambda v: v == "check", 3, m)
        check(s, "ping/pong" + (f" ({(time.time() - t0) * 1000:.0f} ms)" if pong else ""), pong)
        globals()[s](b, alerts)
    c.loop_stop()
    with open(a.csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["node", "check", "result", "detail"])
        for r in results:
            w.writerow([r[0], r[1], "PASS" if r[2] else "FAIL", r[3]])
    failed = [r for r in results if not r[2]]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed  (details: {a.csv})")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
