import importlib, os, shutil
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
from PIL import Image as PI
OUT = 'out'; os.makedirs(OUT, exist_ok=True)
items = [('power', '01_power_distribution'), ('network', '02_hub_network'), ('climate', '03_climate_node'),
         ('alarm', '04_alarm_node'), ('lighting', '05_lighting_node'), ('solar', '06_solar_tracker_node')]
for mod, name in items:
    m = importlib.import_module(mod)
    for ext in ('png', 'svg'): m.draw(f'{OUT}/{name}.{ext}')
ss = getSampleStyleSheet(); body = ss['BodyText']; body.fontSize = 9; body.leading = 11.5
h = ss['Heading2']
W, H = landscape(letter)
doc = SimpleDocTemplate(f'{OUT}/Smart_Home_Circuit_Diagrams.pdf', pagesize=landscape(letter), leftMargin=0.4*inch, rightMargin=0.4*inch, topMargin=0.35*inch, bottomMargin=0.35*inch,
                        title='Smart Home Model - Circuit Diagrams', author='Smart Home Model Capstone')
story = []
for i, (mod, name) in enumerate(items):
    w, hh = PI.open(f'{OUT}/{name}.png').size
    maxw, maxh = W - 0.8*inch - 14, H - 0.7*inch - 16
    s = min(maxw / w, maxh / hh)
    story += [Image(f'{OUT}/{name}.png', w*s, hh*s), PageBreak()]
P = lambda t: Paragraph(t, body)
story.append(Paragraph('ESP32 pin map (all four nodes)', h))
pins = [['Node', 'GPIO', 'Connects to', 'Notes'],
 ['All', 'VIN / GND', '+5V rail / GND bus (18 AWG)', 'USB only for flashing; rail off when plugging USB in'],
 ['All', 'EN', '10 µF to GND', 'auto upload-mode fix from bench test'],
 ['All', 'GPIO2', 'on-board LED', 'status / sim indicator'],
 ['Climate', '21 / 22', 'I2C: BME680 (0x77), SHT40 (0x44)', '3V3 sensors'],
 ['Climate', '25', 'Q1 D4184 → heater (via KSD9700 50 °C NC)', '1.24 A'],
 ['Climate', '26', 'Q2 D4184 → 40 mm fan (1N5819 flyback)', 'PWM ≤ 1 kHz or on/off'],
 ['Alarm', '27', 'HC-SR501 PIR OUT', '3.3 V output, direct'],
 ['Alarm', '26', 'MC-38 reed to GND + 10 kΩ pull-up', 'HIGH = open; set pin to INPUT in firmware'],
 ['Alarm', '25', 'Q3 D4184 → SFM-27 buzzer', '+5V supply'],
 ['Lighting', '27', 'HC-SR501 PIR OUT', ''],
 ['Lighting', '16', '74AHCT125 1A → 1Y → 330 Ω → strip DIN', 'firmware cap 3 A'],
 ['Lighting', '21 / 22', 'I2C: BH1750 (0x23)', 'replaces bench LDR on GPIO34'],
 ['Solar', '32 / 33 / 35 / 39', 'LDR TL / TR / BL / BR, 10 kΩ to GND', 'ADC1 only (Wi-Fi safe)'],
 ['Solar', '18 / 19', 'MG90S pan / tilt signal', 'servo power from +5V rail, C2 470 µF'],
 ['Solar', '21 / 22', 'I2C: INA219 #1 (0x40), #2 (0x41)', 'high side, 22 Ω load each']]
t = Table([[P(c) for c in r] for r in pins], colWidths=[0.9*inch, 1.3*inch, 3.9*inch, 3.6*inch], repeatRows=1)
t.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e0e0e0')), ('GRID', (0,0), (-1,-1), 0.4, colors.grey), ('VALIGN', (0,0), (-1,-1), 'TOP'),
                       ('TOPPADDING', (0,0), (-1,-1), 2), ('BOTTOMPADDING', (0,0), (-1,-1), 2)]))
story += [t, PageBreak(), Paragraph('Gaps the diagrams reveal in the order list (Nov 19 version)', h)]
gaps = [['#', 'Item', 'Why it is needed', 'Suggested fix'],
 ['1', 'Small passives: 4× 10 µF, 1× 1000 µF 10 V, 1× 470 µF 10 V electrolytic; 1× 330 Ω; 5× 10 kΩ',
  'EN boot fix (each node), LED strip bulk cap, servo cap, LED data resistor, 4 LDR dividers + reed pull-up', 'Lab stock, or add a resistor + electrolytic capacitor assortment (~$12)'],
 ['2', '1× 1N5819 Schottky diode', 'Fan flyback (D4184 modules usually have none)', 'Lab stock or diode assortment'],
 ['3', '2× 22 Ω 3 W resistors (20–27 Ω, ≥ 2 W)', 'Fixed load for each panel so the INA219s measure real power', 'Lab stock or add ~$6'],
 ['4', 'Pan/tilt bracket kit ($30)', 'Still on the list, but the tracker now uses the 3D-printed pan/tilt', 'Remove: total drops from $704.50 to $674.50'],
 ['5', '10 A ATO fuse', 'F1 on the 5 V rail', 'Confirm the fuse assortment includes 10 A'],
 ['6', 'MC-38 variant', 'Diagram assumes contact closed when the magnet is near (door shut)', 'Pick that variant; the "NC/NO" option may have both leads'],
 ['7', '40 mm fan wiring', 'Diagram assumes a 2-wire 5 V fan switched low-side', 'Check the GeeekPi fan has 2 wires; if 3/4-wire, use only red/black'],
 ['8', 'Optional: 14-pin DIP socket, female headers', 'Easier to swap U1 and breakouts on protoboard', 'Check the Smraza kit; lab stock'],
 ['9', 'Steel M3 screws/nuts, #4 wood screws', '3D-printed mounts (from the 3D print thread)', 'Lab or house materials']]
t2 = Table([[P(c) for c in r] for r in gaps], colWidths=[0.3*inch, 3.0*inch, 3.5*inch, 3.0*inch], repeatRows=1)
t2.setStyle(t._argW and TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e0e0e0')), ('GRID', (0,0), (-1,-1), 0.4, colors.grey), ('VALIGN', (0,0), (-1,-1), 'TOP')]))
story += [t2, Spacer(1, 8), P('<b>Covered by the order:</b> 6 ESP32 boards (4 used, 2 spare), 5 PIRs (2 used), 5 D4184 modules (3 used: heater, fan, buzzer), 4 INA219 (2 used), 2 BH1750 (1 used, 1 spare), 10 KSD9700 (1 used), 10 74AHCT125 (1 used). '
      'MQ-2 gas sensing is not on the list, so it is not drawn. Firmware follow-ups: pin defines for heater/fan/buzzer/LED data in config.h, door pin to INPUT, and drivers for BME680/SHT40, BH1750, INA219 and WS2812B.')]
doc.build(story)
print('built')
