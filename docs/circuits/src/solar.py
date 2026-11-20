from common import *
def draw(fn):
  with schemdraw.Drawing(show=False) as d:
    d.config(fontsize=FS, unit=2)
    A = esp32(d, (0, 0), [('sda', 'GPIO21 SDA'), ('scl', 'GPIO22 SCL'), ('g18', 'GPIO18'), ('g19', 'GPIO19')],
              left_pins=[('g32','GPIO32'),('g33','GPIO33'),('g35','GPIO35'),('g39','GPIO39')], h=13)
    names = ['TL','TR','BL','BR']
    for i,(k) in enumerate(['g32','g33','g35','g39']):
        p = A[k]; jx = p[0]-1.6
        poly(d, [p, (jx, p[1])], dots=[(jx, p[1])])
        ldr = d.add(elm.Photoresistor().left().at((jx, p[1])).length(2.4).label(f'LDR {i+1} ({names[i]})', fontsize=FS-1.5))
        d.add(elm.Vdd().at(ldr.end).theta(180).label('3V3', fontsize=FS-1.5).color('#1f5fbf'))
        r = d.add(elm.Resistor().down().at((jx, p[1])).length(1.0).scale(0.6).label('10 k', loc='bot', fontsize=FS-2))
        gnd(d, r.end)
    ip = lambda: [('vcc','VCC','T',0.3),('gnd','GND','B',0.3),('sda','SDA','L',0.65),('scl','SCL','L',0.35),('vp','VIN+','R',0.7),('vm','VIN−','R',0.3)]
    I1 = box(d, (11, 10.0), 4.6, 2.4, 'INA219 #1', ip(), sub='0x40\ntracking', tdx=0)
    I2 = box(d, (11, 5.6), 4.6, 2.4, 'INA219 #2', ip(), sub='0x41 (A0\nbridged), ref.', tdx=0)
    for I, nm in ((I1, 'Tracked panel\n6 V 1–2 W'), (I2, 'Fixed reference\npanel 6 V 1–2 W')):
        p33(d, I['vcc']); gnd(d, I['gnd'])
        px = I['vp'][0] + 3.6; rx = I['vm'][0] + 1.0
        poly(d, [I['vp'], (px, I['vp'][1])])
        pv = d.add(elm.Solar().down().at((px, I['vp'][1])).length(2.6).label(nm, loc='bot', fontsize=FS-1.5).reverse())
        gnd(d, pv.end)
        poly(d, [I['vm'], (rx, I['vm'][1])])
        rl = d.add(elm.Resistor().down().at((rx, I['vm'][1])).length(1.6).label('RL\n22 Ω 3 W', loc='bot', fontsize=FS-1.5))
        gnd(d, rl.end)
    xs, xc = 5.2, 6.1
    poly(d, [A['sda'], (xs, A['sda'][1]), (xs, I1['sda'][1]), I1['sda']])
    poly(d, [A['scl'], (xc, A['scl'][1]), (xc, I1['scl'][1]), I1['scl']])
    poly(d, [(xs, I2['sda'][1]), I2['sda']], dots=[(xs, I2['sda'][1])])
    poly(d, [(xs, A['sda'][1]), (xs, I2['sda'][1])])
    poly(d, [(xc, A['scl'][1]), (xc, I2['scl'][1])])
    poly(d, [(xc, I2['scl'][1]), I2['scl']], dots=[(xc, I2['scl'][1])])
    sv = lambda: [('v','+5V','T',0.5),('g','GND','B',0.5),('sig','SIG','L',0.5)]
    M1 = box(d, (11, -4.6), 3.4, 2.0, 'MG90S pan', sv(), tdx=0.3)
    M2 = box(d, (11, -9.4), 3.4, 2.0, 'MG90S tilt', sv(), tdx=0.3)
    for M in (M1, M2): p5(d, M['v']); gnd(d, M['g'])
    poly(d, [A['g18'], (7.6, A['g18'][1]), (7.6, M1['sig'][1]), M1['sig']])
    poly(d, [A['g19'], (7.0, A['g19'][1]), (7.0, M2['sig'][1]), M2['sig']])
    c = d.add(elm.Capacitor(polar=True).down().at((15.5, -6.2)).length(2.2).label('C2 470 µF 10 V\n(at servo power\nterminal)', loc='bot', fontsize=FS-1.5))
    p5(d, c.start); gnd(d, c.end)
    title(d, (-8, 13.8), 'Solar tracker node', 'Dual-axis tracker: four LDRs behind a cross-shaped shade drive two MG90S servos on the 3D-printed pan/tilt; two INA219s compare tracked vs fixed panel power.')
    note(d, (-8.2, -12.6), '• LDR dividers use ADC1 pins only (GPIO32/33/35/39) because ADC2 stops working with Wi-Fi on. More light = higher voltage. 10 kΩ matches the\n'
         '   bench test; if readings saturate under a bright lamp, drop to 4.7 kΩ to stay in the ESP32\'s linear 0.2–1.9 V window. LDR order: TL, TR, BL, BR.\n'
         '• Servos take power from the +5V rail, never from the ESP32 3V3 pin. 3.3 V signal from GPIO18/19 drives the MG90S directly. C2 absorbs start-up\n'
         '   current spikes (stall ≈ 0.7 A each) that would otherwise brown out the ESP32. Firmware tilt limit ±65° (3D-print clearance check).\n'
         '• Each INA219 sits high-side between its panel and a fixed load resistor RL (22 Ω ≈ near max-power point of a 6 V, 1–2 W panel), so both panels\n'
         '   see the same load and the power comparison is fair. Panel − goes to common GND. Bridge A0 on the second INA219 for address 0x41.')
    d.save(fn, dpi=200)
if __name__ == '__main__':
    draw('solar.png')
