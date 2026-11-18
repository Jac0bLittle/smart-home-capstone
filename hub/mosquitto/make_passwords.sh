#!/usr/bin/env bash
# Creates one MQTT login per device and saves the hub's own login for the
# logger/alert services. Run on the hub:  sudo ./make_passwords.sh
# Passwords are typed in, never stored in this repo.
set -euo pipefail
PASSWD=/etc/mosquitto/passwd
ENVFILE=/etc/smarthome/hub.env
USERS=(hub climate alarm lighting solar tester)

[[ $EUID -eq 0 ]] || { echo "Run with sudo"; exit 1; }
mkdir -p /etc/smarthome
touch "$PASSWD"

for u in "${USERS[@]}"; do
  while true; do
    read -rsp "Password for MQTT user '$u': " p1; echo
    read -rsp "Repeat: " p2; echo
    [[ -n "$p1" && "$p1" == "$p2" ]] && break
    echo "Empty or did not match, try again."
  done
  mosquitto_passwd -b "$PASSWD" "$u" "$p1"
  if [[ $u == hub ]]; then
    umask 077
    cat > "$ENVFILE" <<ENV
MQTT_HOST=localhost
MQTT_PORT=1883
MQTT_USER=hub
MQTT_PASS=$p1
ENV
  fi
done

chown mosquitto:mosquitto "$PASSWD"; chmod 600 "$PASSWD"
chmod 600 "$ENVFILE"
echo "Done. Restarting Mosquitto..."
systemctl restart mosquitto
echo "Add alert settings (ntfy topic, Gmail) to $ENVFILE - see hub/hub.env.example"
