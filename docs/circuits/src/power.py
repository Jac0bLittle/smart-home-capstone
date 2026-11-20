from blocks import *
def draw(fn):
    f, ax = fig(17, 11)
    ax.text(0.3, 10.6, 'Power distribution', fontsize=18, va='top')
    ax.text(0.3, 10.15, 'One switched power strip feeds everything. All node, LED, servo, heater and fan power comes from one fused 5 V 10 A rail; no 12 V supply.', fontsize=10, color='#555', va='top')
    out = box(ax, 0.3, 7.2, 1.6, 1.0, 'Wall outlet', '120 V AC', fc='#ede7f6')
    st = box(ax, 2.6, 5.5, 2.0, 3.7, 'Power strip', '6 outlets,\nindividual\nswitches', fc='#ede7f6')
    line(ax, [out['r'], (st['x'], out['r'][1])], AC, label='AC')
    pi_ps = box(ax, 5.6, 8.4, 2.2, 0.9, 'Pi 27 W PSU', '5.1 V 5 A USB-C', fc='#e3f2fd')
    rt_ps = box(ax, 5.6, 7.2, 2.2, 0.9, 'Router adapter', 'included with AX10', fc='#e3f2fd')
    psu = box(ax, 5.6, 4.95, 2.2, 1.6, '5 V 10 A PSU', '+ screw-terminal\nadapter', fc='#ffebee')
    for b, y in ((pi_ps, 8.85), (rt_ps, 7.65), (psu, 6.0)):
        line(ax, [(st['x']+st['w'], y), (b['x'], y)], AC)
    pi = box(ax, 8.8, 8.3, 2.6, 1.1, 'Raspberry Pi 5 (jarvis)', 'hub, ≈ 5–8 W', fc='#e8f5e9')
    line(ax, [pi_ps['r'], pi['l']], USB, label='USB-C', fs=8)
    rt = box(ax, 8.8, 7.15, 2.6, 0.95, 'TP-Link Archer AX10', 'router', fc='#e8f5e9')
    line(ax, [rt_ps['r'], rt['l']], USB, label='12 V barrel', fs=8)
    # Pi accessories
    jab = box(ax, 12.2, 9.15, 2.3, 0.7, 'Jabra Speak 510', 'USB-A, bus powered', fc='#fff8e1', fs=9)
    clr = box(ax, 12.2, 8.35, 2.3, 0.6, 'Active Cooler', 'Pi FAN header', fc='#fff8e1', fs=9)
    rtc = box(ax, 12.2, 7.6, 2.3, 0.6, 'RTC battery', 'Pi BAT (JST-SH)', fc='#fff8e1', fs=9)
    for b in (jab, clr, rtc):
        line(ax, [(pi['x']+pi['w'], pi['y']+pi['h']/2), (11.8, pi['y']+pi['h']/2), (11.8, b['l'][1]), b['l']], USB, lw=1.4)
    # fuse and buses
    bx5, bxg = 10.2, 10.65
    fx = 8.4; y5, yg = 5.85, 5.15
    line(ax, [(psu['x']+psu['w'], y5), (fx, y5)], RED, lw=2.6, label='+5V', fs=8)
    ax.add_patch(FancyBboxPatch((fx, y5-0.15), 0.9, 0.3, boxstyle='round,pad=0.01', fc='#ffcdd2', ec=RED, lw=1.5))
    ax.text(fx+0.45, y5+0.25, 'F1 10 A ATO\ninline holder', fontsize=8, ha='center', va='bottom', color=RED)
    line(ax, [(psu['x']+psu['w'], yg), (9.75, yg), (9.75, 0.42), (bxg, 0.42), (bxg, 0.6)], BLK, lw=2.6, label='GND', lpos=0, loff=(0, -0.32), fs=8)
    line(ax, [(fx+0.9, y5), (10.0, y5)], RED, lw=2.6)
    # Wago buses (vertical)
    ax.add_patch(FancyBboxPatch((bx5-0.15, 0.6), 0.3, 5.4, boxstyle='round,pad=0.02', fc='#ffcdd2', ec=RED))
    ax.add_patch(FancyBboxPatch((bxg-0.15, 0.6), 0.3, 4.75, boxstyle='round,pad=0.02', fc='#e0e0e0', ec=BLK))
    line(ax, [(10.0, y5), (bx5-0.15, y5)], RED, lw=2.6)
    ax.text(bx5-0.3, 0.25, 'Wago 221\n+5V bus', fontsize=8, ha='right', va='top', color=RED)
    ax.text(bxg+0.2, 0.25, 'Wago 221\nGND bus', fontsize=8, ha='left', va='top')
    loads = [('Climate node', 'ESP32, sensors, heater 1.24 A, fan', 4.6),
             ('Alarm node', 'ESP32 + PIR + buzzer', 3.85),
             ('Lighting node', 'ESP32, PIR, BH1750, 74AHCT125', 3.1),
             ('LED strip 1 (start)', 'WS2812B, 60 LEDs', 2.35),
             ('LED strip 2 (start)', 'WS2812B, 60 LEDs', 1.6),
             ('Solar node + servos', 'ESP32, 2× MG90S, 2× INA219, C2', 0.85)]
    for i, (t, s, y) in enumerate(loads):
        b = box(ax, 12.2, y-0.32, 3.2, 0.64, t, s, fc='#fffde7', fs=9)
        line(ax, [(bx5, y+0.12), (b['x'], y+0.12)], RED, lw=1.8)
        line(ax, [(bxg, y-0.12), (b['x'], y-0.12)], BLK, lw=1.8)
        ax.plot([bx5], [y+0.12], 'o', color=RED, ms=5); ax.plot([bxg], [y-0.12], 'o', color=BLK, ms=5)
    ax.text(12.2, 5.25, '18 AWG red/black pair to each\nVIN/GND (or strip +5V/GND) terminal', fontsize=8, ha='left', va='bottom')
    # budget table
    rows = [('Load (5 V rail)', 'Peak A'), ('4× ESP32 (Wi-Fi bursts)', '1.0'), ('LED strips, firmware cap 3 A\n(7.2 A if uncapped, full white)', '3.0'),
            ('Heater 6.2 W', '1.24'), ('40 mm fan', '0.15'), ('2× MG90S moving / start', '1.0'), ('PIRs, buzzer, sensors, U1', '0.1'),
            ('Total peak', '≈ 6.5 A'), ('Supply / fuse', '10 A / 10 A')]
    tx, ty = 0.4, 4.9
    ax.text(tx, ty+0.35, 'Current budget', fontsize=12, weight='bold')
    for i, (a, b) in enumerate(rows):
        yy = ty - i*0.48
        bold = i in (0, 7)
        ax.text(tx, yy, a, fontsize=9, va='top', weight='bold' if bold else 'normal')
        ax.text(tx+4.6, yy, b, fontsize=9, va='top', ha='right', weight='bold' if bold else 'normal')
        if i in (0, 6): ax.plot([tx, tx+4.7], [yy-0.42, yy-0.42] if i == 0 else [yy-0.3, yy-0.3], color='#999', lw=0.8)
    ax.text(5.6, 4.6, 'Notes', fontsize=11, weight='bold', va='top')
    ax.text(5.6, 4.2, '• ~35 % headroom at peak. The LED cap is what keeps\n   the rail under 10 A; never run both strips at full white.\n'
            '• F1 sits right after the PSU so every downstream wire\n   is protected. 18 AWG is fine for 10 A over short runs.\n'
            '• Heater, fan, strips and servos draw from the bus, not\n   through the ESP32 board traces.\n'
            '• All grounds meet at the GND bus (star point).\n'
            '• Flashing in place: switch the 5 V rail off before\n   plugging USB into a node, unless the DevKit has a\n   VIN–USB protection diode.\n'
            '• Hub, router and voice are separate from the 5 V rail:\n   a node or LED fault cannot reset the hub.',
            fontsize=8.5, va='top', linespacing=1.35)
    # legend
    for i, (c, t) in enumerate(((AC, '120 V AC'), (RED, '+5 V DC'), (BLK, 'GND'), (USB, 'USB / adapter cable'))):
        line(ax, [(0.4+i*2.1, 0.3), (0.9+i*2.1, 0.3)], c, lw=2.5); ax.text(1.0+i*2.1, 0.3, t, fontsize=8.5, va='center')
    f.savefig(fn, dpi=200, bbox_inches='tight'); plt.close(f)
if __name__ == '__main__':
    draw('power.png')
