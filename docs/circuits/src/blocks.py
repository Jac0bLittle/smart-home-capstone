import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
RED, BLK, AC, USB, NET, WIFI = '#c62828', '#222222', '#6a1b9a', '#1565c0', '#2e7d32', '#ef6c00'
def fig(w, h):
    f, ax = plt.subplots(figsize=(w, h)); ax.set_xlim(0, w); ax.set_ylim(0, h); ax.axis('off'); return f, ax
def box(ax, x, y, w, h, title, sub='', fc='#f5f5f5', ec='#333', fs=10):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.02,rounding_size=0.08', fc=fc, ec=ec, lw=1.4))
    n = sub.count('\n') + 1 if sub else 0
    if n >= 2 and h > 0.9:
        ax.text(x + w/2, y + h - 0.12, title, ha='center', va='top', fontsize=fs, weight='bold')
        ax.text(x + w/2, y + h - 0.12 - fs*0.028, sub, ha='center', va='top', fontsize=fs-2, color='#444', linespacing=1.25)
    else:
        ax.text(x + w/2, y + h/2 + ((0.35 if h > 1.5 else 0.13) if sub else 0), title, ha='center', va='center', fontsize=fs, weight='bold')
        if sub: ax.text(x + w/2, y + h/2 - (0.3 if h > 1.5 else 0.17), sub, ha='center', va='center', fontsize=fs-2, color='#444', linespacing=1.1)
    return dict(l=(x, y+h/2), r=(x+w, y+h/2), t=(x+w/2, y+h), b=(x+w/2, y), x=x, y=y, w=w, h=h)
def line(ax, pts, c=BLK, lw=2, ls='-', label=None, lpos=0.5, loff=(0, 0.1), fs=8, arrow=False):
    xs, ys = zip(*pts); ax.plot(xs, ys, color=c, lw=lw, ls=ls, solid_capstyle='round')
    if arrow:
        ax.annotate('', xy=pts[-1], xytext=pts[-2], arrowprops=dict(arrowstyle='-|>', color=c, lw=lw))
    if label:
        i = min(int(lpos*(len(pts)-1)), len(pts)-2); a, b = pts[i], pts[i+1]
        ax.text((a[0]+b[0])/2+loff[0], (a[1]+b[1])/2+loff[1], label, color=c, fontsize=fs, ha='center', va='bottom')
