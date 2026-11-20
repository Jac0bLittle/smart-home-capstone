from common import *
def draw(fn):
  with schemdraw.Drawing(show=False) as d:
    d.config(fontsize=FS, unit=2)
    A = esp32(d, (0, 0), [('sda', 'GPIO21 SDA'), ('scl', 'GPIO22 SCL'), ('g27', 'GPIO27'), ('g16', 'GPIO16')])
    L = box(d, (11, 4.4), 4.0, 2.2, 'BH1750', [('vcc','VCC','T',0.3),('gnd','GND','B',0.3),('sda','SDA','L',0.65),('scl','SCL','L',0.35),('addr','ADDR','R',0.5)], sub='lux, 0x23', tdx=0.1)
    p33(d, L['vcc']); gnd(d, L['gnd'])
    e = stub(d, L['addr'], 'right', 0.6); gnd(d, e)
    xs, xc = 5.4, 6.3
    poly(d, [A['sda'], (xs, A['sda'][1]), (xs, L['sda'][1]), L['sda']])
    poly(d, [A['scl'], (xc, A['scl'][1]), (xc, L['scl'][1]), L['scl']])
    P = box(d, (11, -0.48), 3.4, 2.2, 'HC-SR501', [('vcc','VCC','T',0.3),('gnd','GND','B',0.3),('out','OUT','L',0.5)], sub='PIR motion', tdx=0.4)
    p5(d, P['vcc']); gnd(d, P['gnd'])
    poly(d, [A['g27'], (7.2, A['g27'][1]), (7.2, P['out'][1]), P['out']])
    # level shifter
    U = box(d, (8, -7.2), 4.6, 2.6, 'U1\n74AHCT125', [('vcc','VCC (14)','T',0.5),('gnd','GND (7)','B',0.5),('a','1A (2)','L',0.7),('oe','1OE (1)','L',0.3),('y','1Y (3)','R',0.5)], sub='3.3→5 V', tdy=-0.1, tdx=0.2)
    p5(d, U['vcc']); gnd(d, U['gnd'])
    e = stub(d, U['oe'], 'left', 0.5); gnd(d, e)
    poly(d, [A['g16'], (4.4, A['g16'][1]), (4.4, U['a'][1]), U['a']])
    r = d.add(elm.Resistor().theta(0).at(U['y']).length(2.4).label('330 Ω', fontsize=FS-1))
    S1 = box(d, (r.end[0]+3.0, U['y'][1]), 4.4, 2.6, 'Strip 1', [('v','+5V','T',0.5),('g','GND','B',0.5),('din','DIN','L',0.5),('dout','DOUT','R',0.5)], sub='WS2812B\n60 LEDs')
    poly(d, [r.end, S1['din']])
    S2 = box(d, (S1['dout'][0]+3.4, U['y'][1]), 4.4, 2.6, 'Strip 2', [('v','+5V','T',0.5),('g','GND','B',0.5),('din','DIN','L',0.5)], sub='WS2812B\n60 LEDs')
    poly(d, [S1['dout'], S2['din']])
    for S in (S1, S2): p5(d, S['v'], '+5V inject\n(18 AWG)'); gnd(d, S['g'])
    # bulk cap
    cx = S1['din'][0]-0.9
    c = d.add(elm.Capacitor(polar=True).down().at((S2['din'][0]+6.6, U['y'][1]+1.2)).length(2.4).label('C1 1000 µF 10 V\n(fit at the strip-1\npower input)', loc='bot', fontsize=FS-1))
    p5(d, c.start); gnd(d, c.end)
    title(d, (-3, 7.6), 'Exterior lighting node', 'Dusk + motion lighting: 2 m of WS2812B (120 LEDs) on one data line, lux sensor and PIR. +5V for the strips comes straight from the fused rail, not through the ESP32.')
    note(d, (-3.2, -12), '• ESP32 data is 3.3 V; WS2812B needs ≥ 3.5 V logic at 5 V, so U1 (74AHCT125, powered from 5 V) shifts it up. Tie unused inputs 2A/3A/4A (5, 9, 12)\n'
         '   to GND and their OE pins (4, 10, 13) to +5V. 330 Ω at the first DIN damps ringing; put C1 across +5V/GND at the strip-1 input.\n'
         '• Power the strips from both ends (injection at each strip start). 120 LEDs × 60 mA = 7.2 A at full white, so the firmware caps total\n'
         '   strip current at 3 A (e.g. FastLED setMaxPowerInVoltsAndMilliamps(5, 3000)). Strip and ESP32 grounds must be joined.\n'
         '• BH1750 replaces the bench-test LDR on GPIO34; re-tune lux_threshold (375 on the bench) with the real sensor. ADDR→GND gives 0x23.\n'
         '   The second BH1750 on the order is a spare (or a second sensor at 0x5C with ADDR→3V3).')
    d.save(fn, dpi=200)
if __name__ == '__main__':
    draw('lighting.png')
