"""Kolory, czcionki i rysowanie elementów w stylu Horyzontu."""
import glob
import os

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QFont, QFontDatabase, QLinearGradient, QPainter, QPainterPath, QPen,
                           QRadialGradient)

# Schematy: te same barwy co wbudowany styl Horyzontu (morski, grafitowy, śliwkowy) i dodatkowy niebieski.
SCHEMES = {
    "teal": {"band": ("#0d4f59", "#093f47"), "mid": "#1c7e8a", "glow": "#79d3db", "mid_dark": "#14636e",
             "accent": "#1f8591", "accent_dark": "#0f5d67", "accent_darker": "#0b4a52", "accent_light": "#5cc6d0",
             "tile": "#0b4a52", "line": "#cfeff2"},
    "graphite": {"band": ("#3a4652", "#2b343d"), "mid": "#5d6d7c", "glow": "#b8c6d2", "mid_dark": "#4b5a68",
                 "accent": "#4b5a68", "accent_dark": "#33404c", "accent_darker": "#26303a", "accent_light": "#8fa2b3",
                 "tile": "#2b343d", "line": "#e2e8ee"},
    "plum": {"band": ("#4a2f66", "#3a2452"), "mid": "#76549a", "glow": "#cdb4e6", "mid_dark": "#5d4080",
             "accent": "#6c4a8c", "accent_dark": "#4e3368", "accent_darker": "#3d2752", "accent_light": "#b394d0",
             "tile": "#3a2452", "line": "#efe4f8"},
    "blue": {"band": ("#123f8f", "#0c3277"), "mid": "#4a74cc", "glow": "#a8c6f6", "mid_dark": "#3a62b6",
             "accent": "#2f62c0", "accent_dark": "#1d4a9c", "accent_darker": "#143a80", "accent_light": "#8fb4ee",
             "tile": "#143a80", "line": "#dbe8ff"},
}
AMBER = ("#ffd38a", "#f6ad3e", "#e8901f", "#d47a12", "#c06a0c")
GREEN = ("#9ff0a8", "#4fc85d", "#2f9d3e", "#1f7a2c")

_family = None


def scheme(name):
    return SCHEMES.get(name) or SCHEMES["teal"]


def font_family():
    """Tahoma (z pakietu Wine, jak w Horyzoncie), a gdy jej nie ma — DejaVu Sans."""
    global _family
    if _family:
        return _family
    fams = set(QFontDatabase.families())
    if "Tahoma" not in fams:
        for d in ("/usr/share/wine/fonts", "/usr/share/fonts/wine-tahoma-fonts", "/usr/share/fonts/wine-tahoma",
                  "/usr/local/share/fonts"):
            for f in glob.glob(os.path.join(d, "tahoma*.ttf")) + glob.glob(os.path.join(d, "Tahoma*.ttf")):
                QFontDatabase.addApplicationFont(f)
        fams = set(QFontDatabase.families())
    for cand in ("Tahoma", "DejaVu Sans", "Noto Sans", "Liberation Sans"):
        if cand in fams:
            _family = cand
            return cand
    _family = "Sans Serif"
    return _family


def font(px, bold=False, italic=False):
    f = QFont(font_family())
    f.setPixelSize(max(8, int(round(px))))
    f.setBold(bold)
    f.setItalic(italic)
    f.setHintingPreference(QFont.PreferNoHinting)
    return f


def vgrad(rect, stops):
    g = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    for pos, c in stops:
        g.setColorAt(pos, QColor(c))
    return g


def hgrad(rect, stops):
    g = QLinearGradient(rect.topLeft(), rect.topRight())
    for pos, c in stops:
        g.setColorAt(pos, QColor(c))
    return g


def rounded(rect, r):
    path = QPainterPath()
    path.addRoundedRect(QRectF(rect), r, r)
    return path


def with_alpha(c, a):
    c = QColor(c)
    c.setAlpha(a)
    return c


def paint_background(p, rect, sc, top_h, bottom_h, divider_x=None):
    """Tło ekranu powitalnego: ciemne pasy u góry i u dołu, jaśniejszy środek z poświatą,
    jasna linia pod górnym pasem, bursztynowa nad dolnym i pionowy rozdzielacz."""
    p.save()
    w, h = rect.width(), rect.height()
    top = QRectF(0, 0, w, top_h)
    bottom = QRectF(0, h - bottom_h, w, bottom_h)
    mid = QRectF(0, top_h, w, h - top_h - bottom_h)
    p.fillRect(top, vgrad(top, [(0, sc["band"][1]), (1, sc["band"][0])]))
    p.fillRect(bottom, vgrad(bottom, [(0, sc["band"][0]), (1, sc["band"][1])]))
    p.fillRect(mid, QColor(sc["mid"]))
    # poświata w lewej górnej części (jak światło wschodzącego słońca)
    g = QRadialGradient(QPointF(w * 0.18, top_h + mid.height() * 0.05), max(w, h) * 0.55)
    g.setColorAt(0, with_alpha(sc["glow"], 150))
    g.setColorAt(0.45, with_alpha(sc["glow"], 45))
    g.setColorAt(1, with_alpha(sc["glow"], 0))
    p.fillRect(mid, g)
    # lekkie przyciemnienie u dołu środka
    shade = QRectF(0, mid.bottom() - mid.height() * 0.35, w, mid.height() * 0.35)
    p.fillRect(shade, vgrad(shade, [(0, with_alpha(sc["mid_dark"], 0)), (1, with_alpha(sc["mid_dark"], 160))]))
    # linie oddzielające
    lh = max(2.0, h / 384)
    line = QRectF(0, top_h - lh, w, lh)
    p.fillRect(line, hgrad(line, [(0, with_alpha(sc["line"], 40)), (0.35, with_alpha(sc["line"], 230)),
                                  (0.8, with_alpha(sc["line"], 120)), (1, with_alpha(sc["line"], 0))]))
    line = QRectF(0, h - bottom_h, w, lh)
    p.fillRect(line, hgrad(line, [(0, with_alpha(AMBER[2], 0)), (0.3, with_alpha(AMBER[1], 255)),
                                  (0.7, with_alpha(AMBER[0], 220)), (1, with_alpha(AMBER[2], 0))]))
    if divider_x is not None:
        r = QRectF(divider_x, top_h + mid.height() * 0.08, 1.2, mid.height() * 0.84)
        p.fillRect(r, vgrad(r, [(0, "#00ffffff"), (0.5, "#c8ffffff"), (1, "#00ffffff")]))
    p.restore()


def paint_glossy_button(p, rect, colors, border, radius=4, pressed=False, hover=False):
    """Zaokrąglony przycisk z połyskiem (strzałka logowania, „?”, przycisk zasilania)."""
    p.save()
    p.setRenderHint(QPainter.Antialiasing)
    rect = QRectF(rect)
    cols = list(colors)
    if pressed:
        cols = cols[::-1]
    elif hover:
        cols = [QColor(c).lighter(112).name() for c in cols]
    stops = [(i / (len(cols) - 1), c) for i, c in enumerate(cols)]
    path = rounded(rect, radius)
    p.fillPath(path, vgrad(rect, stops))
    gl = QRectF(rect.left() + 1.5, rect.top() + 1.5, rect.width() - 3, rect.height() * 0.45)
    p.fillPath(rounded(gl, max(1, radius - 1)), vgrad(gl, [(0, "#a0ffffff"), (1, "#10ffffff")]))
    p.setPen(QPen(QColor(border), 1.2))
    p.setBrush(Qt.NoBrush)
    p.drawPath(path)
    p.restore()


def paint_arrow(p, rect, color="#ffffff"):
    p.save()
    p.setRenderHint(QPainter.Antialiasing)
    r = QRectF(rect)
    cx, cy, s = r.center().x(), r.center().y(), min(r.width(), r.height())
    path = QPainterPath()
    path.moveTo(cx - s * 0.30, cy - s * 0.09)
    path.lineTo(cx + 0.02 * s, cy - s * 0.09)
    path.lineTo(cx + 0.02 * s, cy - s * 0.27)
    path.lineTo(cx + s * 0.32, cy)
    path.lineTo(cx + 0.02 * s, cy + s * 0.27)
    path.lineTo(cx + 0.02 * s, cy + s * 0.09)
    path.lineTo(cx - s * 0.30, cy + s * 0.09)
    path.closeSubpath()
    p.setPen(QPen(QColor(0, 0, 0, 70), 1))
    p.setBrush(QColor(color))
    p.drawPath(path)
    p.restore()


def stylesheet(sc, k=1.0):
    """Arkusz stylów dla zwykłych kontrolek (pola tekstowe, przyciski, listy) w oknach dialogowych."""
    fs = int(round(12 * k))
    return f"""
    QWidget {{ font-family: "{font_family()}"; font-size: {fs}px; }}
    QLineEdit {{ background: #ffffff; color: #000000; border: 1px solid #7f9db9; padding: {int(3*k)}px {int(4*k)}px;
                selection-background-color: {sc['accent']}; selection-color: #ffffff; }}
    QLineEdit:focus {{ border: 1px solid {sc['accent']}; }}
    QPushButton {{ color: #000000; min-width: {int(70*k)}px; min-height: {int(20*k)}px; padding: {int(2*k)}px {int(10*k)}px;
                  border: 1px solid {sc['accent_darker']}; border-radius: 3px;
                  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ffffff, stop:0.85 #ecebe6, stop:1 #d6d0c5); }}
    QPushButton:hover {{ border: 1px solid #e8901f; }}
    QPushButton:pressed {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #e3e2da, stop:1 #f2f1ec); }}
    QPushButton:default {{ border: 2px solid {sc['accent']}; }}
    QPushButton:focus {{ border: 2px solid {sc['accent_light']}; }}
    QComboBox {{ background: #ffffff; color: #000000; border: 1px solid #7f9db9; padding: {int(2*k)}px {int(4*k)}px; }}
    QComboBox QAbstractItemView {{ background: #ffffff; color: #000000; selection-background-color: {sc['accent']};
                                  selection-color: #ffffff; }}
    QLabel {{ color: #000000; }}
    QMenu {{ background: #ffffff; color: #000000; border: 1px solid #8a9aa6; padding: 2px; }}
    QMenu::item {{ padding: {int(4*k)}px {int(22*k)}px {int(4*k)}px {int(22*k)}px; }}
    QMenu::item:selected {{ background: {sc['accent']}; color: #ffffff; }}
    QMenu::indicator {{ width: {int(12*k)}px; height: {int(12*k)}px; left: {int(5*k)}px; }}
    QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; border: none; }}
    QScrollBar:vertical {{ background: transparent; width: {int(10*k)}px; margin: 0; }}
    QScrollBar::handle:vertical {{ background: rgba(255,255,255,90); border-radius: {int(4*k)}px; min-height: 30px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
    """
