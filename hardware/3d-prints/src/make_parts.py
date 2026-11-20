"""Parametric 3D-print parts for the Smart Home Model (ENEE 3850).

Run:  python3 make_parts.py [outdir]     (needs: pip install manifold3d trimesh)
Every dimension is in millimetres. Servo numbers are typical MG90S/SG90
values; test-print tracker_base first and adjust SERVO_* if the fit is off.
"""
import sys, os
import numpy as np
import trimesh
from manifold3d import Manifold, set_circular_segments

set_circular_segments(64)
OUT = sys.argv[1] if len(sys.argv) > 1 else "stl"
os.makedirs(OUT, exist_ok=True)

# ---------------- shared parameters ----------------
CLR = 0.3                      # printing clearance per side
SERVO_L, SERVO_W = 22.8, 12.4  # MG90S body length (shaft end to wire end), width
SERVO_SHAFT_FROM_END = 5.9     # shaft centre to the near end of the body
SERVO_TAB_UNDER = 15.9         # body bottom to underside of the mounting tabs
SERVO_TAB_T = 2.5              # tab thickness
SERVO_HOLE_PITCH = 27.8        # tab screw hole spacing
SERVO_HORN_FACE = 29.5         # body bottom to outer face of the horn arm
PILOT = 1.8                    # pilot hole for the servo's M2 self-tapping screws
M3 = 3.4                       # M3 clearance
HORN_W, HORN_DEPTH = 6.5, 1.8  # horn-arm pocket width / depth

# solar panel (6 V 1-2 W mini panel, ~110 x 60 mm; measure yours)
PANEL_L, PANEL_W, PANEL_T = 110.0, 60.0, 3.0

def box(x0, x1, y0, y1, z0, z1):
    return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])

def cyl_z(d, z0, z1, x=0, y=0):
    return Manifold.cylinder(z1 - z0, d / 2).translate([x, y, z0])

def cyl_x(d, x0, x1, y=0, z=0):
    return Manifold.cylinder(x1 - x0, d / 2).rotate([0, 90, 0]).translate([x0, y, z])

def save(m, name):
    mesh = m.to_mesh()
    t = trimesh.Trimesh(vertices=np.asarray(mesh.vert_properties)[:, :3],
                        faces=np.asarray(mesh.tri_verts), process=True)
    assert t.is_watertight, name
    t.export(os.path.join(OUT, name + ".stl"))
    print(f"{name:28s} {t.extents.round(1)}  vol {t.volume/1000:.1f} cm3")
    return t

# Servo body y-range relative to its shaft (body runs toward +y)
SY0 = -SERVO_SHAFT_FROM_END
SY1 = SERVO_L - SERVO_SHAFT_FROM_END
HOLE_Y = ((SY0 + SY1) / 2 - SERVO_HOLE_PITCH / 2, (SY0 + SY1) / 2 + SERVO_HOLE_PITCH / 2)
ABOVE_TAB = SERVO_HORN_FACE - SERVO_TAB_UNDER - SERVO_TAB_T   # tab top -> horn face

# =============== 1. tracker_base: pan servo, shaft up at (0,0) ===============
def tracker_base():
    floor_t = 3.0
    top = floor_t + SERVO_TAB_UNDER                     # tabs rest here
    m = box(-25, 25, -20, 31, 0, floor_t)
    m += box(-SERVO_W/2 - 3.5, SERVO_W/2 + 3.5, HOLE_Y[0] - 3.5, HOLE_Y[1] + 3.5, 0, top)
    m -= box(-SERVO_W/2 - CLR, SERVO_W/2 + CLR, SY0 - CLR, SY1 + CLR, floor_t, top + 1)
    for hy in HOLE_Y:
        m -= cyl_z(PILOT, top - 10, top + 1, 0, hy)
    m -= box(-4, 4, SY1 - 1, HOLE_Y[1] + 5, floor_t, floor_t + 7)   # wire exit
    for x in (-20, 20):
        for y in (-15, 26):
            m -= cyl_z(M3, -1, floor_t + 1, x, y)
    return m

# =============== 2. tracker_yoke: sits on the pan horn, carries tilt servo ===============
A = 30.0          # inner face of each yoke arm (|x|)
ARM_T = 4.0
BASE_T = 4.0
AXIS_Z = BASE_T + 25.0   # tilt axis height above the bottom of the yoke
YK_Y0, YK_Y1 = HOLE_Y[0] - 4, HOLE_Y[1] + 4

def tracker_yoke():
    m = box(-A - ARM_T, A + ARM_T, YK_Y0, YK_Y1, 0, BASE_T)
    # left arm: tilt servo goes through it, tabs on the outer face, shaft pointing +x
    left = box(-A - ARM_T, -A, YK_Y0, YK_Y1, 0, AXIS_Z + 9)
    left -= box(-A - ARM_T - 1, -A + 1, SY0 - CLR, SY1 + CLR,
                AXIS_Z - SERVO_W/2 - CLR, AXIS_Z + SERVO_W/2 + CLR)
    for hy in HOLE_Y:
        left -= cyl_x(PILOT, -A - ARM_T - 1, -A + 1, hy, AXIS_Z)
    # right arm: M3 pivot bolt
    right = box(A, A + ARM_T, -8, 8, 0, AXIS_Z + 8)
    right += cyl_x(16, A, A + ARM_T, 0, AXIS_Z)
    right -= cyl_x(M3, A - 1, A + ARM_T + 1, 0, AXIS_Z)
    m = m + left + right
    # gussets
    m += box(-A, -A + 6, YK_Y0, YK_Y0 + 3, BASE_T, BASE_T + 6)
    m += box(A - 6, A, -8, -5, BASE_T, BASE_T + 6)
    # pan horn pocket underneath (double-arm straight horn) + screwdriver hole
    m -= box(-18, 18, -HORN_W/2, HORN_W/2, -1, HORN_DEPTH)
    m -= cyl_z(8.5, -1, HORN_DEPTH + 2)
    m -= cyl_z(6.0, -1, BASE_T + 1)
    return m

# =============== 3. tracker_panel_plate: panel tray + LDR cross divider ===============
EAR_GAP = 26.0                     # tilt axis -> underside of plate
PLATE_T = 3.0
PLATE_Y = PANEL_W / 2 + 3.0
PX0, PX1 = -(PANEL_L / 2 + 5), PANEL_L / 2 + 37    # sensor zone at +x
LDR_CX = PANEL_L / 2 + 20
HORN_FACE_X = -A - ARM_T + ABOVE_TAB              # outer face of tilt horn
L_EAR = (HORN_FACE_X - HORN_DEPTH, HORN_FACE_X - HORN_DEPTH + 5.0)
R_EAR = (A - 5.0, A - 1.0)

FOOT_W = 12.0                      # ear foot that bolts under the plate
EAR_BOLT_Y = (-5.0, 5.0)

def ear_foot_x(x0, x1, inboard):
    return (x1, x1 + FOOT_W) if inboard > 0 else (x0 - FOOT_W, x0)

def ear(x0, x1, inboard):
    """Vertical ear (tilt axis at z = 0) with a foot under the plate."""
    e = box(x0, x1, -8, 8, 0, EAR_GAP)
    e += cyl_x(16, x0, x1, 0, 0)
    f0, f1 = ear_foot_x(x0, x1, inboard)
    e += box(min(f0, x0), max(f1, x1), -8, 8, EAR_GAP - 3.5, EAR_GAP)
    fx = (f0 + f1) / 2
    for y in EAR_BOLT_Y:
        e -= cyl_z(M3, EAR_GAP - 5, EAR_GAP + 1, fx, y)
        e -= Manifold.cylinder(2.6, 3.3, circular_segments=6).translate([fx, y, EAR_GAP - 3.5 - 0.01])  # M3 nut trap
    return e

def left_ear():
    le = ear(*L_EAR, inboard=+1)
    le -= box(L_EAR[0] - 1, L_EAR[0] + HORN_DEPTH, -HORN_W/2, HORN_W/2, -1, 21)   # single-arm horn slot
    le -= cyl_x(8.0, L_EAR[0] - 1, L_EAR[0] + HORN_DEPTH, 0, 0)                   # horn hub
    le -= cyl_x(6.0, L_EAR[0] - 1, L_EAR[1] + 1, 0, 0)                            # horn screw access
    return le

def right_ear():
    return ear(*R_EAR, inboard=-1) - cyl_x(M3, R_EAR[0] - 1, R_EAR[1] + 1, 0, 0)

def tracker_panel_plate(with_ears=False):
    z0 = EAR_GAP
    m = box(PX0, PX1, -PLATE_Y, PLATE_Y, z0, z0 + PLATE_T)
    # rim around panel
    ix, iy = PANEL_L / 2 + 0.5, PANEL_W / 2 + 0.5
    rim = box(-ix - 2, ix + 2, -iy - 2, iy + 2, z0 + PLATE_T, z0 + PLATE_T + PANEL_T - 0.5)
    rim -= box(-ix, ix, -iy, iy, z0, z0 + 20)
    rim -= box(-10, 10, -iy - 3, -iy + 1, z0, z0 + 20)        # finger notch
    m += rim
    m -= box(-6, 6, -4, 4, z0 - 1, z0 + PLATE_T + 1)            # panel lead hole
    for x in (-38, 38):                                        # lightening / tape access
        m -= box(x - 9, x + 9, -12, 12, z0 - 1, z0 + PLATE_T + 1)
    # LDR quad + cross-shaped blinder (Weissbach & Aunkst)
    wall_h, wall_t, half = 22.0, 1.6, 16.0
    m += box(LDR_CX - half, LDR_CX + half, -wall_t/2, wall_t/2, z0 + PLATE_T, z0 + PLATE_T + wall_h)
    m += box(LDR_CX - wall_t/2, LDR_CX + wall_t/2, -half, half, z0 + PLATE_T, z0 + PLATE_T + wall_h)
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = LDR_CX + sx * 6.5, sy * 6.5
            for dx in (-1.7, 1.7):                  # two leads, 3.4 mm pitch
                m -= cyl_z(1.1, z0 - 1, z0 + PLATE_T + 1, cx + dx, cy)
            m -= cyl_z(5.4, z0 + PLATE_T - 1.0, z0 + PLATE_T + 1, cx, cy)  # seat for 5 mm head
    # M3 holes for the two ears' feet
    for (x0, x1), inb in ((L_EAR, +1), (R_EAR, -1)):
        f0, f1 = ear_foot_x(x0, x1, inb)
        for y in EAR_BOLT_Y:
            m -= cyl_z(M3, z0 - 1, z0 + PLATE_T + 1, (f0 + f1) / 2, y)
            m -= cyl_z(6.0, z0 + PLATE_T - 1.5, z0 + PLATE_T + 1, (f0 + f1) / 2, y)  # head recess (panel sits on top)
    if with_ears:
        m += left_ear() + right_ear()
    return m

def tracker_tilt_ears():
    """Both ears laid flat for printing (outer face on the bed)."""
    le = left_ear().rotate([0, -90, 0])
    re = right_ear().rotate([0, 90, 0])
    def to_bed(m, dx):
        b = m.bounding_box()
        return m.translate([dx - b[0], -b[1], -b[2]])
    return to_bed(le, 0) + to_bed(re, 45)

# =============== 4. pir_wall_bezel: HC-SR501 behind a wall cut-out ===============
def pir_wall_bezel():
    t = 3.0
    m = box(-24, 24, -19, 19, 0, t)
    m -= cyl_z(24.0, -1, t + 1)                         # dome window
    for x in (-14.25, 14.25):                           # PCB holes, 28.5 mm apart
        m -= cyl_z(2.2, -1, t + 1, x, 0)
        m += cyl_z(5.0, t, t + 3, x, 0) - cyl_z(1.8, t - 1, t + 4, x, 0)  # standoffs
    for x in (-20, 20):
        for y in (-15, 15):
            m -= cyl_z(3.0, -1, t + 1, x, y)            # #4 wood screws into the wall
            m -= Manifold.cylinder(1.6, 1.5, 3.0).translate([x, y, -0.01])  # countersink
    return m

# =============== 5. climate_fan_heater_bracket ===============
def climate_fan_heater_bracket():
    t = 3.0
    foot = box(-25, 25, 0, 62, 0, t)
    for x in (-19, 19):
        foot -= cyl_z(3.0, -1, t + 1, x, 6)             # screws into the floor
    face = box(-23, 23, 0, t, 0, 46 + t)
    face -= Manifold.cylinder(t + 2, 19).rotate([-90, 0, 0]).translate([0, -1, 23 + t])   # airflow hole
    for x in (-16, 16):
        for z in (-16, 16):
            face -= Manifold.cylinder(t + 2, M3 / 2).rotate([-90, 0, 0]).translate([x, -1, 23 + t + z])
    # heater plate stands edge-on in the airflow, in a groove 8 mm in front of the fan
    rail = box(-4, 4, t + 6, t + 58, t, t + 6)
    rail -= box(-1.1, 1.1, t + 8, t + 59, t + 1.5, t + 7)    # 2.2 mm groove (shim thinner plates)
    m = foot + face + rail
    m += box(-25, -22, t, 20, t, 20) + box(22, 25, t, 20, t, 20)   # side gussets
    return m

# =============== 6. sensor_vent_housing: BME680 / SHT40 ===============
def sensor_vent_housing():
    iw, il, ih, w = 26.0, 32.0, 12.0, 1.8
    m = box(-iw/2 - w, iw/2 + w, -il/2 - w, il/2 + w, 0, ih + w)
    m -= box(-iw/2, iw/2, -il/2, il/2, w, ih + w + 1)          # open top = back against wall
    for i in range(5):                                          # vent slots on both long sides
        y = -il/2 + 5 + i * 5.5
        m -= box(-iw/2 - w - 1, iw/2 + w + 1, y, y + 2.5, w + 3, ih - 1)
    m -= box(-5, 5, il/2 - 1, il/2 + w + 1, ih + w - 5, ih + w + 1)  # cable notch
    m += box(-iw/2, iw/2, -il/2, -il/2 + 1.2, w, w + 4) - box(-iw/2+3, iw/2-3, -il/2-1, -il/2+2, w+1.5, w+5)
    ox = iw/2 + w                                               # wall flanges
    m += box(-ox - 6, -ox + 0.01, -8, 8, ih + w - 2.5, ih + w)
    m += box(ox - 0.01, ox + 6, -8, 8, ih + w - 2.5, ih + w)
    for x in (-iw/2 - w - 3, iw/2 + w + 3):
        m -= cyl_z(3.0, ih + w - 4, ih + w + 1, x, 0)
    return m

parts = {
    "tracker_base": tracker_base(),
    "tracker_yoke": tracker_yoke(),
    "tracker_panel_plate": tracker_panel_plate(),
    "tracker_tilt_ears": tracker_tilt_ears(),
    "pir_wall_bezel": pir_wall_bezel(),
    "climate_fan_heater_bracket": climate_fan_heater_bracket(),
    "sensor_vent_housing": sensor_vent_housing(),
}
meshes = {k: save(v, k) for k, v in parts.items()}

if __name__ == "__main__" and "--check" in sys.argv:
    # Tilt sweep check: plate (axis at its z=0) placed on the yoke's tilt axis.
    yoke = parts["tracker_yoke"]
    tab_x = -A - ARM_T                                   # tab top face (outer face of arm)
    body_top = tab_x + (22.7 - SERVO_TAB_UNDER - SERVO_TAB_T)  # MG90S body height 22.7
    servo_tilt = box(tab_x - SERVO_TAB_UNDER, body_top, SY0, SY1, AXIS_Z - SERVO_W/2, AXIS_Z + SERVO_W/2)
    servo_tilt += cyl_x(5.0, body_top, HORN_FACE_X - HORN_DEPTH - 0.2, 0, AXIS_Z)   # spline under the horn
    for ang in range(-75, 80, 5):
        p = tracker_panel_plate(with_ears=True).rotate([ang, 0, 0]).translate([0, 0, AXIS_Z])
        a, b = (p ^ yoke).volume(), (p ^ servo_tilt).volume()
        print(f"tilt {ang:+4d} deg  plate/yoke {a:7.2f}  plate/servo {b:7.2f} mm3")
