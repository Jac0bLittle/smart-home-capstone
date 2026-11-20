from blocks import *
def draw(fn):
    f, ax = fig(16, 10)
    ax.text(0.3, 9.7, 'Hub and network', fontsize=18, va='top')
    ax.text(0.3, 9.25, 'Isolated project LAN 192.168.0.0/24. All MQTT traffic stays local (Mosquitto on the Pi); the internet uplink is only for installs and phone alerts.', fontsize=10, color='#555', va='top')
    rt = box(ax, 6.2, 5.0, 3.4, 1.5, 'TP-Link Archer AX10', 'router 192.168.0.1\n2.4 GHz SSID, WPA2-AES\nband steering off', fc='#e8f5e9', fs=11)
    pi = box(ax, 6.0, 1.0, 3.8, 2.4, 'Raspberry Pi 5 4 GB  "jarvis"', '192.168.0.10 (DHCP reservation)\nPi OS Lite 64-bit, 64 GB microSD\nMosquitto :1883 (per-device logins, ACL)\nNode-RED :1880 + /dashboard\nSQLite logger · alerter (ntfy) · voice', fc='#e3f2fd', fs=11)
    line(ax, [rt['b'], pi['t']], NET, lw=3, label='Cat6 Ethernet (LAN port)', loff=(1.3, 0), fs=9)
    # Pi peripherals
    jab = box(ax, 11.2, 2.55, 3.0, 0.8, 'Jabra Speak 510', 'USB-A: mic + speaker (voice)', fc='#fff8e1', fs=10)
    clr = box(ax, 11.2, 1.6, 3.0, 0.7, 'Active Cooler', 'FAN header', fc='#fff8e1', fs=10)
    rtc = box(ax, 11.2, 0.7, 3.0, 0.7, 'RTC battery', 'BAT connector (keeps time)', fc='#fff8e1', fs=10)
    for b in (jab, clr, rtc): line(ax, [(pi['x']+pi['w'], b['l'][1]), b['l']], USB, lw=1.8)
    ps = box(ax, 1.2, 1.7, 3.0, 0.9, 'Pi 27 W USB-C PSU', '5.1 V 5 A', fc='#ffebee', fs=10)
    line(ax, [ps['r'], (pi['x'], ps['r'][1])], RED, lw=2, label='USB-C power', fs=8)
    # WAN
    wan = box(ax, 6.7, 7.6, 2.4, 0.9, 'Internet (optional)', 'installs, ntfy push', fc='#fafafa', fs=10)
    line(ax, [wan['b'], rt['t']], '#777', lw=2, ls='--', label='WAN port', loff=(0.6, -0.1), fs=8)
    # nodes
    nodes = [('Climate node', 'climate-node1'), ('Alarm node', 'alarm-node1'), ('Lighting node', 'lighting-node1'), ('Solar node', 'solar-node1')]
    for i, (t, cid) in enumerate(nodes):
        y = 7.5 - i*1.25
        b = box(ax, 12.0, y, 3.4, 0.95, t, f'ESP32 · client ID {cid}\nlogin: home/{cid.split("-")[0]}/# only', fc='#fffde7', fs=10)
        line(ax, [(rt['x']+rt['w'], rt['r'][1] + 0.45 - i*0.3), (10.4+i*0.3, rt['r'][1] + 0.45 - i*0.3), (10.4+i*0.3, y+0.47), (b['x'], y+0.47)], WIFI, lw=1.8, ls=(0, (4, 2)))
    ax.text(0.8, 7.9, 'Nodes ↔ hub: 2.4 GHz Wi-Fi, MQTT 3.1.1 to\njarvis:1883, keep-alive 15 s, Last Will "offline"', fontsize=9, color=WIFI, ha='left', va='bottom')
    # clients
    cl = box(ax, 0.8, 5.2, 3.4, 1.2, 'Phone / laptop', 'dashboard http://jarvis.local:1880/dashboard\n(Wi-Fi, HTTP basic auth)', fc='#f3e5f5', fs=10)
    line(ax, [cl['r'], rt['l']], WIFI, lw=1.8, ls=(0, (4, 2)), label='Wi-Fi / LAN', fs=8)
    ax.text(0.8, 4.5, 'Measured on the bench (Nov 16–17)', fontsize=10, weight='bold', va='top')
    ax.text(0.8, 4.1, '• Node → hub round trip: median 11.7 ms, p95 19.9 ms, 0/200 lost\n'
            '• Far side of apartment: median 21.5 ms, −55 to −58 dBm\n'
            '• Reconnect after router power cycle: 0.25 s after link up\n'
            '• Broker restart: back online in 2.05 s\n'
            '• Hub RAM: 437 MiB used (4 GB board)', fontsize=9, va='top', linespacing=1.45)
    for i, (c, t, ls) in enumerate(((NET, 'Ethernet', '-'), (WIFI, 'Wi-Fi', (0, (4, 2))), (USB, 'USB / Pi header', '-'), ('#777', 'internet (optional)', '--'))):
        line(ax, [(0.8+i*2.6, 0.35), (1.3+i*2.6, 0.35)], c, lw=2.5, ls=ls); ax.text(1.4+i*2.6, 0.35, t, fontsize=9, va='center')
    f.savefig(fn, dpi=200, bbox_inches='tight'); plt.close(f)
if __name__ == '__main__':
    draw('network.png')
