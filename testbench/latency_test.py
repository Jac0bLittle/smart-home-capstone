#!/usr/bin/env python3
"""Experiment: round-trip latency hub <-> node over MQTT (QoS 1).

Sends cmd/ping to a node and times the matching event/pong. Reports
min / median / p95 / max and loss, and writes every sample to a CSV.

  python3 latency_test.py --node climate --count 200 --interval 0.5
"""
import csv
import statistics
import threading
import time

from tb import base_args, connect, now_ms


def main():
    p = base_args(__doc__)
    p.add_argument("--node", default="climate", help="climate | alarm | lighting | solar")
    p.add_argument("--count", type=int, default=100)
    p.add_argument("--interval", type=float, default=0.5, help="seconds between pings")
    p.add_argument("--timeout", type=float, default=3.0, help="seconds before a ping counts as lost")
    p.add_argument("--csv", default=None)
    a = p.parse_args()

    base = f"home/{a.node}/node1/"
    sent, rtts, lock = {}, {}, threading.Lock()
    c, ok, rc = connect(a, f"latency-{int(time.time())}")
    if not ok:
        raise SystemExit(f"connect failed (rc {rc})")

    def on_message(cl, userdata, msg):
        t = now_ms()
        seq = msg.payload.decode().split(":")[0]
        with lock:
            if seq in sent and seq not in rtts:
                rtts[seq] = t - sent[seq]

    c.on_message = on_message
    c.subscribe(base + "event/pong", qos=1)
    time.sleep(0.5)
    print(f"pinging {a.node} x{a.count} every {a.interval}s ...")
    for i in range(a.count):
        seq = str(i)
        with lock:
            sent[seq] = now_ms()
        c.publish(base + "cmd/ping", f"{seq}:{int(sent[seq])}", qos=1)
        time.sleep(a.interval)
    time.sleep(a.timeout)
    c.loop_stop()

    vals = [rtts[str(i)] for i in range(a.count) if str(i) in rtts]
    lost = a.count - len(vals)
    fname = a.csv or f"latency_{a.node}_{time.strftime('%Y%m%d_%H%M%S')}.csv"
    with open(fname, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["seq", "rtt_ms"])
        for i in range(a.count):
            w.writerow([i, f"{rtts[str(i)]:.1f}" if str(i) in rtts else "lost"])
    if not vals:
        raise SystemExit(f"no pongs received - is {a.node}-node1 online? (CSV: {fname})")
    vals.sort()
    p95 = vals[min(len(vals) - 1, int(round(0.95 * len(vals))) - 1)]
    print(f"received {len(vals)}/{a.count}  loss {100.0 * lost / a.count:.1f}%")
    print(f"RTT ms  min {vals[0]:.1f}  median {statistics.median(vals):.1f}  "
          f"p95 {p95:.1f}  max {vals[-1]:.1f}")
    print(f"one-way estimate (RTT/2): median {statistics.median(vals) / 2:.1f} ms")
    print(f"samples written to {fname}")


if __name__ == "__main__":
    main()
