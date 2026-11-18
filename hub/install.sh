#!/usr/bin/env bash
# Smart Home hub setup for Raspberry Pi OS Lite 64-bit (Experiments 1-5).
# Run from this folder on the Pi:   sudo ./install.sh
# Safe to run again; it only adds or updates files.
set -euo pipefail
cd "$(dirname "$0")"
[[ $EUID -eq 0 ]] || { echo "Run with sudo"; exit 1; }
PI_USER=${SUDO_USER:-pi}

echo "== 1/6 Packages"
apt-get update
apt-get install -y mosquitto mosquitto-clients python3-paho-mqtt sqlite3 avahi-daemon curl

echo "== 2/6 Mosquitto config, ACL"
install -m 644 mosquitto/smarthome.conf /etc/mosquitto/conf.d/smarthome.conf
install -m 600 -o mosquitto -g mosquitto mosquitto/smarthome.acl /etc/mosquitto/smarthome.acl
if [[ ! -s /etc/mosquitto/passwd || ! -f /etc/smarthome/hub.env ]]; then
  echo "No MQTT logins yet - creating them now."
  bash ./mosquitto/make_passwords.sh
fi
systemctl enable --now mosquitto
systemctl restart mosquitto

echo "== 3/6 Hub services (logger + alerter)"
id smarthome &>/dev/null || useradd --system --no-create-home --shell /usr/sbin/nologin smarthome
mkdir -p /opt/smarthome/services /var/lib/smarthome /etc/smarthome
install -m 644 services/*.py /opt/smarthome/services/
chown smarthome:smarthome /var/lib/smarthome
# Services read hub.env; let the smarthome user read it but nobody else.
chgrp smarthome /etc/smarthome/hub.env && chmod 640 /etc/smarthome/hub.env
grep -q '^NTFY_TOPIC' /etc/smarthome/hub.env || sed -n '/^# Logger/,$p' hub.env.example >> /etc/smarthome/hub.env
install -m 644 systemd/smarthome-*.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now smarthome-logger smarthome-alerter

echo "== 4/6 Node-RED (official installer, runs as $PI_USER)"
if ! command -v node-red >/dev/null; then
  sudo -u "$PI_USER" bash -c 'bash <(curl -sL https://github.com/node-red/linux-installers/releases/latest/download/install-update-nodered-deb) --confirm-install --confirm-pi --no-init'
fi
systemctl enable nodered

echo "== 5/6 FlowFuse Dashboard 2.0"
sudo -u "$PI_USER" bash -c 'mkdir -p ~/.node-red && cd ~/.node-red && npm install --no-fund --no-audit @flowfuse/node-red-dashboard'
systemctl restart nodered

echo "== 6/6 Checks"
systemctl --no-pager --lines=0 status mosquitto smarthome-logger smarthome-alerter nodered || true
free -h
echo
echo "Next:"
echo "  - Open http://$(hostname).local:1880 and import nodered/flows.json (Menu > Import)."
echo "  - Double-click the 'jarvis broker' config node and enter the hub MQTT password."
echo "  - Dashboard: http://$(hostname).local:1880/dashboard"
echo "  - Edit /etc/smarthome/hub.env for ntfy/Gmail, then: sudo systemctl restart smarthome-alerter"
