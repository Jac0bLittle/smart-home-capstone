#!/usr/bin/env python3
"""Experiment: how long nodes take to come back after a Wi-Fi/broker outage.

Leave this running, then power-cycle the router, restart Mosquitto, or send
"drop" on a node's serial console. It logs every online/offline change and the
nodes' own reconnect_ms / boot_ms reports, and prints each outage's length.

  python3 reconnect_watch.py --csv reconnect_log.csv
"""
import csv
import time

from tb import base_args, connect


def main():
    p = base_args(__doc__)
    p.add_argument("--csv", default=f"reconnect_{time.strftime('%Y%m%d_%H%M%S')}.csv")
    a = p.parse_args()
    offline_at = {}
    f = open(a.csv, "w", newline="")
    w = csv.writer(f)
    w.writerow(["time", "node", "what", "value"])

    def row(node, what, value):
        ts = time.strftime("%H:%M:%S") + f".{int(time.time() * 1000) % 1000:03d}"
        w.writerow([ts, node, what, value])
        f.flush()
        print(f"{ts}  {node:16s} {what:14s} {value}")

    def on_message(cl, userdata, msg):
        parts = msg.topic.split("/")
        node = f"{parts[1]}/{parts[2]}"
        val = msg.payload.decode(errors="replace")
        if parts[-1] == "status":
            if msg.retain:
                row(node, "status(ret)", val)
                return
            if val == "offline":
                offline_at[node] = time.time()
                row(node, "OFFLINE", "")
            elif val == "online":
                gone = time.time() - offline_at.pop(node, time.time())
                row(node, "ONLINE", f"after {gone:.1f} s offline" if gone > 0 else "")
        else:
            row(node, parts[-1], val)

    while True:
        c, ok, rc = connect(a, f"reconnect-watch-{int(time.time())}")
        if ok:
            break
        print(f"broker not reachable (rc {rc}); retrying in 2 s")
        time.sleep(2)
    topics = [("home/+/+/status", 1), ("home/+/+/event/reconnect_ms", 1), ("home/+/+/event/boot_ms", 1)]

    def on_connect(cl, userdata, flags, *rest):      # also re-subscribes after a broker restart
        cl.subscribe(topics)
        row("watcher", "connected", "")

    def on_disconnect(cl, userdata, *rest):
        row("watcher", "disconnected", "broker unreachable")

    c.on_message = on_message
    c.on_connect = on_connect
    c.on_disconnect = on_disconnect
    c.subscribe(topics)
    c.reconnect_delay_set(1, 5)
    print(f"watching (Ctrl+C to stop); log -> {a.csv}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
