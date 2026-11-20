import schemdraw, schemdraw.elements as elm
schemdraw.use('matplotlib')
FS = 10

def box(d, center, w, h, title, pins, sub=None, color=None, tdx=0, tdy=0):
    """pins: list of (anchorname, label, side, pos 0..1)"""
    p = [elm.IcPin(name=lbl, side=side[0].upper(), pos=pos, anchorname=a, lblsize=FS-1) for a, lbl, side, pos in pins]
    e = elm.Ic(pins=p, size=(w, h), pinlength=0.5, lblsize=FS-1, pinlblsize=FS-1.5)
    if color: e.color(color)
    e = d.add(e.theta(0).at(center).anchor('center'))
    t = title + ('\n' + sub if sub else '')
    c = e.absanchors['center']
    d.add(elm.Label().at((c[0]+tdx, c[1]+tdy)).label(t, fontsize=FS))
    return e.absanchors

def p5(d, at, lbl='+5V', theta=90):
    d.add(elm.Vdd().at(at).theta(theta).label(lbl, fontsize=FS-1))
def p33(d, at, theta=90):
    d.add(elm.Vdd().at(at).theta(theta).label('3V3', fontsize=FS-1).color('#1f5fbf'))
def gnd(d, at):
    d.add(elm.Ground().at(at))
def stub(d, at, direction, length=0.6):
    l = d.add(getattr(elm.Line(), direction)().at(at).length(length))
    return l.end
def wire(d, a, b, shape='-|', **kw):
    return d.add(elm.Wire(shape, **kw).at(a).to(b))
def dot(d, at):
    d.add(elm.Dot().at(at))
def note(d, at, text, fs=FS-1, halign='left', valign='top', color='#333333'):
    d.add(elm.Label().at(at).label(text, fontsize=fs, halign=halign, valign=valign, color=color))
def title(d, at, t, sub):
    d.add(elm.Label().at(at).label(t, fontsize=16, halign='left', valign='bottom'))
    d.add(elm.Label().at((at[0], at[1]-0.35)).label(sub, fontsize=10, halign='left', valign='top', color='#555555'))

def esp32(d, center, right_pins, left_pins=(), h=None, w=6, name='ESP32-WROOM-32\nDevKit'):
    """right/left pins: list of (anchor, label). Returns anchors. Adds VIN/GND/EN power."""
    n = max(len(right_pins), len(left_pins), 4)
    h = h or max(4.5, 0.9 * n + 1.2)
    pins = [('vin', 'VIN (5V)', 'top', 0.25), ('v33', '3V3', 'top', 0.75),
            ('gnd', 'GND', 'bottom', 0.25), ('en', 'EN', 'bottom', 0.75)]
    for i, (a, l) in enumerate(right_pins):
        pins.append((a, l, 'right', 1 - (i + 1) / (len(right_pins) + 1)))
    for i, (a, l) in enumerate(left_pins):
        pins.append((a, l, 'left', 1 - (i + 1) / (len(left_pins) + 1)))
    A = box(d, center, w, h, name, pins, sub='(38-pin screw-\nterminal breakout)', tdx=-w/2+1.6, tdy=0)
    p5(d, A['vin']); gnd(d, A['gnd']); d.add(elm.Vdd().at(A['v33']).label('3V3 out', fontsize=FS-1).color('#1f5fbf'))
    # EN boot-fix cap (bench test note)
    c = d.add(elm.Capacitor(polar=True).at(A['en']).down().length(1.5).label('10 µF', loc='bot', fontsize=FS-1).flip())
    gnd(d, c.end)
    return A

def poly(d, pts, dots=()):
    for a, b in zip(pts, pts[1:]):
        d.add(elm.Line().at(a).to(b))
    for p in dots: dot(d, p)
def fet(d, gate_xy, name='Q1', sub='D4184\nmodule'):
    q = d.add(elm.NFet().theta(0).reverse().at(gate_xy).anchor('gate'))
    note(d, (q.drain[0]+0.35, q.center[1]-0.2), name + '\n' + sub, fs=FS-1.5, valign='center')
    gnd(d, q.source)
    return q
