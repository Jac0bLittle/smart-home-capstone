"""Figures for the final semester report: hardware connection diagrams,
labeled system block diagram, concept sketches, firmware flowcharts."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, Polygon
import os, sys

OUT = sys.argv[1] if len(sys.argv) > 1 else "out"
os.makedirs(OUT, exist_ok=True)

C = {  # wire colors (power vs signal kept distinct, per the course example)
    "5V": "#d62728", "GND": "#111111", "3V3": "#ff7f0e", "12V": "#8c1d40",
    "SW": "#8c564b",   # switched low side of a load
    "SDA": "#1f77b4", "SCL": "#2ca02c", "SIG": "#9467bd", "PWM": "#e377c2",
    "AN": "#17becf", "PV": "#bcbd22", "DATA": "#7f7f7f",
}
LEG = [("5V", "+5 V power"), ("3V3", "+3.3 V power"), ("GND", "Ground"),
       ("SW", "Switched load return"), ("SDA", "I²C SDA"), ("SCL", "I²C SCL"),
       ("SIG", "Digital signal"), ("PWM", "PWM / servo / LED data"),
       ("AN", "Analog (ADC1)"), ("PV", "Panel / sense path")]

PIN_DY = 0.42


def conn_diagram(fname, title, subtitle, esp_pins, modules, wires, legend_keys):
    """Breadboard-view style connection diagram.
    esp_pins: labels on the ESP32 right edge.
    modules: list of (key, name, sub, pins, fill) stacked on the right; pins on left edge.
    wires: list of (endA, endB, colorkey); end = ('ESP', pin) or (modkey, pin)."""
    n_esp = len(esp_pins)
    # module positions
    pos = {}
    y = 0
    mod_boxes = []
    for key, name, sub, pins, fill in modules:
        h = max(len(pins) * PIN_DY + 0.5, 1.1)
        mod_boxes.append((key, name, sub, pins, fill, y, h))
        for i, p in enumerate(pins):
            pos[(key, p)] = (12.0, y - 0.45 - i * PIN_DY)
        y -= h + 0.35
    total_h = -y
    esp_h = n_esp * 0.62 + 2.3
    esp_top = -(total_h - esp_h) / 2
    for i, p in enumerate(esp_pins):
        pos[("ESP", p)] = (3.0, esp_top - 0.9 - i * 0.62)

    fig_h = max(total_h, esp_h) * 0.55 + 1.6
    fig, ax = plt.subplots(figsize=(13, fig_h))
    ax.set_xlim(-0.5, 16.8)
    ax.set_ylim(-max(total_h, esp_h) - 1.6, 1.3)
    ax.axis("off")
    ax.text(-0.4, 1.05, title, fontsize=15, weight="bold", va="top")
    ax.text(-0.4, 0.5, subtitle, fontsize=9.5, color="#444", va="top")

    # ESP32 board (dark blue PCB like Fritzing)
    ax.add_patch(FancyBboxPatch((0, esp_top - esp_h), 3.0, esp_h, boxstyle="round,pad=0.02,rounding_size=0.12",
                                fc="#20456b", ec="#0d2238", lw=1.5))
    ax.add_patch(Rectangle((0.5, esp_top - 1.05), 1.6, 0.75, fc="#b8b8b8", ec="#666"))
    ax.text(1.3, esp_top - 0.68, "WROOM-32", fontsize=7, ha="center", va="center")
    ax.text(0.15, esp_top - esp_h + 0.35, "ESP32 DevKit\n(38-pin, screw-\nterminal breakout)", color="white",
            fontsize=7.5, ha="left", va="bottom", weight="bold")
    ax.add_patch(Rectangle((1.0, esp_top - esp_h - 0.05), 0.5, 0.25, fc="#999", ec="#555"))
    ax.text(1.25, esp_top - esp_h - 0.35, "USB", fontsize=6.5, ha="center")
    for p in esp_pins:
        x, yy = pos[("ESP", p)]
        ax.add_patch(Rectangle((x - 0.16, yy - 0.09), 0.18, 0.18, fc="#d4af37", ec="#7a5c00"))
        ax.text(x - 0.25, yy, p, color="white", fontsize=8, ha="right", va="center")

    for key, name, sub, pins, fill, top, h in mod_boxes:
        ax.add_patch(FancyBboxPatch((12.0, top - h), 4.4, h, boxstyle="round,pad=0.02,rounding_size=0.1",
                                    fc=fill, ec="#333", lw=1.2))
        ax.text(15.0, top - h / 2 + (0.15 if sub else 0), name, fontsize=9, weight="bold", ha="center", va="center")
        if sub:
            ax.text(15.0, top - h / 2 - 0.28, sub, fontsize=7.2, ha="center", va="center", color="#333")
        for p in pins:
            x, yy = pos[(key, p)]
            ax.add_patch(Rectangle((x - 0.02, yy - 0.09), 0.18, 0.18, fc="#d4af37", ec="#7a5c00"))
            ax.text(x + 0.25, yy, p, fontsize=7.8, ha="left", va="center")

    lanes = len(wires)
    x0, x1 = 3.5, 11.5
    for i, (a, b, ck) in enumerate(wires):
        xa, ya = pos[a]
        xb, yb = pos[b]
        xl = x0 + (x1 - x0) * (i + 0.5) / lanes
        col = C[ck]
        ax.plot([xa, xl, xl, xb], [ya, ya, yb, yb], color=col, lw=2.0, solid_capstyle="round", zorder=3)
        ax.plot([xa, xb], [ya, yb], "o", color=col, ms=4, zorder=4)

    # legend
    lx = -0.3
    ly = -max(total_h, esp_h) - 1.15
    for k in legend_keys:
        lab = dict(LEG)[k]
        ax.plot([lx, lx + 0.5], [ly, ly], color=C[k], lw=3)
        ax.text(lx + 0.6, ly, lab, fontsize=8, va="center")
        lx += 0.8 + len(lab) * 0.095
    fig.savefig(f"{OUT}/{fname}.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


BUS = ("bus", "5 V bus (Wago 221)", "from fused 10 A rail, F1", ["+5V", "GND"], "#ffe3e3")
CAP = ("cen", "C 10 µF", "EN auto-upload fix", ["+", "−"], "#eeeeee")
D4184 = lambda k, n: (k, f"{n} D4184 MOSFET", "logic-level, low-side", ["IN", "GND", "OUT−"], "#e8f0ff")

# ---- Climate node
conn_diagram(
    "hw_climate", "Hardware connection diagram: climate node",
    "Breadboard-view wiring of the climate node on its screw-terminal breakout. Wire colors separate power from signal.",
    ["VIN", "GND", "3V3", "GPIO21 SDA", "GPIO22 SCL", "GPIO25", "GPIO26", "EN"],
    [BUS,
     ("bme", "BME680", "temp/hum/press, I²C 0x77", ["VCC", "GND", "SDA", "SCL"], "#e9f7e9"),
     ("sht", "SHT40", "temp/hum, I²C 0x44", ["VCC", "GND", "SDA", "SCL"], "#e9f7e9"),
     ("ksd", "KSD9700 50 °C NC", "thermal cutoff on heater", ["T1", "T2"], "#fff3d6"),
     ("htr", "Heater film", "5 V 6.2 W, ≈4 Ω", ["+", "−"], "#fff3d6"),
     D4184("q1", "Q1"),
     ("fan", "40 mm fan", "5 V, 2-wire", ["+", "−"], "#fff3d6"),
     ("d1", "1N5819", "flyback across fan", ["K", "A"], "#eeeeee"),
     D4184("q2", "Q2"),
     CAP],
    [(("bus", "+5V"), ("ESP", "VIN"), "5V"), (("bus", "GND"), ("ESP", "GND"), "GND"),
     (("ESP", "3V3"), ("bme", "VCC"), "3V3"), (("ESP", "3V3"), ("sht", "VCC"), "3V3"),
     (("bus", "GND"), ("bme", "GND"), "GND"), (("bus", "GND"), ("sht", "GND"), "GND"),
     (("ESP", "GPIO21 SDA"), ("bme", "SDA"), "SDA"), (("ESP", "GPIO21 SDA"), ("sht", "SDA"), "SDA"),
     (("ESP", "GPIO22 SCL"), ("bme", "SCL"), "SCL"), (("ESP", "GPIO22 SCL"), ("sht", "SCL"), "SCL"),
     (("bus", "+5V"), ("ksd", "T1"), "5V"), (("ksd", "T2"), ("htr", "+"), "5V"),
     (("htr", "−"), ("q1", "OUT−"), "SW"), (("ESP", "GPIO25"), ("q1", "IN"), "SIG"),
     (("bus", "GND"), ("q1", "GND"), "GND"),
     (("bus", "+5V"), ("fan", "+"), "5V"), (("fan", "+"), ("d1", "K"), "5V"), (("fan", "−"), ("d1", "A"), "SW"),
     (("fan", "−"), ("q2", "OUT−"), "SW"), (("ESP", "GPIO26"), ("q2", "IN"), "PWM"),
     (("bus", "GND"), ("q2", "GND"), "GND"),
     (("ESP", "EN"), ("cen", "+"), "SIG"), (("bus", "GND"), ("cen", "−"), "GND")],
    ["5V", "3V3", "GND", "SW", "SDA", "SCL", "SIG", "PWM"])

# ---- Alarm node
conn_diagram(
    "hw_alarm", "Hardware connection diagram: security alarm node",
    "PIR and door reed switch inputs, buzzer driven through a MOSFET module. Reed + pull-up makes a cut wire read as 'door open'.",
    ["VIN", "GND", "3V3", "GPIO27", "GPIO26", "GPIO25", "EN"],
    [BUS,
     ("pir", "HC-SR501 PIR", "5 V supply, 3.3 V output", ["VCC", "OUT", "GND"], "#e9f7e9"),
     ("r1", "R 10 kΩ", "door pull-up", ["1", "2"], "#eeeeee"),
     ("reed", "MC-38 reed", "closed = door shut", ["C1", "C2"], "#e9f7e9"),
     ("bz", "SFM-27 buzzer", "active, ≈95 dB", ["+", "−"], "#fff3d6"),
     D4184("q3", "Q3"),
     CAP],
    [(("bus", "+5V"), ("ESP", "VIN"), "5V"), (("bus", "GND"), ("ESP", "GND"), "GND"),
     (("bus", "+5V"), ("pir", "VCC"), "5V"), (("ESP", "GPIO27"), ("pir", "OUT"), "SIG"),
     (("bus", "GND"), ("pir", "GND"), "GND"),
     (("ESP", "3V3"), ("r1", "1"), "3V3"), (("ESP", "GPIO26"), ("r1", "2"), "SIG"),
     (("ESP", "GPIO26"), ("reed", "C1"), "SIG"), (("bus", "GND"), ("reed", "C2"), "GND"),
     (("bus", "+5V"), ("bz", "+"), "5V"), (("bz", "−"), ("q3", "OUT−"), "SW"),
     (("ESP", "GPIO25"), ("q3", "IN"), "SIG"), (("bus", "GND"), ("q3", "GND"), "GND"),
     (("ESP", "EN"), ("cen", "+"), "SIG"), (("bus", "GND"), ("cen", "−"), "GND")],
    ["5V", "3V3", "GND", "SW", "SIG"])

# ---- Lighting node
conn_diagram(
    "hw_lighting", "Hardware connection diagram: exterior lighting node",
    "Lux sensor + PIR inputs; 74AHCT125 shifts the 3.3 V LED data to 5 V. Strips are powered from both ends of the 5 V bus.",
    ["VIN", "GND", "3V3", "GPIO21 SDA", "GPIO22 SCL", "GPIO27", "GPIO16", "EN"],
    [BUS,
     ("bh", "BH1750", "lux, I²C 0x23", ["VCC", "GND", "SDA", "SCL", "ADDR"], "#e9f7e9"),
     ("pir", "HC-SR501 PIR", "", ["VCC", "OUT", "GND"], "#e9f7e9"),
     ("u1", "U1 74AHCT125", "3.3 → 5 V buffer", ["VCC(14)", "1A(2)", "1OE(1)", "1Y(3)", "GND(7)"], "#e8f0ff"),
     ("r", "R 330 Ω", "data series", ["1", "2"], "#eeeeee"),
     ("s1", "WS2812B strip 1", "60 LEDs", ["+5V", "DIN", "DOUT", "GND"], "#fff3d6"),
     ("s2", "WS2812B strip 2", "60 LEDs", ["+5V", "DIN", "GND"], "#fff3d6"),
     ("c1", "C1 1000 µF", "at strip-1 input", ["+", "−"], "#eeeeee"),
     CAP],
    [(("bus", "+5V"), ("ESP", "VIN"), "5V"), (("bus", "GND"), ("ESP", "GND"), "GND"),
     (("ESP", "3V3"), ("bh", "VCC"), "3V3"), (("bus", "GND"), ("bh", "GND"), "GND"),
     (("bus", "GND"), ("bh", "ADDR"), "GND"),
     (("ESP", "GPIO21 SDA"), ("bh", "SDA"), "SDA"), (("ESP", "GPIO22 SCL"), ("bh", "SCL"), "SCL"),
     (("bus", "+5V"), ("pir", "VCC"), "5V"), (("ESP", "GPIO27"), ("pir", "OUT"), "SIG"),
     (("bus", "GND"), ("pir", "GND"), "GND"),
     (("bus", "+5V"), ("u1", "VCC(14)"), "5V"), (("ESP", "GPIO16"), ("u1", "1A(2)"), "PWM"),
     (("bus", "GND"), ("u1", "1OE(1)"), "GND"), (("bus", "GND"), ("u1", "GND(7)"), "GND"),
     (("u1", "1Y(3)"), ("r", "1"), "PWM"), (("r", "2"), ("s1", "DIN"), "PWM"),
     (("s1", "DOUT"), ("s2", "DIN"), "PWM"),
     (("bus", "+5V"), ("s1", "+5V"), "5V"), (("bus", "GND"), ("s1", "GND"), "GND"),
     (("bus", "+5V"), ("s2", "+5V"), "5V"), (("bus", "GND"), ("s2", "GND"), "GND"),
     (("bus", "+5V"), ("c1", "+"), "5V"), (("bus", "GND"), ("c1", "−"), "GND"),
     (("ESP", "EN"), ("cen", "+"), "SIG"), (("bus", "GND"), ("cen", "−"), "GND")],
    ["5V", "3V3", "GND", "SDA", "SCL", "SIG", "PWM"])

# ---- Solar node
conn_diagram(
    "hw_solar", "Hardware connection diagram: solar tracker node",
    "Four LDR dividers on ADC1, two servos from the 5 V bus, two INA219s measuring the tracked and fixed panels into 22 Ω loads.",
    ["VIN", "GND", "3V3", "GPIO32", "GPIO33", "GPIO35", "GPIO39", "GPIO21 SDA", "GPIO22 SCL", "GPIO18", "GPIO19", "EN"],
    [BUS,
     ("ldr", "LDR quad board", "4× GL5528 + 4× 10 kΩ to GND", ["3V3", "TL", "TR", "BL", "BR", "GND"], "#e9f7e9"),
     ("sp", "MG90S pan", "", ["+5V", "SIG", "GND"], "#fff3d6"),
     ("st", "MG90S tilt", "", ["+5V", "SIG", "GND"], "#fff3d6"),
     ("c2", "C2 470 µF", "servo supply", ["+", "−"], "#eeeeee"),
     ("i1", "INA219 #1", "0x40, tracked", ["VCC", "GND", "SDA", "SCL", "VIN+", "VIN−"], "#e8f0ff"),
     ("p1", "Tracked panel", "6 V 1–2 W + RL 22 Ω", ["P+", "RL", "P−/RL"], "#fffbd0"),
     ("i2", "INA219 #2", "0x41 (A0), reference", ["VCC", "GND", "SDA", "SCL", "VIN+", "VIN−"], "#e8f0ff"),
     ("p2", "Fixed panel", "6 V 1–2 W + RL 22 Ω", ["P+", "RL", "P−/RL"], "#fffbd0"),
     CAP],
    [(("bus", "+5V"), ("ESP", "VIN"), "5V"), (("bus", "GND"), ("ESP", "GND"), "GND"),
     (("ESP", "3V3"), ("ldr", "3V3"), "3V3"), (("bus", "GND"), ("ldr", "GND"), "GND"),
     (("ESP", "GPIO32"), ("ldr", "TL"), "AN"), (("ESP", "GPIO33"), ("ldr", "TR"), "AN"),
     (("ESP", "GPIO35"), ("ldr", "BL"), "AN"), (("ESP", "GPIO39"), ("ldr", "BR"), "AN"),
     (("bus", "+5V"), ("sp", "+5V"), "5V"), (("ESP", "GPIO18"), ("sp", "SIG"), "PWM"), (("bus", "GND"), ("sp", "GND"), "GND"),
     (("bus", "+5V"), ("st", "+5V"), "5V"), (("ESP", "GPIO19"), ("st", "SIG"), "PWM"), (("bus", "GND"), ("st", "GND"), "GND"),
     (("bus", "+5V"), ("c2", "+"), "5V"), (("bus", "GND"), ("c2", "−"), "GND"),
     (("ESP", "3V3"), ("i1", "VCC"), "3V3"), (("bus", "GND"), ("i1", "GND"), "GND"),
     (("ESP", "GPIO21 SDA"), ("i1", "SDA"), "SDA"), (("ESP", "GPIO22 SCL"), ("i1", "SCL"), "SCL"),
     (("i1", "VIN+"), ("p1", "P+"), "PV"), (("i1", "VIN−"), ("p1", "RL"), "PV"), (("bus", "GND"), ("p1", "P−/RL"), "GND"),
     (("ESP", "3V3"), ("i2", "VCC"), "3V3"), (("bus", "GND"), ("i2", "GND"), "GND"),
     (("ESP", "GPIO21 SDA"), ("i2", "SDA"), "SDA"), (("ESP", "GPIO22 SCL"), ("i2", "SCL"), "SCL"),
     (("i2", "VIN+"), ("p2", "P+"), "PV"), (("i2", "VIN−"), ("p2", "RL"), "PV"), (("bus", "GND"), ("p2", "P−/RL"), "GND"),
     (("ESP", "EN"), ("cen", "+"), "SIG"), (("bus", "GND"), ("cen", "−"), "GND")],
    ["5V", "3V3", "GND", "SDA", "SCL", "AN", "PWM", "PV", "SIG"])


# ---------------------------------------------------------------- block diagram
def box(ax, x, y, w, h, title, fill, terms_l=(), terms_r=(), terms_t=(), terms_b=(), fs=9):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fill, ec="#222", lw=1.3))
    ax.text(x + w / 2, y + h / 2, title, ha="center", va="center", fontsize=fs, weight="bold")
    P = {}
    for i, t in enumerate(terms_l):
        yy = y + h - (i + 1) * h / (len(terms_l) + 1)
        ax.text(x - 0.08, yy + 0.18, t, fontsize=6.5, va="bottom", ha="right", color="#333"); P[t + "@L"] = (x, yy)
    for i, t in enumerate(terms_r):
        yy = y + h - (i + 1) * h / (len(terms_r) + 1)
        ax.text(x + w + 0.08, yy + 0.18, t, fontsize=6.5, va="bottom", ha="left", color="#333"); P[t + "@R"] = (x + w, yy)
    for i, t in enumerate(terms_t):
        xx = x + (i + 1) * w / (len(terms_t) + 1)
        ax.text(xx, y + h - 0.12, t, fontsize=6.5, va="top", ha="center", color="#333"); P[t + "@T"] = (xx, y + h)
    for i, t in enumerate(terms_b):
        xx = x + (i + 1) * w / (len(terms_b) + 1)
        ax.text(xx, y + 0.1, t, fontsize=6.5, va="bottom", ha="center", color="#333"); P[t + "@B"] = (xx, y)
    return P


def line(ax, pts, ck, lw=2.2, ls="-"):
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=C[ck] if ck in C else ck, lw=lw, ls=ls, solid_capstyle="round", zorder=2)


fig, ax = plt.subplots(figsize=(15, 10))
ax.set_xlim(0, 30); ax.set_ylim(0, 20); ax.axis("off")
ax.text(0.2, 19.6, "Smart Home Model: system block diagram with labeled terminals", fontsize=15, weight="bold", va="top")
ax.text(0.2, 18.9, "Power wiring in red/black/purple, signals in other colors. Terminal names match the node schematics and the ESP32 pin map.", fontsize=9.5, color="#444", va="top")
W = box(ax, 0.5, 9.5, 2.6, 2.2, "Wall outlet\n120 V AC", "#efe6f5", terms_r=["L/N"])
PS = box(ax, 4.2, 6.5, 2.8, 8.5, "Switched\npower strip", "#efe6f5", terms_l=["IN"], terms_r=["OUT1", "OUT2", "OUT3"])
PI = box(ax, 8.6, 14.0, 3.2, 2.0, "Pi 27 W PSU", "#e3f0fb", terms_l=["AC"], terms_r=["5V1"])
RA = box(ax, 8.6, 11.0, 3.2, 2.0, "Router adapter", "#e3f0fb", terms_l=["AC"], terms_r=["12 V DC"])
P5 = box(ax, 8.6, 6.0, 3.2, 2.6, "5 V 10 A PSU", "#fde4e4", terms_l=["AC"], terms_r=["+V", "−V"])
F1 = box(ax, 12.6, 7.8, 1.6, 0.9, "F1 10 A", "#fde4e4", terms_l=["in"], terms_r=["out"], fs=8)
HUB = box(ax, 13.0, 13.4, 4.8, 3.2, "Raspberry Pi 5 4 GB\n\"jarvis\" hub\nMosquitto · Node-RED\nlogger · alerter · voice", "#e6f4e6",
          terms_l=["PWR"], terms_r=["USB-A", "ETH"], terms_t=["BAT", "FAN"])
RT = box(ax, 20.0, 10.8, 3.6, 2.0, "TP-Link AX10 router\n2.4 GHz WPA2", "#e6f4e6", terms_l=["DC IN"], terms_t=["LAN1"], terms_r=["Wi-Fi"])
SPK = box(ax, 20.0, 15.6, 3.6, 1.6, "USB speakerphone\n(mic + speaker)", "#fff7dc", terms_l=["USB"])
PH = box(ax, 25.4, 15.0, 4.0, 1.8, "Phone / laptop\ndashboard +\nAndroid page", "#f3e6f7")
BUSB = box(ax, 15.3, 1.0, 0.9, 7.6, "", "#fde4e4")
ax.text(15.75, 0.6, "+5V bus", ha="center", fontsize=8, color=C["5V"])
GB = box(ax, 16.8, 1.0, 0.9, 7.6, "", "#e6e6e6")
ax.text(17.25, 0.6, "GND bus", ha="center", fontsize=8)
nodes = [("Climate node (ESP32)\nBME680 · SHT40 · heater · fan", "", 7.0), ("Alarm node (ESP32)\nPIR · reed · buzzer", "", 5.0),
         ("Lighting node (ESP32)\nBH1750 · PIR · 2× WS2812B", "", 3.0), ("Solar node (ESP32)\n4× LDR · 2× MG90S · 2× INA219", "", 1.0)]
for name, sub, yy in nodes:
    b = box(ax, 20.0, yy, 5.6, 1.6, name, "#fffbe0", terms_l=["VIN", "GND"], terms_r=["Wi-Fi"], fs=8)
    line(ax, [(15.75 + 0.45, b["VIN@L"][1]), b["VIN@L"]], "5V")
    line(ax, [(17.25 + 0.45, b["GND@L"][1]), b["GND@L"]], "GND")
    ax.plot([16.2], [b["VIN@L"][1]], "o", color=C["5V"], ms=5)
    ax.plot([17.7], [b["GND@L"][1]], "o", color="k", ms=5)
    line(ax, [b["Wi-Fi@R"], (29.2, b["Wi-Fi@R"][1])], "#ff7f0e", lw=1.6, ls="--")
line(ax, [(29.2, 1.8), (29.2, 11.8)], "#ff7f0e", lw=1.6, ls="--")
line(ax, [RT["Wi-Fi@R"], (29.2, RT["Wi-Fi@R"][1])], "#ff7f0e", lw=1.6, ls="--")
line(ax, [(29.2, 11.8), (29.2, 15.0)], "#ff7f0e", lw=1.6, ls="--")
ax.text(28.9, 9.5, "2.4 GHz Wi-Fi\nMQTT 3.1.1 :1883", fontsize=7.5, ha="right", color="#c25e00")
# AC wiring (purple)
line(ax, [W["L/N@R"], PS["IN@L"]], "#7b3fa0")
for k, dst in [("OUT1@R", PI["AC@L"]), ("OUT2@R", RA["AC@L"]), ("OUT3@R", P5["AC@L"])]:
    s = PS[k]; line(ax, [s, (8.0, s[1]), (8.0, dst[1]), dst], "#7b3fa0")
line(ax, [PI["5V1@R"], HUB["PWR@L"]], "5V")
line(ax, [RA["12 V DC@R"], (18.8, RA["12 V DC@R"][1]), (18.8, RT["DC IN@L"][1]), RT["DC IN@L"]], "12V")
line(ax, [P5["+V@R"], F1["in@L"]], "5V")
line(ax, [F1["out@R"], (15.3, F1["out@R"][1])], "5V")
line(ax, [P5["−V@R"], (12.3, P5["−V@R"][1]), (12.3, 0.4), (17.25, 0.4), (17.25, 1.0)], "GND")
line(ax, [HUB["ETH@R"], (19.0, HUB["ETH@R"][1]), (19.0, 13.4), (RT["LAN1@T"][0], 13.4), RT["LAN1@T"]], "#2e7d32")
ax.text(19.1, 13.6, "Cat6 Ethernet", fontsize=7.5, color="#2e7d32")
line(ax, [HUB["USB-A@R"], (19.4, HUB["USB-A@R"][1]), (19.4, SPK["USB@L"][1]), SPK["USB@L"]], "#1f77b4")
for lab, x0 in [("RTC battery", 13.6), ("Active cooler", 16.0)]:
    pass
leg = [("#7b3fa0", "120 V AC"), (C["5V"], "+5 V DC"), (C["12V"], "12 V DC (router only)"), ("k", "GND"),
       ("#2e7d32", "Ethernet"), ("#1f77b4", "USB data"), ("#ff7f0e", "Wi-Fi (MQTT)")]
lx = 0.5
for col, lab in leg:
    ax.plot([lx, lx + 0.8], [17.6, 17.6], color=col, lw=3, ls="--" if "Wi-Fi" in lab else "-")
    ax.text(lx + 0.95, 17.6, lab, fontsize=8, va="center"); lx += 1.3 + len(lab) * 0.16
ax.text(0.5, 4.2, "Notes\n• Mains stays outside the model: only listed plug-in\n  supplies; everything inside is ≤12 V DC.\n• F1 (10 A ATO) sits right after the 5 V PSU, so every\n  downstream wire is protected.\n• Hub, router and voice are separate from the 5 V\n  rail, so a node fault cannot reset the hub.\n• Pin-level terminals for each node: see the\n  schematics and hardware connection diagrams.",
        fontsize=8.5, va="top")
fig.savefig(f"{OUT}/block_diagram.png", dpi=170, bbox_inches="tight"); plt.close(fig)


# ---------------------------------------------------------------- concept sketches
fig, axs = plt.subplots(1, 3, figsize=(15, 5.2))
titles = ["Concept A: proprietary central controller\n(myRIO-type, 2019 baseline)",
          "Concept B: one low-cost controller\nwith direct GPIO wiring",
          "Concept C (selected): hub + distributed\nESP32 nodes over Wi-Fi/MQTT"]
for ax, t in zip(axs, titles):
    ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axis("off"); ax.set_title(t, fontsize=10.5, weight="bold")
    ax.add_patch(Polygon([[1, 1], [9, 1], [9, 6.2], [5, 9], [1, 6.2]], closed=True, fc="#fafafa", ec="#555", lw=1.5))
subs = [("Climate", 2.2, 4.8), ("Alarm", 7.8, 4.8), ("Lights", 2.2, 2.0), ("Solar", 5.0, 7.7)]
# A
ax = axs[0]
ax.add_patch(Rectangle((3.8, 2.6), 2.4, 1.6, fc="#c9d9f2", ec="#223")); ax.text(5, 3.4, "myRIO\n$548", ha="center", va="center", fontsize=9, weight="bold")
for n, x, y in subs:
    ax.add_patch(Rectangle((x - 0.8, y - 0.4), 1.6, 0.8, fc="#fff3d6", ec="#333")); ax.text(x, y, n, ha="center", va="center", fontsize=8)
    ax.plot([x, x, 5], [y, 3.4 if abs(y - 3.4) > 0.5 else y, 3.4], color="#555", lw=3)
ax.text(5, 0.4, "Long harnesses to one controller; LabVIEW VIs", ha="center", fontsize=8.5)
# B
ax = axs[1]
ax.add_patch(Rectangle((4.0, 2.8), 2.0, 1.2, fc="#d8eed8", ec="#223")); ax.text(5, 3.4, "1 MCU", ha="center", va="center", fontsize=9, weight="bold")
for n, x, y in subs:
    ax.add_patch(Rectangle((x - 0.8, y - 0.4), 1.6, 0.8, fc="#fff3d6", ec="#333")); ax.text(x, y, n, ha="center", va="center", fontsize=8)
    for k in range(4):
        ax.plot([x + (k - 1.5) * 0.12, x + (k - 1.5) * 0.12, 5 + (k - 1.5) * 0.1], [y, 3.4 + (k - 1.5) * 0.1, 3.4 + (k - 1.5) * 0.1], color="#888", lw=1)
ax.text(5, 0.4, "Cheap, but cable congestion and GPIO limits", ha="center", fontsize=8.5)
# C
ax = axs[2]
ax.add_patch(Rectangle((3.9, 2.6), 2.2, 1.4, fc="#e6f4e6", ec="#223", zorder=5)); ax.text(5, 3.3, "Pi 5 hub\nMQTT", ha="center", va="center", fontsize=8.5, weight="bold", zorder=6)
for n, x, y in subs:
    ax.add_patch(Rectangle((x - 0.9, y - 0.45), 1.8, 0.9, fc="#fffbe0", ec="#333")); ax.text(x, y, n + "\nESP32", ha="center", va="center", fontsize=7.5)
    ax.annotate("", xy=(5, 3.3), xytext=(x, y), arrowprops=dict(arrowstyle="<->", color="#ff7f0e", ls="--", lw=1.4))
ax.add_patch(Rectangle((1, 0.6), 8, 0.4, fc="#ddd", ec="#555")); ax.text(5, 0.8, "sliding under-floor service bay", ha="center", va="center", fontsize=7.5)
ax.plot([1, 5, 9], [6.2, 9, 6.2], color="#5aa9e6", lw=3)
ax.text(7.6, 8.1, "clear roof", fontsize=7.5, color="#2a7ab8")
fig.tight_layout(); fig.savefig(f"{OUT}/concepts.png", dpi=170, bbox_inches="tight"); plt.close(fig)


# ---------------------------------------------------------------- flowcharts
def fc_node(ax, x, y, text, kind="proc", w=3.4, h=0.9, fill=None):
    if kind == "dec":
        ax.add_patch(Polygon([[x, y + h * 0.75], [x + w / 2, y], [x, y - h * 0.75], [x - w / 2, y]], fc=fill or "#fff3d6", ec="#333"))
    elif kind == "term":
        ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle="round,pad=0.02,rounding_size=0.4", fc=fill or "#e6f4e6", ec="#333"))
    else:
        ax.add_patch(Rectangle((x - w / 2, y - h / 2), w, h, fc=fill or "#e8f0ff", ec="#333"))
    ax.text(x, y, text, ha="center", va="center", fontsize=7.6)


def arr(ax, p, q, lab=None, via=None):
    pts = [p] + (via or []) + [q]
    for a, b in zip(pts[:-2], pts[1:-1]):
        ax.plot([a[0], b[0]], [a[1], b[1]], color="#333", lw=1.1)
    ax.annotate("", xy=pts[-1], xytext=pts[-2], arrowprops=dict(arrowstyle="-|>", color="#333", lw=1.1))
    if lab:
        m = pts[1] if via else ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
        ax.text(m[0] + 0.1, m[1] + 0.12, lab, fontsize=7, color="#a00")


fig, axs = plt.subplots(1, 2, figsize=(15, 11))
# Common node loop
ax = axs[0]; ax.set_xlim(0, 10); ax.set_ylim(0, 22); ax.axis("off")
ax.set_title("Shared ESP32 node firmware (all four nodes)", fontsize=11, weight="bold")
N = [(5, 21, "Power on / reset", "term"), (5, 19.6, "Load config.h + secrets.h\nrestore retained state", "proc"),
     (5, 18.1, "Connect Wi-Fi (2.4 GHz)\n+ MQTT login, Last Will 'offline'", "proc"),
     (5, 16.6, "Publish status 'online', boot_ms\nsubscribe cmd/#", "proc"),
     (5, 15.0, "Every loop (≈10–100 ms):\nread sensors", "proc"),
     (5, 13.4, "Run subsystem logic\n(see right)", "proc"),
     (5, 11.8, "Command\nreceived?", "dec"),
     (5, 10.0, "Clamp to safe range,\napply, publish state/ (QoS 1, retained)", "proc"),
     (5, 8.4, "Telemetry timer\nelapsed?", "dec"),
     (5, 6.6, "Publish tele/ (QoS 0)\nuptime, RSSI, free heap", "proc"),
     (5, 5.0, "MQTT link\nlost?", "dec"),
     (5, 3.2, "Keep local safety logic running;\nheater off after 60 s without hub;\nretry connect with back-off", "proc")]
for x, y, t, k in N:
    fc_node(ax, x, y, t, k, w=4.2 if k != "dec" else 3.2, h=1.0 if k != "dec" else 1.2)
for (a, b) in zip(N[:6], N[1:7]):
    arr(ax, (a[0], a[1] - 0.5), (b[0], b[1] + (0.9 if b[3] == "dec" else 0.5)))
arr(ax, (5, 11.8 - 0.9), (5, 10.5), "yes")
arr(ax, (6.6, 11.8), (5, 8.4 + 0.9), "no", via=[(7.6, 11.8), (7.6, 9.6), (5, 9.6)])
arr(ax, (5, 9.5), (5, 9.3))
arr(ax, (5, 8.4 - 0.9), (5, 7.1), "yes")
arr(ax, (6.6, 8.4), (5, 5.0 + 0.9), "no", via=[(7.6, 8.4), (7.6, 6.0), (5, 6.0)])
arr(ax, (5, 5.0 - 0.9), (5, 3.7 + 0.5), "yes")
arr(ax, (3.4, 5.0), (2.9, 15.0), "no → next loop", via=[(1.0, 5.0), (1.0, 15.0)])
arr(ax, (5, 2.6), (2.9, 15.0), None, via=[(5, 1.6), (0.6, 1.6), (0.6, 15.0)])

# Alarm + solar logic
ax = axs[1]; ax.set_xlim(0, 12); ax.set_ylim(0, 22); ax.axis("off")
ax.set_title("Subsystem logic: alarm (top) and solar tracker (bottom)", fontsize=11, weight="bold")
A = [(6, 21.1, "mode = armed?", "dec"), (6, 19.3, "PIR or door event\nwithin window?", "dec"),
     (6, 17.5, "Count detections;\n2 within window?", "dec"), (6, 15.9, "Buzzer ON (Q3), publish event/alarm\nhub alerter → ntfy push / email (5 min cooldown)", "proc"),
     (6, 14.6, "Until 'silence' or 'disarmed' command", "term")]
for x, y, t, k in A:
    fc_node(ax, x, y, t, k, w=5.4 if k != "dec" else 3.6, h=0.9 if k != "dec" else 0.9)
arr(ax, (6, 21.1 - 0.68), (6, 19.3 + 0.68), "yes"); arr(ax, (6, 19.3 - 0.68), (6, 17.5 + 0.68), "yes")
arr(ax, (6, 17.5 - 0.68), (6, 16.35), "yes"); arr(ax, (6, 15.45), (6, 15.05))
ax.text(8.0, 21.1, "no → idle (log only)", fontsize=7, color="#a00"); ax.text(8.0, 19.3, "no → wait", fontsize=7, color="#a00"); ax.text(8.0, 17.5, "no → keep counting", fontsize=7, color="#a00")
S = [(6, 12.6, "Read 4 LDRs (TL, TR, BL, BR) every 100 ms", "proc"),
     (6, 11.1, "Sum < 600?", "dec"), (6, 9.5, "ePan = (R−L)/(R+L)\neTilt = (T−B)/(T+B)", "proc"),
     (6, 8.0, "|e| > 5 % dead band?", "dec"),
     (6, 6.4, "Step = e × 20°, capped at 2°/step;\nclamp pan 10–170°, tilt 10–90°", "proc"),
     (6, 5.0, "Write servos; publish state/ on change", "proc"),
     (6, 3.6, "Every 5 s: publish panel_v, panel_ma,\npanel_mw (tracked), ref_mw (fixed)", "proc")]
for x, y, t, k in S:
    fc_node(ax, x, y, t, k, w=5.4 if k != "dec" else 3.6, h=0.9 if k != "dec" else 1.1)
arr(ax, (6, 12.15), (6, 11.1 + 0.82)); arr(ax, (6, 11.1 - 0.82), (6, 9.95), "no")
arr(ax, (6, 9.05), (6, 8.0 + 0.82)); arr(ax, (6, 8.0 - 0.82), (6, 6.85), "yes")
arr(ax, (6, 5.95), (6, 5.45)); arr(ax, (6, 4.55), (6, 4.05))
fc_node(ax, 10.3, 11.1, "10 s: event/low_light 1, hold\n60 s: park 90°/45°", "proc", w=3.2, h=1.0, fill="#fde4e4")
arr(ax, (7.8, 11.1), (8.7, 11.1), "yes")
ax.text(8.0, 8.0, "no → hold (no jitter)", fontsize=7, color="#a00")
ax.text(0.3, 1.8, "Modes from cmd/mode: track (shown), park (hold 90°/45°), manual (dashboard / Android sliders).\nAll tuning values are marked TUNE at the top of each node_<subsystem>.cpp.", fontsize=7.8)
fig.tight_layout(); fig.savefig(f"{OUT}/flowcharts.png", dpi=170, bbox_inches="tight"); plt.close(fig)
print("done")
