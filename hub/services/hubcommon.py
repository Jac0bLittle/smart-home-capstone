"""Shared helpers for the hub services: settings and the MQTT connection."""
import os
import socket

import paho.mqtt.client as mqtt


def load_env(path=None):
    """Read KEY=VALUE lines from the env file into os.environ (existing values win)."""
    path = path or os.environ.get("SMARTHOME_ENV", "/etc/smarthome/hub.env")
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


def make_client(client_id):
    """MQTT 3.1.1 client using the hub login from the environment.

    Callbacks should accept on_connect(client, userdata, flags, *rest) so they
    work with paho-mqtt 1.6 and 2.x."""
    cid = f"{client_id}-{socket.gethostname()}"
    if hasattr(mqtt, "CallbackAPIVersion"):          # paho-mqtt 2.x (Raspberry Pi OS trixie)
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=cid, protocol=mqtt.MQTTv311)
    else:                                            # paho-mqtt 1.6 (bookworm)
        client = mqtt.Client(client_id=cid, protocol=mqtt.MQTTv311)
    client.username_pw_set(os.environ.get("MQTT_USER", "hub"), os.environ.get("MQTT_PASS", ""))
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    return client


def connect(client):
    client.connect(os.environ.get("MQTT_HOST", "localhost"),
                   int(os.environ.get("MQTT_PORT", "1883")), keepalive=30)
