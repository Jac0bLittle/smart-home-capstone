from common import *
def draw(fn):
  with schemdraw.Drawing(show=False) as d:
    d.config(fontsize=FS, unit=2)
    A = esp32(d, (0, 0), [('g27', 'GPIO27'), ('g26', 'GPIO26'), ('g25', 'GPIO25')])
    P = box(d, (11, 4.2), 3.4, 2.2, 'HC-SR501', [('vcc','VCC','T',0.3),('gnd','GND','B',0.3),('out','OUT','L',0.5)], sub='PIR motion', tdx=0.4)
    p5(d, P['vcc']); gnd(d, P['gnd'])
    poly(d, [A['g27'], (5.0, A['g27'][1]), (5.0, P['out'][1]), P['out']])
    # reed switch with pull-up
    x = 8.5; y = A['g26'][1]
    poly(d, [A['g26'], (x, y)], dots=[(x, y)])
    r = d.add(elm.Resistor().up().at((x, y)).length(2.2).label('10 kΩ\npull-up', loc='bot', fontsize=FS-1))
    p33(d, r.end)
    poly(d, [(x, y), (x+2, y)])
    s = d.add(elm.SwitchReed().down().at((x+2, y)).length(2.4).label('MC-38 reed\n(NC: closed\nwhen door shut)', loc='bot', fontsize=FS-1))
    gnd(d, s.end)
    # buzzer
    g = -7
    q = fet(d, (12.5, g), 'Q3')
    dr = q.drain
    Bz = box(d, (dr[0], dr[1]+1.6), 2.6, 2.0, 'BZ1', [('p','+','T',0.5),('m','−','B',0.5)], sub='SFM-27 buzzer\n3–24 V active')
    p5(d, Bz['p'])
    poly(d, [Bz['m'], dr])
    poly(d, [A['g25'], (4.2, A['g25'][1]), (4.2, g), q.gate])
    title(d, (-3, 7.6), 'Security alarm node', 'PIR motion + door reed switch; buzzer sounds after two detections while armed. +5V from the shared fused rail; all grounds common.')
    note(d, (-3.2, -10.5), '• HC-SR501 runs from 5 V but its OUT is 3.3 V, so it goes straight to GPIO27 (no divider). Set its jumper to repeat-trigger (H).\n'
         '• Reed wired switch-to-GND with a 10 kΩ pull-up: door shut = LOW, door open = HIGH (what the firmware expects). A cut wire also\n'
         '   reads "open", so tampering trips the alarm. Final firmware: change halInputPulldown(PIN_DOOR) to INPUT for GPIO26.\n'
         '• The buzzer draws ~15–30 mA, more than a GPIO should supply, so it switches through a third D4184 module (Q3).\n'
         '• The bench-test Nano simulator used 1 k/2 k dividers on GPIO26/27; remove those for the final build.\n'
         '• MQ-2 gas sensor is not on the order list, so it is not drawn. Re-add on GPIO34 (ADC1) through a 1:2 divider if approved.')
    d.save(fn, dpi=200)
if __name__ == '__main__':
    draw('alarm.png')
