"""Shared helpers for the test bench scripts (paho-mqtt 1.6 or 2.x).

Connection settings come from flags or environment variables:
  TB_HOST (default 192.168.0.10), TB_PORT (1883), TB_USER (tester), TB_PASS
If no password is given, the script asks for it.
"""
import argparse
import getpass
import os
import time

import paho.mqtt.client as mqtt

SUBS = ["climate", "alarm", "lighting", "solar"]


def base_args(desc):
    p = argparse.ArgumentParser(description=desc)
    p.add_argument("--host", default=os.environ.get("TB_HOST", "192.168.0.10"))
    p.add_argument("--port", type=int, default=int(os.environ.get("TB_PORT", "1883")))
    p.add_argument("--user", default=os.environ.get("TB_USER", "tester"))
    p.add_argument("--password", default=os.environ.get("TB_PASS"))
    return p


def client(client_id, user, password):
    if hasattr(mqtt, "CallbackAPIVersion"):
        c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id, protocol=mqtt.MQTTv311)
    else:
        c = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
    c.username_pw_set(user, password)
    return c


def connect(args, client_id, will=None):
    """Connect and wait for CONNACK. Returns (client, ok, return_code)."""
    pw = args.password if args.password is not None else getpass.getpass(f"MQTT password for {args.user}: ")
    args.password = pw
    c = client(client_id, args.user, pw)
    result = {}

    def on_connect(cl, userdata, flags, *rest):
        rc = rest[0] if rest else 0
        result["rc"] = int(rc.value if hasattr(rc, "value") else rc)

    c.on_connect = on_connect
    if will:
        c.will_set(*will)
    c.connect(args.host, args.port, keepalive=15)
    c.loop_start()
    t = time.time()
    while "rc" not in result and time.time() - t < 5:
        time.sleep(0.02)
    rc = result.get("rc", -1)
    if rc != 0:
        c.loop_stop()
    return c, rc == 0, rc


def now_ms():
    return time.time() * 1000.0
