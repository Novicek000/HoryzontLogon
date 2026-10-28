"""Kontrolki ekranu powitalnego: kafelek konta, przyciski, dymek, nakładki (okna na środku ekranu)."""
import glob
import os

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QLabel, QLineEdit, QPushButton, QWidget

from .. import icons
from ..i18n import T
from . import style
from .style import AMBER, GREEN, font, hgrad, rounded, vgrad, with_alpha


def account_pixmap(account, size, index=0):
    """Obraz konta z AccountsService / ~/.face; bez niego — rysunek Horyzontu (pierwsze konto: latawiec,
    jak domyślny obraz w menu Start)."""
    if account.icon:
        pm = QPixmap(account.icon)
        if not pm.isNull():
            return pm.scaled(QSize(size, size), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    return icons.pixmap("avatar_" + icons.AVATARS[index % len(icons.AVATARS)], size)


# ====================================================================== przyciski
class GlossyButton(QWidget):
    """Mały kwadratowy przycisk z połyskiem: zielona strzałka logowania albo niebieski „?”."""
    clicked = Signal()

    def __init__(self, kind, parent=None):
        super().__init__(parent)
        self.kind = kind
        self._hover = self._down = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.TabFocus)
        self.setToolTip(T("Zaloguj", "Log on") if kind == "go" else T("Wskazówka do hasła", "Password hint"))

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._down = True
            self.update()

    def mouseReleaseEvent(self, e):
        was = self._down
        self._down = False
        self.update()
        if was and e.button() == Qt.LeftButton and self.rect().contains(e.position().toPoint()) and self.isEnabled():
            self.clicked.emit()

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter):
            self.clicked.emit()
            return
        super().keyPressEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        rad = r.width() * 0.2
        if self.kind == "go":
            cols = GREEN if self.isEnabled() else ("#d8e0da", "#b5c2b8", "#9aa89e", "#8a968d")
            style.paint_glossy_button(p, r, cols, "#0e5a1f" if self.isEnabled() else "#6a766d", rad,
                                      self._down, self._hover)
            style.paint_arrow(p, r)
        else:
            style.paint_glossy_button(p, r, ("#bfe3ff", "#5aa6e6", "#2f78c8", "#1f5aa6"), "#0b3a7a", rad,
                                      self._down, self._hover)
            p.setPen(QColor("#ffffff"))
            p.setFont(font(r.height() * 0.68, bold=True))
            p.drawText(r, Qt.AlignCenter, "?")
        if self.hasFocus():
            p.setPen(QPen(QColor(255, 255, 255, 200), 1, Qt.DotLine))
            p.drawRoundedRect(r.adjusted(2, 2, -2, -2), rad, rad)


class PasswordEdit(QLineEdit):
    """Pole hasła; zgłasza włączony Caps Lock (dioda z /sys/class/leds albo wielkość wpisanych liter)."""
    caps = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEchoMode(QLineEdit.Password)
        self._caps = None

    @staticmethod
    def caps_led():
        found = None
        for f in glob.glob("/sys/class/leds/*::capslock/brightness"):
            try:
                with open(f) as fh:
                    v = fh.read().strip()
                found = bool(found) or v not in ("", "0")
            except OSError:
                continue
        return found

    def _report(self, on):
        if on != self._caps:
            self._caps = on
            self.caps.emit(on)

    def check_caps(self):
        led = self.caps_led()
        if led is not None:
            self._report(led)

    def focusInEvent(self, e):
        super().focusInEvent(e)
        QTimer.singleShot(0, self.check_caps)

    def keyPressEvent(self, e):
        super().keyPressEvent(e)
        if e.key() == Qt.Key_CapsLock:
            QTimer.singleShot(60, self.check_caps)
            return
        led = self.caps_led()
        if led is not None:
            self._report(led)
            return
        t = e.text()
        if len(t) == 1 and t.isalpha() and t.lower() != t.upper():
            shift = bool(e.modifiers() & Qt.ShiftModifier)
            self._report(t.isupper() != shift)


class PowerButton(QWidget):
    """Czerwony przycisk zasilania z podpisem („Wyłącz komputer”)."""
    clicked = Signal()

    def __init__(self, text, k, parent=None):
        super().__init__(parent)
        self.text, self.k = text, k
        self._hover = self._down = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.TabFocus)
        fm = QFontMetrics(font(14 * k))
        self.setFixedSize(int(34 * k + 10 * k + fm.horizontalAdvance(text) + 8 * k), int(36 * k))

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def mousePressEvent(self, e):
        self._down = e.button() == Qt.LeftButton
        self.update()

    def mouseReleaseEvent(self, e):
        was, self._down = self._down, False
        self.update()
        if was and self.rect().contains(e.position().toPoint()):
            self.clicked.emit()

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter):
            self.clicked.emit()
            return
        super().keyPressEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        k = self.k
        s = int(30 * k)
        y = (self.height() - s) // 2
        off = 1 if self._down else 0
        p.drawPixmap(QRect(int(2 * k) + off, y + off, s, s), icons.pixmap("shutdown", s))
        if self._hover:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, 40))
            p.drawRoundedRect(QRectF(0, 0, s + 4 * k, self.height()), 5 * k, 5 * k)
        p.setFont(font(14 * k, bold=False))
        p.setPen(QColor("#ffffff"))
        tr = QRectF(s + 12 * k, 0, self.width() - s - 12 * k, self.height())
        f = p.font()
        f.setUnderline(self._hover or self.hasFocus())
        p.setFont(f)
        p.drawText(tr, Qt.AlignVCenter | Qt.AlignLeft, self.text)


class LinkButton(QWidget):
    """Biały tekst-odnośnik na ciemnym pasku (wybór sesji)."""
    clicked = Signal()

    def __init__(self, k, parent=None):
        super().__init__(parent)
        self.k = k
        self.text = ""
        self._hover = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.TabFocus)

    def set_text(self, text):
        self.text = text
        fm = QFontMetrics(font(12 * self.k))
        self.setFixedSize(fm.horizontalAdvance(text) + int(22 * self.k), int(26 * self.k))
        self.update()

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.rect().contains(e.position().toPoint()):
            self.clicked.emit()

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter, Qt.Key_Down):
            self.clicked.emit()
            return
        super().keyPressEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        f = font(12 * self.k)
        f.setUnderline(self._hover or self.hasFocus())
        p.setFont(f)
        p.setPen(QColor(255, 255, 255, 235))
        r = QRectF(self.rect()).adjusted(0, 0, -16 * self.k, 0)
        p.drawText(r, Qt.AlignVCenter | Qt.AlignLeft, self.text)
        # mały trójkąt
        x = self.width() - 11 * self.k
        cy = self.height() / 2
        path = QPainterPath()
        path.moveTo(x, cy - 2 * self.k)
        path.lineTo(x + 7 * self.k, cy - 2 * self.k)
        path.lineTo(x + 3.5 * self.k, cy + 2.5 * self.k)
        path.closeSubpath()
        p.fillPath(path, QColor(255, 255, 255, 220))


# ====================================================================== kafelek konta
class UserTile(QWidget):
    activated = Signal(object)        # kliknięcie / Enter — wybór konta
    submit = Signal(object)           # Enter w polu hasła albo strzałka
    hint_requested = Signal(object)

    def __init__(self, account, sc, k, parent=None, index=0):
        super().__init__(parent)
        self.account, self.sc, self.k = account, sc, k
        self.selected = False
        self.dimmed = False
        self.mode = "collapsed"       # collapsed / password / arrow / busy / welcome
        self.label = ""
        self._hover = False
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setCursor(Qt.PointingHandCursor)
        self.pic = account_pixmap(account, int(48 * k), index)
        self.edit = PasswordEdit(self)
        self.edit.hide()
        self.edit.returnPressed.connect(lambda: self.submit.emit(self))
        self.go = GlossyButton("go", self)
        self.go.hide()
        self.go.clicked.connect(lambda: self.submit.emit(self))
        self.hint = GlossyButton("hint", self)
        self.hint.hide()
        self.hint.clicked.connect(lambda: self.hint_requested.emit(self))
        self._layout()

    # -------------------------------------------------- geometria
    def name_x(self):
        return int(72 * self.k)

    def collapsed_h(self):
        return int(66 * self.k)

    def sizeHint(self):
        h = self.collapsed_h()
        if self.selected and self.mode in ("password", "arrow", "busy", "welcome"):
            h += int(40 * self.k) if self.mode != "welcome" else int(14 * self.k)
        return QSize(int(400 * self.k), h)

    def _layout(self):
        k = self.k
        x = self.name_x()
        y = int(64 * k)
        fh = int(24 * k)
        self.edit.setGeometry(x, y, int(176 * k), fh)
        self.go.setGeometry(x + int(182 * k) if self.mode != "arrow" else x, y, fh, fh)
        self.hint.setGeometry(self.go.geometry().right() + int(6 * k), y, fh, fh)

    def set_mode(self, mode, label=None, secret=True):
        self.mode = mode
        if label is not None:
            self.label = label
        show_fields = self.selected and mode in ("password", "busy")
        self.edit.setVisible(show_fields)
        self.edit.setEnabled(mode == "password")
        self.edit.setEchoMode(QLineEdit.Password if secret else QLineEdit.Normal)
        self.go.setVisible(self.selected and mode in ("password", "busy", "arrow"))
        self.go.setEnabled(mode != "busy")
        self.hint.setVisible(show_fields and bool(self.account.hint))
        self._layout()
        self.setFixedHeight(self.sizeHint().height())
        self.updateGeometry()
        self.update()

    def set_selected(self, sel):
        self.selected = sel
        self.setCursor(Qt.ArrowCursor if sel else Qt.PointingHandCursor)
        if not sel:
            self.edit.clear()
            self.set_mode("collapsed", "")
        else:
            self.set_mode(self.mode)

    def set_dimmed(self, d):
        self.dimmed = d
        self.update()

    # -------------------------------------------------- zdarzenia
    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and e.position().y() < self.collapsed_h():
            self.activated.emit(self)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            if self.selected and self.mode == "arrow":
                self.submit.emit(self)
            else:
                self.activated.emit(self)
            return
        super().keyPressEvent(e)

    def focusInEvent(self, e):
        super().focusInEvent(e)
        self.update()

    def focusOutEvent(self, e):
        super().focusOutEvent(e)
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        k = self.k
        if self.dimmed and not self.selected and not self._hover:
            p.setOpacity(0.5)
        w, h = self.width(), self.height()
        if self.selected:
            bg = QRectF(0, 0, w, h)
            path = QPainterPath()
            rad = 8 * k
            path.moveTo(rad, 0)
            path.lineTo(w, 0)
            path.lineTo(w, h)
            path.lineTo(rad, h)
            path.arcTo(QRectF(0, h - 2 * rad, 2 * rad, 2 * rad), 270, -90)
            path.lineTo(0, rad)
            path.arcTo(QRectF(0, 0, 2 * rad, 2 * rad), 180, -90)
            path.closeSubpath()
            p.fillPath(path, hgrad(bg, [(0, with_alpha(self.sc["tile"], 235)), (0.55, with_alpha(self.sc["tile"], 150)),
                                        (1, with_alpha(self.sc["tile"], 0))]))
            line = QRectF(0, 0, w, 1)
            p.fillRect(line, hgrad(line, [(0, with_alpha("#ffffff", 120)), (1, with_alpha("#ffffff", 0))]))
            line = QRectF(0, h - 1, w, 1)
            p.fillRect(line, hgrad(line, [(0, with_alpha("#ffffff", 80)), (1, with_alpha("#ffffff", 0))]))
        # obraz konta w ramce
        s = int(48 * k)
        pr = QRectF(9 * k, 9 * k, s, s)
        frame = pr.adjusted(-3 * k, -3 * k, 3 * k, 3 * k)
        hot = self.selected or self._hover or self.hasFocus()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(AMBER[1]) if hot else with_alpha("#ffffff", 210))
        p.drawRoundedRect(frame, 5 * k, 5 * k)
        clip = QPainterPath()
        clip.addRoundedRect(pr, 3 * k, 3 * k)
        p.save()
        p.setClipPath(clip)
        p.drawPixmap(pr.toRect(), self.pic)
        p.restore()
        # nazwa
        x = self.name_x()
        p.setPen(QColor("#ffffff"))
        p.setFont(font(19 * k))
        name_r = QRectF(x, 8 * k, w - x - 8 * k, 30 * k)
        fm = QFontMetrics(p.font())
        p.drawText(name_r, Qt.AlignLeft | Qt.AlignVCenter, fm.elidedText(self.account.real_name, Qt.ElideRight,
                                                                          int(name_r.width())))
        sub = ""
        if self.account.logged_in:
            sub = T("Zalogowany", "Logged on")
        if sub:
            p.setFont(font(11.5 * k))
            p.setPen(with_alpha("#ffffff", 210))
            p.drawText(QRectF(x, 36 * k, w - x, 18 * k), Qt.AlignLeft | Qt.AlignVCenter, sub)
        if self.selected and self.mode in ("password", "busy", "arrow", "welcome") and self.label:
            p.setFont(font(12 * k))
            p.setPen(with_alpha("#ffffff", 235))
            ly = 44 * k if not sub else 46 * k
            lx = x if self.mode != "arrow" else x + 32 * k
            ry = ly if self.mode != "arrow" else 64 * k
            p.drawText(QRectF(lx, ry, w - lx - 4 * k, 20 * k), Qt.AlignLeft | Qt.AlignVCenter, self.label)
        if self.hasFocus() and not self.selected:
            p.setPen(QPen(with_alpha("#ffffff", 160), 1, Qt.DotLine))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(QRectF(2, 2, w - 4, h - 4), 6 * k, 6 * k)


# ====================================================================== dymek
class Balloon(QWidget):
    """Żółty dymek z ogonkiem wskazującym pole (Caps Lock, złe hasło, wskazówka)."""

    def __init__(self, k, parent=None):
        super().__init__(parent)
        self.k = k
        self.title = self.text = ""
        self.icon = "info"
        self.tail_x = 30
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.hide()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_at(self, target_rect, title, text, icon="info", timeout=12000):
        """target_rect — prostokąt wskazywanego pola we współrzędnych rodzica."""
        k = self.k
        self.title, self.text, self.icon = title, text, icon
        width = int(300 * k)
        fm_b = QFontMetrics(font(12 * k, bold=True))
        fm = QFontMetrics(font(12 * k))
        tr = fm.boundingRect(QRect(0, 0, width - int(24 * k), 1000), Qt.TextWordWrap, text)
        height = int(14 * k + fm_b.height() + 6 * k + tr.height() + 14 * k + 12 * k)
        par = self.parentWidget().rect()
        x = target_rect.left() - int(14 * k)
        x = max(int(8 * k), min(x, par.width() - width - int(8 * k)))
        y = target_rect.bottom() + int(2 * k)
        self.tail_x = max(int(16 * k), min(target_rect.left() + int(14 * k) - x, width - int(24 * k)))
        self.setGeometry(x, y, width, height)
        self.raise_()
        self.show()
        self.update()
        if timeout:
            self._timer.start(timeout)

    def mousePressEvent(self, e):
        self.hide()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        k = self.k
        tail = 12 * k
        body = QRectF(0.5, tail + 0.5, self.width() - 1, self.height() - tail - 1)
        path = QPainterPath()
        path.addRoundedRect(body, 7 * k, 7 * k)
        t = QPainterPath()
        t.moveTo(self.tail_x, body.top() + 2)
        t.lineTo(self.tail_x + 2 * k, 0.5)
        t.lineTo(self.tail_x + 16 * k, body.top() + 2)
        t.closeSubpath()
        path = path.united(t)
        p.fillPath(path, QColor("#ffffe1"))
        p.setPen(QPen(QColor("#5a5a50"), 1))
        p.drawPath(path)
        ix, iy, isz = body.left() + 10 * k, body.top() + 9 * k, 16 * k
        if self.icon == "warning":
            tri = QPainterPath()
            tri.moveTo(ix + isz / 2, iy)
            tri.lineTo(ix + isz, iy + isz)
            tri.lineTo(ix, iy + isz)
            tri.closeSubpath()
            p.fillPath(tri, vgrad(QRectF(ix, iy, isz, isz), [(0, "#ffe27a"), (1, "#e0a010")]))
            p.setPen(QPen(QColor("#8a5a06"), 1))
            p.drawPath(tri)
            p.setPen(QColor("#000000"))
            p.setFont(font(11 * k, bold=True))
            p.drawText(QRectF(ix, iy + 3 * k, isz, isz - 3 * k), Qt.AlignCenter, "!")
        else:
            p.drawPixmap(QRect(int(ix), int(iy), int(isz), int(isz)), icons.pixmap("help", int(isz)))
        p.setPen(QColor("#000000"))
        p.setFont(font(12 * k, bold=True))
        fm_b = QFontMetrics(p.font())
        p.drawText(QRectF(ix + isz + 6 * k, iy - 1 * k, body.width() - isz - 40 * k, fm_b.height() + 2 * k),
                   Qt.AlignLeft | Qt.AlignVCenter, self.title)
        # zamknij
        cx = body.right() - 18 * k
        p.setPen(QPen(QColor("#6a6a60"), 1.4))
        p.drawLine(QPointF(cx, iy + 2 * k), QPointF(cx + 8 * k, iy + 10 * k))
        p.drawLine(QPointF(cx + 8 * k, iy + 2 * k), QPointF(cx, iy + 10 * k))
        p.setPen(QColor("#000000"))
        p.setFont(font(12 * k))
        tr = QRectF(body.left() + 12 * k, iy + fm_b.height() + 8 * k, body.width() - 24 * k,
                    body.bottom() - iy - fm_b.height() - 10 * k)
        p.drawText(tr, Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop, self.text)


# ====================================================================== nakładki
class Overlay(QWidget):
    """Przyciemnienie całego ekranu z oknem pośrodku. Podklasy rysują zawartość okna."""
    closed = Signal()

    def __init__(self, parent, sc, k, box_w, box_h, fade=True):
        super().__init__(parent)
        self.sc, self.k = sc, k
        self.box = QRect(0, 0, int(box_w * k), int(box_h * k))
        self._fade = 0 if fade else 110
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._step)
        self.setGeometry(parent.rect())
        self.box.moveCenter(self.rect().center())
        self.setFocusPolicy(Qt.StrongFocus)

    def open(self):
        self.setGeometry(self.parentWidget().rect())
        self.box.moveCenter(self.rect().center())
        self.relayout()
        self.show()
        self.raise_()
        self.setFocus()
        self._timer.start(30)

    def close_overlay(self):
        self.hide()
        self.closed.emit()
        self.deleteLater()

    def _step(self):
        self._fade = min(110, self._fade + 14)
        self.update()
        if self._fade >= 110:
            self._timer.stop()

    def relayout(self):
        pass

    def resizeEvent(self, e):
        self.box.moveCenter(self.rect().center())
        self.relayout()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.close_overlay()
            return
        super().keyPressEvent(e)

    def mousePressEvent(self, e):
        e.accept()

    def paint_dim(self, p):
        p.fillRect(self.rect(), QColor(10, 16, 20, self._fade))

    def paint_window(self, p, title):
        """Okno w stylu Horyzontu: pasek tytułu z gradientem i jasne wnętrze."""
        k, sc = self.k, self.sc
        b = QRectF(self.box)
        cap_h = 28 * k
        p.setRenderHint(QPainter.Antialiasing)
        outer = rounded(b.adjusted(-3 * k, -cap_h, 3 * k, 3 * k), 7 * k)
        cap = QRectF(b.left() - 3 * k, b.top() - cap_h, b.width() + 6 * k, cap_h + 6 * k)
        p.fillPath(outer, QColor(sc["accent_dark"]))
        p.save()
        p.setClipPath(outer)
        p.fillRect(cap, vgrad(cap, [(0, sc["accent_light"]), (0.15, sc["accent"]), (0.9, sc["accent_dark"]),
                                     (1, sc["accent_darker"])]))
        p.restore()
        p.setPen(QPen(QColor(sc["accent_darker"]), 1))
        p.setBrush(Qt.NoBrush)
        p.drawPath(outer)
        p.fillRect(b, QColor("#ebeee9"))
        p.setPen(QColor("#ffffff"))
        p.setFont(font(13 * k, bold=True))
        p.drawPixmap(QRect(int(b.left() + 3 * k), int(b.top() - cap_h + 6 * k), int(16 * k), int(16 * k)),
                     icons.pixmap("logo", int(16 * k)))
        p.drawText(QRectF(b.left() + 25 * k, b.top() - cap_h, b.width() - 30 * k, cap_h),
                   Qt.AlignVCenter | Qt.AlignLeft, title)


class BigRoundButton(QWidget):
    clicked = Signal()

    def __init__(self, icon, text, k, parent=None):
        super().__init__(parent)
        self.icon_name, self.text, self.k = icon, text, k
        self._hover = False
        self.setMouseTracking(True)
        self.setFixedSize(int(100 * k), int(86 * k))
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)

    def set(self, icon, text):
        self.icon_name, self.text = icon, text
        self.update()

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.rect().contains(e.position().toPoint()):
            self.clicked.emit()

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter):
            self.clicked.emit()
            return
        super().keyPressEvent(e)

    def focusInEvent(self, e):
        self.update()

    def focusOutEvent(self, e):
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        k = self.k
        hot = self._hover or self.hasFocus()
        sz = int((44 if hot else 40) * k)
        x = (self.width() - sz) // 2
        y = int(8 * k) - (int(2 * k) if hot else 0)
        if hot:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, 40))
            p.drawEllipse(QRect(x - int(6 * k), y - int(6 * k), sz + int(12 * k), sz + int(12 * k)))
        p.drawPixmap(QRect(x, y, sz, sz), icons.pixmap(self.icon_name, sz))
        f = font(12 * k)
        f.setUnderline(self.hasFocus())
        p.setFont(f)
        p.setPen(QColor("#ffffff"))
        p.drawText(QRect(0, int(56 * k), self.width(), int(28 * k)), Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap,
                   self.text)
