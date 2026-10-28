"""Ikony ekranu powitalnego — te same oryginalne rysunki wektorowe co w środowisku Horyzont
(logo ze wschodzącym słońcem, obrazy kont, przyciski zasilania), renderowane do QPixmap.
"""
from functools import lru_cache

_uid = [0]


def _id(prefix):
    _uid[0] += 1
    return f"{prefix}{_uid[0]}"


def _stops(stops):
    out = []
    for st in stops:
        o, c = st[0], st[1]
        op = ' stop-opacity="%s"' % st[2] if len(st) > 2 else ""
        out.append('<stop offset="%s" stop-color="%s"%s/>' % (o, c, op))
    return "".join(out)


def lg(stops, x1=0, y1=0, x2=0, y2=1, units="objectBoundingBox"):
    gid = _id("g")
    st = _stops(stops)
    return gid, f'<linearGradient id="{gid}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" gradientUnits="{units}">{st}</linearGradient>'


def rg(stops, cx=0.5, cy=0.5, r=0.5, fx=None, fy=None):
    gid = _id("r")
    st = _stops(stops)
    fxy = f' fx="{fx}" fy="{fy}"' if fx is not None else ""
    return gid, f'<radialGradient id="{gid}" cx="{cx}" cy="{cy}" r="{r}"{fxy}>{st}</radialGradient>'


class S:
    """Pomocnik do składania dokumentu SVG."""

    def __init__(self):
        self.defs = []
        self.body = []

    def grad(self, g):
        gid, d = g
        self.defs.append(d)
        return f"url(#{gid})"

    def add(self, s):
        self.body.append(s)
        return self

    def svg(self):
        return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">'
                f'<defs>{"".join(self.defs)}</defs>{"".join(self.body)}</svg>')


def shadow(s, cx=24, cy=44, rx=18, ry=2.6, op=0.28):
    f = s.grad(rg([(0, "#000", op), (1, "#000", 0)]))
    s.add(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{f}"/>')


def round_badge(s, c1, c2, cx=24, cy=24, r=18, stroke="#0b3f6c"):
    shadow(s, cy=44, rx=14)
    g = s.grad(rg([(0, c1), (1, c2)], 0.4, 0.3, 0.75))
    s.add(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{g}" stroke="{stroke}" stroke-width="1"/>')
    gl = s.grad(lg([(0, "#fff", 0.7), (1, "#fff", 0)]))
    s.add(f'<ellipse cx="{cx}" cy="{cy - r*0.45}" rx="{r*0.7}" ry="{r*0.42}" fill="{gl}"/>')


def icon_help():
    s = S(); round_badge(s, "#8fd3f4", "#1c6fae")
    s.add('<path d="M18.5 18.5 Q18.5 12 24.5 12 Q30.5 12 30.5 17.5 Q30.5 21 26.5 23 Q24.5 24 24.5 27.5" fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round"/>')
    s.add('<circle cx="24.5" cy="34" r="2.7" fill="#fff"/>')
    return s.svg()


def icon_shutdown():
    s = S(); shadow(s)
    g = s.grad(lg([(0, "#ff8a6a"), (1, "#c0321a")]))
    s.add(f'<rect x="6" y="6" width="36" height="36" rx="7" fill="{g}" stroke="#7a1606" stroke-width="1"/>')
    gl = s.grad(lg([(0, "#fff", 0.6), (1, "#fff", 0)]))
    s.add(f'<rect x="8" y="8" width="32" height="15" rx="6" fill="{gl}"/>')
    s.add('<path d="M17.5 16.5 A10 10 0 1 0 30.5 16.5" fill="none" stroke="#fff" stroke-width="3.4" stroke-linecap="round"/>')
    s.add('<path d="M24 11 V24" stroke="#fff" stroke-width="3.4" stroke-linecap="round"/>')
    return s.svg()


def icon_restart():
    s = S(); shadow(s)
    g = s.grad(lg([(0, "#7fe0a8"), (1, "#1f8a5b")]))
    s.add(f'<rect x="6" y="6" width="36" height="36" rx="7" fill="{g}" stroke="#0e5a36" stroke-width="1"/>')
    gl = s.grad(lg([(0, "#fff", 0.6), (1, "#fff", 0)]))
    s.add(f'<rect x="8" y="8" width="32" height="15" rx="6" fill="{gl}"/>')
    s.add('<path d="M32 18 A10 10 0 1 0 34 26" fill="none" stroke="#fff" stroke-width="3.4" stroke-linecap="round"/>')
    s.add('<path d="M27 17 H33.5 V10.5" fill="none" stroke="#fff" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"/>')
    return s.svg()


def icon_standby():
    s = S(); shadow(s)
    g = s.grad(lg([(0, "#ffe27a"), (1, "#d9a21c")]))
    s.add(f'<rect x="6" y="6" width="36" height="36" rx="7" fill="{g}" stroke="#7a5606" stroke-width="1"/>')
    gl = s.grad(lg([(0, "#fff", 0.6), (1, "#fff", 0)]))
    s.add(f'<rect x="8" y="8" width="32" height="15" rx="6" fill="{gl}"/>')
    s.add('<path d="M28 13 A11 11 0 1 0 35 31 A9 9 0 0 1 28 13 Z" fill="#fff"/>')
    return s.svg()


def sun_logo(s, cx=24, cy=24, r=20):
    """Własne logo środowiska: słońce wschodzące nad linią horyzontu."""
    import math
    g = s.grad(rg([(0, "#fff6c8"), (0.5, "#ffc13a"), (1, "#e8701c")], 0.45, 0.4, 0.6))
    rays = []
    for i in range(12):
        a = math.pi * 2 * i / 12
        x1, y1 = cx + math.cos(a) * r * 0.62, cy + math.sin(a) * r * 0.62
        x2, y2 = cx + math.cos(a) * r * 0.98, cy + math.sin(a) * r * 0.98
        rays.append(f'<path d="M{x1:.2f} {y1:.2f} L{x2:.2f} {y2:.2f}" stroke="#ffcf4a" stroke-width="{r*0.13:.2f}" stroke-linecap="round"/>')
    s.add("".join(rays))
    s.add(f'<circle cx="{cx}" cy="{cy}" r="{r*0.5:.2f}" fill="{g}" stroke="#b8501a" stroke-width="{max(0.6, r*0.04):.2f}"/>')
    s.add(f'<path d="M{cx - r*0.5:.2f} {cy + r*0.12:.2f} H{cx + r*0.5:.2f}" stroke="#fff" stroke-width="{r*0.07:.2f}" opacity="0.85"/>')
    s.add(f'<path d="M{cx - r*0.42:.2f} {cy + r*0.27:.2f} H{cx + r*0.42:.2f}" stroke="#fff" stroke-width="{r*0.06:.2f}" opacity="0.65"/>')


def icon_logo():
    s = S(); sun_logo(s); return s.svg()


def avatar(bg1, bg2, content):
    s = S()
    g = s.grad(lg([(0, bg1), (1, bg2)]))
    s.add(f'<rect x="0" y="0" width="48" height="48" fill="{g}"/>')
    content(s)
    return s.svg()


def _kite(s):
    s.add('<path d="M28 6 L40 18 L28 34 L16 18 Z" fill="#e8483a" stroke="#7a1606" stroke-width="1"/>')
    s.add('<path d="M28 6 V34 M16 18 H40" stroke="#ffd34d" stroke-width="1.4"/>')
    s.add('<path d="M28 34 Q24 40 28 44 Q32 47 26 48" fill="none" stroke="#5a3a1c" stroke-width="1"/>')
    for x, y in ((25, 39), (29, 44)):
        s.add(f'<path d="M{x-2} {y} L{x+2} {y-1} L{x+2} {y+1} Z" fill="#2a8a96"/>')
    s.add('<ellipse cx="10" cy="10" rx="7" ry="3" fill="#fff" opacity="0.8"/>')


def _boat(s):
    s.add('<rect x="0" y="32" width="48" height="16" fill="#1f6f9a"/>')
    s.add('<path d="M0 36 Q6 34 12 36 T24 36 T36 36 T48 36" fill="none" stroke="#9fd4f2" stroke-width="1"/>')
    s.add('<path d="M24 6 V30 L10 30 Z" fill="#fff" stroke="#46525c" stroke-width="0.8"/><path d="M26 10 V30 L38 30 Z" fill="#f0a030" stroke="#46525c" stroke-width="0.8"/>')
    s.add('<path d="M8 31 H40 L36 37 H12 Z" fill="#8a3a1c"/>')


def _flower(s):
    s.add('<path d="M24 26 Q22 38 26 48" stroke="#2f7a3a" stroke-width="2.4" fill="none"/>')
    s.add('<path d="M25 38 Q32 32 38 36 Q31 41 25 38 Z" fill="#3f9f4a"/>')
    for a in range(0, 360, 36):
        s.add(f'<ellipse cx="24" cy="12" rx="4" ry="8" fill="#ffd34d" stroke="#c88a10" stroke-width="0.6" transform="rotate({a} 24 20)"/>')
    s.add('<circle cx="24" cy="20" r="6" fill="#7a4a24"/>')


def _cat(s):
    s.add('<circle cx="38" cy="10" r="6" fill="#fff6c8"/>')
    s.add('<path d="M10 48 Q8 30 18 26 L16 16 L22 22 Q26 21 30 22 L36 16 L34 26 Q42 30 40 48 Z" fill="#2b2f36"/>')
    s.add('<circle cx="21" cy="29" r="1.6" fill="#ffd34d"/><circle cx="29" cy="29" r="1.6" fill="#ffd34d"/>')


def _guitar(s):
    s.add('<path d="M30 4 L34 8 L22 24" stroke="#3a2a1a" stroke-width="3" stroke-linecap="round"/>')
    s.add('<path d="M22 22 Q30 26 28 34 Q26 44 16 44 Q6 44 6 34 Q6 26 14 26 Q18 20 22 22 Z" fill="#c8701c" stroke="#5a3010" stroke-width="1"/>')
    s.add('<circle cx="17" cy="33" r="3.4" fill="#2b1a0a"/>')


def _planet(s):
    for x, y in ((6, 8), (40, 6), (36, 40), (8, 38), (20, 4)):
        s.add(f'<circle cx="{x}" cy="{y}" r="0.9" fill="#fff"/>')
    g = s.grad(rg([(0, "#ffd9a8"), (1, "#c8701c")], 0.4, 0.35, 0.7))
    s.add(f'<circle cx="24" cy="24" r="12" fill="{g}"/>')
    s.add('<ellipse cx="24" cy="24" rx="21" ry="5.5" fill="none" stroke="#9fd4f2" stroke-width="2" transform="rotate(-20 24 24)"/>')


def icon_avatar_kite():
    return avatar("#8fd3f4", "#d9f2ff", _kite)


def icon_avatar_boat():
    return avatar("#ffd9a8", "#9fd4f2", _boat)


def icon_avatar_flower():
    return avatar("#9fd4f2", "#e6f7ff", _flower)


def icon_avatar_cat():
    return avatar("#3a3f6a", "#8a6aa8", _cat)


def icon_avatar_guitar():
    return avatar("#f6e6c8", "#e0b878", _guitar)


def icon_avatar_planet():
    return avatar("#0e1a3a", "#2a3a6a", _planet)


AVATARS = ["kite", "boat", "flower", "cat", "guitar", "planet"]


def person(s, x, y, sc, c1, c2):
    g = s.grad(lg([(0, c1), (1, c2)]))
    s.add(f'<g transform="translate({x} {y}) scale({sc})">'
          f'<circle cx="12" cy="8" r="7" fill="#f5cfa8" stroke="#8a5a30" stroke-width="0.9"/>'
          f'<path d="M5 6 Q6 0 12 0.5 Q19 0 19.5 7 Q16 3.5 12 4 Q8 4 5 6 Z" fill="#6a4020"/>'
          f'<path d="M0 30 Q0 17 12 17 Q24 17 24 30 Z" fill="{g}" stroke="#2a3a44" stroke-width="0.9"/></g>')


def icon_user():
    s = S(); shadow(s, rx=12)
    person(s, 11, 8, 1.1, "#5ec3cf", "#1f6f78")
    return s.svg()


def icon_users():
    s = S(); shadow(s)
    person(s, 20, 8, 1.0, "#f0a030", "#b8661a")
    person(s, 4, 13, 1.05, "#5ec3cf", "#1f6f78")
    return s.svg()


def icon_key():
    s = S(); shadow(s)
    g = s.grad(lg([(0, "#ffe08a"), (1, "#d18a12")], 0, 0, 1, 1))
    s.add(f'<circle cx="15" cy="17" r="10" fill="{g}" stroke="#7a4a06" stroke-width="1.2"/>')
    s.add('<circle cx="12.5" cy="14.5" r="3.2" fill="#fff8e0" stroke="#7a4a06" stroke-width="1"/>')
    s.add(f'<path d="M21.5 23.5 L40 42 L43 39 L40 36 L42.5 33.5 L39.5 30.5 L37 33 L35 31 L37.5 28.5 L34.5 25.5 L32 28 L25 21 Z" '
          f'fill="{g}" stroke="#7a4a06" stroke-width="1.1" stroke-linejoin="round"/>')
    return s.svg()

def icon_hibernate():
    s = S(); shadow(s)
    g = s.grad(lg([(0, "#9fc8f4"), (1, "#2a5fae")]))
    s.add(f'<rect x="6" y="6" width="36" height="36" rx="7" fill="{g}" stroke="#0b2f6c" stroke-width="1"/>')
    gl = s.grad(lg([(0, "#fff", 0.6), (1, "#fff", 0)]))
    s.add(f'<rect x="8" y="8" width="32" height="15" rx="6" fill="{gl}"/>')
    s.add('<path d="M15 14 H25 L15 26 H25" fill="none" stroke="#fff" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>')
    s.add('<path d="M27 24 H34 L27 32 H34" fill="none" stroke="#fff" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round" opacity="0.85"/>')
    return s.svg()


ICONS = {name[5:]: fn for name, fn in list(globals().items()) if name.startswith("icon_") and callable(fn)}


@lru_cache(maxsize=None)
def svg_for(name):
    fn = ICONS.get(name) or ICONS["user"]
    return fn()


_pix = {}


def pixmap(name, size):
    """QPixmap ikony w podanym rozmiarze (z uwzględnieniem skalowania ekranu)."""
    from PySide6.QtCore import QByteArray, QRectF, Qt
    from PySide6.QtGui import QGuiApplication, QPainter, QPixmap
    from PySide6.QtSvg import QSvgRenderer
    dpr = 1.0
    app = QGuiApplication.instance()
    if app is not None and app.primaryScreen() is not None:
        dpr = app.primaryScreen().devicePixelRatio()
    key = (name, size, dpr)
    pm = _pix.get(key)
    if pm is None:
        px = max(1, round(size * dpr))
        pm = QPixmap(px, px)
        pm.fill(Qt.transparent)
        r = QSvgRenderer(QByteArray(svg_for(name).encode("utf-8")))
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        r.render(p, QRectF(0, 0, px, px))
        p.end()
        pm.setDevicePixelRatio(dpr)
        _pix[key] = pm
    return pm
