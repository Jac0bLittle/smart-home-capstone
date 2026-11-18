#!/usr/bin/env python3
"""Hub alert service: turns MQTT states into phone (ntfy) and email alerts.

Rules follow Device Configuration Sheet 6.1. The nodes decide locally when
the alarm is triggered or the heater is cut off (so they work if the hub is
down); this service only notifies people and records each alert on
home/hub/jarvis/event/alert.

  Intruder   home/alarm/node1/state/mode == triggered       -> push + email
  Gas        home/alarm/node1/state/gas == 1                -> push + email
  Offline    any home/+/+/status == offline for > 60 s      -> push
  Over-temp  home/climate/node1/event/heater_cutoff         -> push
  Test       home/hub/jarvis/cmd/test_alert                 -> push + email

Each alert type has a 5-minute cooldown (sheet 6.1); repeats inside the
window are logged but not re-sent. Set DRY_RUN=1 to print instead of send.
"""
import json
import os
import smtplib
import threading
import time
import urllib.request
from email.message import EmailMessage

from hubcommon import connect, load_env, make_client

load_env()
COOLDOWN_S = float(os.environ.get("ALERT_COOLDOWN_S", "300"))
OFFLINE_GRACE_S = float(os.environ.get("OFFLINE_GRACE_S", "60"))
DRY_RUN = os.environ.get("DRY_RUN", "0") == "1"
NTFY_URL = os.environ.get("NTFY_URL", "https://ntfy.sh").rstrip("/")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
EMAIL_TO = [a.strip() for a in os.environ.get("EMAIL_TO", "").split(",") if a.strip()]

HUB_STATUS = "home/hub/jarvis/status"
ALERT_TOPIC = "home/hub/jarvis/event/alert"


def log(msg):
    print(time.strftime("%Y-%m-%d %H:%M:%S"), msg, flush=True)


def send_ntfy(title, message, urgent):
    if not NTFY_TOPIC:
        log("ntfy: NTFY_TOPIC not set, skipped")
        return False
    req = urllib.request.Request(f"{NTFY_URL}/{NTFY_TOPIC}", data=message.encode(), method="POST")
    req.add_header("Title", title)
    req.add_header("Priority", "urgent" if urgent else "default")
    req.add_header("Tags", "rotating_light" if urgent else "house")
    with urllib.request.urlopen(req, timeout=10) as r:
        return 200 <= r.status < 300


def send_email(subject, body):
    if not (SMTP_USER and SMTP_PASS and EMAIL_TO):
        log("email: SMTP_USER/SMTP_PASS/EMAIL_TO not set, skipped")
        return False
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, SMTP_USER, ", ".join(EMAIL_TO)
    msg.set_content(body)
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as s:
        s.starttls()
        s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)
    return True


class Alerter:
    def __init__(self, client):
        self.client = client
        self.last_sent = {}          # alert type -> time sent
        self.offline_timers = {}     # status topic -> Timer
        self.lock = threading.Lock()

    def alert(self, kind, source, message, email=True, urgent=True, t_trigger=None):
        now = time.time()
        with self.lock:
            last = self.last_sent.get(kind, 0)
            if now - last < COOLDOWN_S:
                log(f"suppressed {kind} (cooldown, {COOLDOWN_S - (now - last):.0f} s left): {message}")
                return
            self.last_sent[kind] = now
        # Send outside the MQTT callback thread so HTTP/SMTP delays never block MQTT.
        threading.Thread(target=self._send, args=(kind, source, message, email, urgent, t_trigger or now),
                         daemon=True).start()

    def _send(self, kind, source, message, email, urgent, t_trigger):
        title = f"Smart Home: {kind}"
        sent = []
        try:
            if DRY_RUN:
                log(f"DRY_RUN push: {title} - {message}")
            elif send_ntfy(title, message, urgent):
                sent.append("push")
        except Exception as e:  # keep running if one channel fails
            log(f"ntfy failed: {e}")
        push_ms = (time.time() - t_trigger) * 1000
        if email:
            try:
                if DRY_RUN:
                    log(f"DRY_RUN email: {title} - {message}")
                elif send_email(title, message):
                    sent.append("email")
            except Exception as e:
                log(f"email failed: {e}")
        record = {"type": kind, "source": source, "message": message,
                  "channels": sent, "push_ms": round(push_ms)}
        self.client.publish(ALERT_TOPIC, json.dumps(record), qos=1)
        log(f"ALERT {kind}: {message} (push handed off in {push_ms:.0f} ms, sent: {sent or 'none'})")

    # --- rules ---
    def on_message(self, client, userdata, msg):
        t = time.time()
        topic = msg.topic
        payload = msg.payload.decode("utf-8", "replace").strip()
        parts = topic.split("/")

        if topic == "home/alarm/node1/state/mode" and payload == "triggered" and not msg.retain:
            self.alert("Intruder", "alarm", "Alarm triggered: two detections while armed (door and/or motion).", t_trigger=t)
        elif topic == "home/alarm/node1/state/gas" and payload == "1" and not msg.retain:
            self.alert("Gas detected", "alarm", "Gas sensor over threshold.", t_trigger=t)
        elif topic == "home/climate/node1/event/heater_cutoff":
            self.alert("Heater cutoff", "climate", f"Climate node shut the heater off: {payload}",
                       email=False, urgent=False, t_trigger=t)
        elif topic == "home/hub/jarvis/cmd/test_alert":
            self.alert("Test alert", "hub", f"Test alert requested ({payload or 'no note'}).", t_trigger=t)
        elif len(parts) == 4 and parts[3] == "status" and parts[1] != "hub":
            self.track_status(topic, parts[1], payload)

    def track_status(self, topic, subsystem, payload):
        old = self.offline_timers.pop(topic, None)
        if old:
            old.cancel()
        if payload == "offline":
            timer = threading.Timer(OFFLINE_GRACE_S, self.alert,
                                    args=(f"{subsystem} node offline", subsystem,
                                          f"The {subsystem} node has been offline for over {OFFLINE_GRACE_S:.0f} s."),
                                    kwargs={"email": False, "urgent": False})
            timer.daemon = True
            timer.start()
            self.offline_timers[topic] = timer


def main():
    client = make_client("alerter")
    client.will_set(HUB_STATUS, "offline", qos=1, retain=True)
    alerter = Alerter(client)

    def on_connect(c, userdata, flags, *rest):
        log(f"connected: {rest[0] if rest else 0}")
        c.subscribe([("home/+/+/status", 1), ("home/alarm/node1/state/#", 1),
                     ("home/climate/node1/event/#", 1), ("home/hub/jarvis/cmd/#", 1)])
        c.publish(HUB_STATUS, "online", qos=1, retain=True)

    client.on_connect = on_connect
    client.on_message = alerter.on_message
    connect(client)
    client.loop_forever()


if __name__ == "__main__":
    main()
