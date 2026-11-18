#!/usr/bin/env python3
"""Logs every home/# message to SQLite with a hub timestamp.

Keeps RETENTION_DAYS of history (default 30, sheet section 2) and prunes
older rows once an hour. One row per message, matching the plain
one-value-per-topic format (sheet 4.1).

    python3 mqtt_logger.py            # uses /etc/smarthome/hub.env
    sqlite3 /var/lib/smarthome/log.db "select * from messages order by ts desc limit 20"
"""
import os
import signal
import sqlite3
import threading
import time

from hubcommon import connect, load_env, make_client

load_env()
DB_PATH = os.environ.get("LOG_DB", "/var/lib/smarthome/log.db")
RETENTION_DAYS = float(os.environ.get("RETENTION_DAYS", "30"))
PRUNE_EVERY_S = 3600


def open_db(path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    db = sqlite3.connect(path, check_same_thread=False)
    db.execute("PRAGMA journal_mode=WAL")   # fewer microSD writes, safe reads while logging
    db.execute("""CREATE TABLE IF NOT EXISTS messages (
                    ts REAL NOT NULL, topic TEXT NOT NULL, payload TEXT, retained INTEGER)""")
    db.execute("CREATE INDEX IF NOT EXISTS idx_topic_ts ON messages(topic, ts)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_ts ON messages(ts)")
    db.commit()
    return db


def prune(db):
    cutoff = time.time() - RETENTION_DAYS * 86400
    n = db.execute("DELETE FROM messages WHERE ts < ?", (cutoff,)).rowcount
    db.commit()
    if n:
        print(f"pruned {n} rows older than {RETENTION_DAYS} days", flush=True)


def main():
    db = open_db(DB_PATH)
    pending = []
    lock = threading.Lock()
    last_commit = time.time()
    last_prune = 0.0

    def on_connect(client, userdata, flags, *rest):
        print(f"connected: {rest[0] if rest else 0}", flush=True)
        client.subscribe("home/#", qos=1)

    def on_message(client, userdata, msg):
        row = (time.time(), msg.topic, msg.payload.decode("utf-8", "replace"), int(msg.retain))
        with lock:
            pending.append(row)

    client = make_client("logger")
    client.on_connect = on_connect
    client.on_message = on_message
    connect(client)
    client.loop_start()

    running = True

    def stop(*_):
        nonlocal running
        running = False
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    while running:
        time.sleep(0.5)
        now = time.time()
        # Batch writes every 2 s to spare the microSD card.
        if pending and now - last_commit >= 2:
            with lock:
                rows, pending[:] = pending[:], []
            db.executemany("INSERT INTO messages VALUES (?,?,?,?)", rows)
            db.commit()
            last_commit = now
        if now - last_prune >= PRUNE_EVERY_S:
            prune(db)
            last_prune = now

    client.loop_stop()
    if pending:
        db.executemany("INSERT INTO messages VALUES (?,?,?,?)", pending)
    db.commit()
    db.close()


if __name__ == "__main__":
    main()
