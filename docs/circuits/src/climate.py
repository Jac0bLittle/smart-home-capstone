from common import *
def draw(fn):
  with schemdraw.Drawing(show=False) as d:
    d.config(fontsize=FS, unit=2)
    A = esp32(d, (0, 0), [('sda', 'GPIO21 SDA'), ('scl', 'GPIO22 SCL'), ('g25', 'GPIO25'), ('g26', 'GPIO26')])
    sp = lambda: [('vcc','VCC','T',0.3),('gnd','GND','B',0.3),('sda','SDA','L',0.65),('scl','SCL','L',0.35)]
    B = box(d, (11, 4.6), 3, 2.2, 'BME680', sp(), sub='addr 0x77', tdx=0.3)
    S = box(d, (11, -0.4), 3, 2.2, 'SHT40', sp(), sub='addr 0x44', tdx=0.3)
    for P in (B, S): p33(d, P['vcc']); gnd(d, P['gnd'])
    xs, xc = 5.5, 6.5
    poly(d, [A['sda'], (xs, A['sda'][1]), (xs, B['sda'][1]), B['sda']])
    poly(d, [(xs, S['sda'][1]), S['sda']], dots=[(xs, S['sda'][1])])
    poly(d, [(xs, A['sda'][1]), (xs, S['sda'][1])]) if S['sda'][1] < A['sda'][1] else None
    poly(d, [A['scl'], (xc, A['scl'][1]), (xc, B['scl'][1]), B['scl']])
    poly(d, [(xc, S['scl'][1]), S['scl']], dots=[(xc, S['scl'][1])])
    # power stages below
    g = -8.5
    q1 = fet(d, (8, g), 'Q1')
    h = d.add(elm.Resistor().up().at(q1.drain).length(2.4).label('Heater film\n5 V 6.2 W\n≈4 Ω, 1.24 A', loc='bot', fontsize=FS-1))
    t = d.add(elm.Button(nc=True).up().at(h.end).length(2.2).label('KSD9700\n50 °C NC\n(on heater plate)', loc='bot', fontsize=FS-1))
    p5(d, t.end)
    poly(d, [A['g25'], (4.5, A['g25'][1]), (4.5, g), q1.gate])
    q2 = fet(d, (15, g), 'Q2')
    m = d.add(elm.Motor().up().at(q2.drain).length(2.4).label('40 mm fan\n5 V', loc='bot', fontsize=FS-1))
    l = d.add(elm.Line().up().at(m.end).length(1.2)); p5(d, l.end)
    poly(d, [m.start, (m.start[0]-1.6, m.start[1])])
    dd = d.add(elm.Schottky().up().at((m.start[0]-1.6, m.start[1])).to((m.start[0]-1.6, m.end[1])).reverse().label('1N5819\nflyback', loc='top', fontsize=FS-1.5))
    poly(d, [(m.start[0]-1.6, m.end[1]), m.end], dots=[m.start, m.end])
    poly(d, [A['g26'], (3.8, A['g26'][1]), (3.8, g-2.3), (13, g-2.3), (13, g), q2.gate])
    title(d, (-3, 8.3), 'Climate node', 'Thermostat: heater + fan, two temperature sensors. +5V comes from the shared fused 10 A rail (see power diagram); all grounds common.')
    note(d, (-3.2, -13), '• BME680 and SHT40 share one I2C bus (GPIO21/22); the breakouts carry their own pull-ups and run from 3V3.\n'
         '• KSD9700 opens at 50 °C and cuts heater current in hardware, even if the ESP32 or Q1 fails ON. Mount it touching the heater plate.\n'
         '• Firmware also cuts the heater above 40 °C, after 15 min ON, and when the hub is lost in manual mode.\n'
         '• D4184 modules have an on-board gate resistor and pull-down, so heater and fan stay OFF while the ESP32 boots.\n'
         '• Fan speed PWM: keep ≤ 1 kHz if the module has an optocoupler input, or just switch the fan on/off.\n'
         '• 10 µF EN–GND lets the board enter upload mode by itself (the "Wrong boot mode" issue from the bench test).')
    d.save(fn, dpi=200)
if __name__ == '__main__':
    draw('climate.png')
