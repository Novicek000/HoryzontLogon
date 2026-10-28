"""Okna na ekranie powitalnym: Wyłącz komputer, dodatkowe pytania PAM, komunikaty, klasyczne logowanie."""
from PySide6.QtCore import QRect, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QComboBox, QLabel, QLineEdit, QPushButton

from .. import config, icons, power
from ..i18n import T
from .style import font, hgrad, vgrad
from .widgets import BigRoundButton, Overlay, PasswordEdit


class TurnOffDialog(Overlay):
    """Wyłącz komputer: Stan wstrzymania (z Shift — Hibernacja), Wyłącz, Uruchom ponownie."""

    def __init__(self, parent, sc, k, demo=False):
        super().__init__(parent, sc, k, 330, 196)
        self.demo = demo
        self.can_hibernate = power.can("hibernate")
        self.buttons = []
        for key, icon, text in (("standby", "standby", T("Stan wstrzymania", "Stand By")),
                                ("turnoff", "shutdown", T("Wyłącz", "Turn Off")),
                                ("restart", "restart", T("Uruchom ponownie", "Restart"))):
            b = BigRoundButton(icon, text, k, self)
            b.action = key
            b.clicked.connect(lambda b=b: self.do(b.action))
            self.buttons.append(b)
        self.cancel = QPushButton(T("Anuluj", "Cancel"), self)
        self.cancel.clicked.connect(self.close_overlay)
        self.cancel.adjustSize()

    def relayout(self):
        k = self.k
        x0 = self.box.left() + (self.box.width() - len(self.buttons) * int(100 * k)) // 2
        for i, b in enumerate(self.buttons):
            b.move(x0 + i * int(100 * k), self.box.top() + int(62 * k))
        self.cancel.move(self.box.right() - self.cancel.width() - int(12 * k),
                         self.box.bottom() - self.cancel.height() - int(9 * k))

    def open(self):
        super().open()
        self.buttons[1].setFocus()

    def _shift(self, on):
        b = self.buttons[0]
        if on and self.can_hibernate:
            b.action = "hibernate"
            b.set("hibernate", T("Hibernacja", "Hibernate"))
        else:
            b.action = "standby"
            b.set("standby", T("Stan wstrzymania", "Stand By"))

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Shift:
            self._shift(True)
            return
        if e.key() in (Qt.Key_Left, Qt.Key_Right):
            i = next((n for n, b in enumerate(self.buttons) if b.hasFocus()), 1)
            i = (i + (1 if e.key() == Qt.Key_Right else -1)) % len(self.buttons)
            self.buttons[i].setFocus()
            return
        super().keyPressEvent(e)

    def keyReleaseEvent(self, e):
        if e.key() == Qt.Key_Shift:
            self._shift(False)
            return
        super().keyReleaseEvent(e)

    def do(self, action):
        self.close_overlay()
        QTimer.singleShot(150, lambda: power.run(action, self.demo))

    def paintEvent(self, e):
        p = QPainter(self)
        self.paint_dim(p)
        k, sc = self.k, self.sc
        b = self.box
        p.setRenderHint(QPainter.Antialiasing)
        hh = int(44 * k)
        head = QRect(b.left(), b.top(), b.width(), hh)
        foot = QRect(b.left(), b.bottom() - hh, b.width(), hh + 1)
        middle = QRect(b.left(), head.bottom() + 1, b.width(), foot.top() - head.bottom() - 1)
        p.fillRect(head, vgrad(QRectF(head), [(0, sc["accent_darker"]), (1, sc["accent"])]))
        p.fillRect(middle, vgrad(QRectF(middle), [(0, sc["accent_light"]), (0.5, sc["accent"]), (1, sc["accent_light"])]))
        p.fillRect(foot, vgrad(QRectF(foot), [(0, sc["accent"]), (1, sc["accent_darker"])]))
        line = QRectF(b.left(), head.bottom() - 1, b.width(), 2)
        p.fillRect(line, hgrad(line, [(0, "#00ffffff"), (0.5, "#ffffffff"), (1, "#00ffffff")]))
        p.setPen(QPen(QColor(sc["accent_darker"]).darker(130), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRect(b.adjusted(0, 0, -1, -1))
        p.setFont(font(18 * k))
        p.setPen(QColor("#ffffff"))
        title = T("Wyłącz komputer", "Turn off computer")
        p.drawText(head.adjusted(int(14 * k), 0, int(-60 * k), 0), Qt.AlignVCenter | Qt.AlignLeft, title)
        s = int(32 * k)
        p.drawPixmap(QRect(head.right() - int(40 * k), head.top() + int(6 * k), s, s), icons.pixmap("logo", s))


class PromptDialog(Overlay):
    """Dodatkowe pytanie modułu PAM (np. „Nowe hasło”, kod weryfikacyjny)."""
    answered = Signal(str)
    cancelled = Signal()

    def __init__(self, parent, sc, k, title, text, secret=True):
        super().__init__(parent, sc, k, 360, 150)
        self.title = title
        self.label = QLabel(text, self)
        self.label.setWordWrap(True)
        self.edit = PasswordEdit(self) if secret else QLineEdit(self)
        self.ok = QPushButton("OK", self)
        self.ok.setDefault(True)
        self.no = QPushButton(T("Anuluj", "Cancel"), self)
        self.ok.clicked.connect(self._ok)
        self.no.clicked.connect(self._cancel)
        self.edit.returnPressed.connect(self._ok)

    def relayout(self):
        k, b = self.k, self.box
        m = int(14 * k)
        self.label.setGeometry(b.left() + int(56 * k), b.top() + m, b.width() - int(70 * k), int(44 * k))
        self.edit.setGeometry(b.left() + int(56 * k), b.top() + int(62 * k), b.width() - int(70 * k), int(24 * k))
        self.ok.adjustSize()
        self.no.adjustSize()
        y = b.bottom() - self.ok.height() - m
        self.no.move(b.right() - m - self.no.width(), y)
        self.ok.move(self.no.x() - int(8 * k) - self.ok.width(), y)

    def open(self):
        super().open()
        self.edit.setFocus()

    def _ok(self):
        t = self.edit.text()
        self.edit.clear()
        self.answered.emit(t)
        self.close_overlay()

    def _cancel(self):
        self.cancelled.emit()
        self.close_overlay()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self._cancel()
            return
        super().keyPressEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        self.paint_dim(p)
        self.paint_window(p, self.title)
        s = int(32 * self.k)
        p.drawPixmap(QRect(self.box.left() + int(14 * self.k), self.box.top() + int(14 * self.k), s, s),
                     icons.pixmap("key", s))


class MessageDialog(Overlay):
    def __init__(self, parent, sc, k, title, text, icon="help"):
        super().__init__(parent, sc, k, 380, 130)
        self.title, self.icon = title, icon
        self.label = QLabel(text, self)
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.ok = QPushButton("OK", self)
        self.ok.setDefault(True)
        self.ok.clicked.connect(self.close_overlay)
        fm = self.label.fontMetrics()
        need = fm.boundingRect(QRect(0, 0, int(300 * k), 2000), Qt.TextWordWrap, text).height()
        self.box.setHeight(max(self.box.height(), need + int(80 * k)))

    def relayout(self):
        k, b = self.k, self.box
        m = int(14 * k)
        self.label.setGeometry(b.left() + int(60 * k), b.top() + m, b.width() - int(74 * k), b.height() - int(60 * k))
        self.ok.adjustSize()
        self.ok.move(b.center().x() - self.ok.width() // 2, b.bottom() - self.ok.height() - m)

    def open(self):
        super().open()
        self.ok.setFocus()

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.close_overlay()
            return
        super().keyPressEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        self.paint_dim(p)
        self.paint_window(p, self.title)
        s = int(32 * self.k)
        p.drawPixmap(QRect(self.box.left() + int(16 * self.k), self.box.top() + int(14 * self.k), s, s),
                     icons.pixmap(self.icon, s))


class ClassicLogon(Overlay):
    """Klasyczne okno „Logowanie do systemu” z polami nazwy i hasła (styl „classic”
    albo dwukrotne Ctrl+Alt+Del na ekranie powitalnym)."""
    submitted = Signal(str, str)
    power_requested = Signal()
    cancelled = Signal()

    def __init__(self, parent, sc, k, sessions, session_id, last_user="", can_cancel=False):
        super().__init__(parent, sc, k, 430, 236, fade=can_cancel)
        self.can_cancel = can_cancel
        self.sessions = sessions
        self.options = False
        self.user_l = QLabel(T("&Nazwa użytkownika:", "&User name:"), self)
        self.user = QLineEdit(last_user, self)
        self.user_l.setBuddy(self.user)
        self.pass_l = QLabel(T("&Hasło:", "&Password:"), self)
        self.password = PasswordEdit(self)
        self.pass_l.setBuddy(self.password)
        self.sess_l = QLabel(T("&Sesja:", "&Session:"), self)
        self.sess = QComboBox(self)
        self.sess_l.setBuddy(self.sess)
        for s in sessions:
            self.sess.addItem(s.label(), s.id)
        i = self.sess.findData(session_id)
        self.sess.setCurrentIndex(max(0, i))
        self.ok = QPushButton("OK", self)
        self.ok.setDefault(True)
        self.cancel = QPushButton(T("Anuluj", "Cancel"), self)
        self.shut = QPushButton(T("&Wyłącz...", "Sh&ut Down..."), self)
        self.opt = QPushButton(T("&Opcje >>", "&Options >>"), self)
        self.ok.clicked.connect(self._submit)
        self.password.returnPressed.connect(self._submit)
        self.user.returnPressed.connect(lambda: self.password.setFocus() if not self.password.text() else self._submit())
        self.cancel.clicked.connect(self._cancel)
        self.shut.clicked.connect(self.power_requested.emit)
        self.opt.clicked.connect(self.toggle_options)
        self.shut.setVisible(config.get("allow_power", True))
        self.status = ""
        self._apply_options()

    def toggle_options(self):
        self.options = not self.options
        self._apply_options()
        self.relayout()
        self.update()

    def _apply_options(self):
        show = self.options and len(self.sessions) > 1
        self.sess_l.setVisible(show)
        self.sess.setVisible(show)
        self.opt.setText(T("&Opcje <<", "&Options <<") if self.options else T("&Opcje >>", "&Options >>"))
        self.opt.setVisible(len(self.sessions) > 1)
        self.box.setHeight(int((236 + (34 if show else 0)) * self.k))

    def session_id(self):
        return self.sess.currentData()

    def set_busy(self, busy, status=""):
        for w in (self.user, self.password, self.ok, self.cancel, self.shut, self.opt, self.sess):
            w.setEnabled(not busy)
        self.status = status
        self.update()

    def relayout(self):
        k, b = self.k, self.box
        banner = int(78 * k)
        lx = b.left() + int(22 * k)
        fx = b.left() + int(158 * k)
        fw = b.width() - int(158 * k) - int(22 * k)
        y = b.top() + banner + int(18 * k)
        rh = int(24 * k)
        for lab, field in ((self.user_l, self.user), (self.pass_l, self.password), (self.sess_l, self.sess)):
            if not field.isVisibleTo(self) and field is self.sess:
                continue
            lab.setGeometry(lx, y, fx - lx - int(6 * k), rh)
            field.setGeometry(fx, y, fw, rh)
            y += rh + int(10 * k)
        btns = [self.ok, self.cancel] + ([self.shut] if self.shut.isVisibleTo(self) else []) + \
               ([self.opt] if self.opt.isVisibleTo(self) else [])
        for bt in btns:
            bt.adjustSize()
        x = b.right() - int(14 * k)
        by = b.bottom() - int(14 * k) - self.ok.height()
        for bt in reversed(btns):
            x -= bt.width()
            bt.move(x, by)
            x -= int(6 * k)

    def open(self):
        super().open()
        (self.password if self.user.text() else self.user).setFocus()

    def _submit(self):
        u = self.user.text().strip()
        if not u:
            self.user.setFocus()
            return
        self.submitted.emit(u, self.password.text())

    def _cancel(self):
        self.password.clear()
        if self.can_cancel:
            self.cancelled.emit()
            self.close_overlay()
        else:
            self.user.selectAll()
            self.user.setFocus()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self._cancel()
            return
        super().keyPressEvent(e)

    def paintEvent(self, e):
        p = QPainter(self)
        if self.can_cancel:
            self.paint_dim(p)
        self.paint_window(p, T("Logowanie do systemu", "Log On to System"))
        k, sc, b = self.k, self.sc, self.box
        banner = QRectF(b.left(), b.top(), b.width(), 78 * k)
        p.fillRect(banner, hgrad(banner, [(0, sc["accent_darker"]), (0.55, sc["accent"]), (1, sc["accent_light"])]))
        s = int(52 * k)
        p.drawPixmap(QRect(int(b.left() + 16 * k), int(banner.top() + 13 * k), s, s), icons.pixmap("logo", s))
        p.setPen(QColor("#ffffff"))
        p.setFont(font(26 * k, bold=True, italic=True))
        p.drawText(QRectF(b.left() + 80 * k, banner.top() + 8 * k, b.width() - 90 * k, 38 * k),
                   Qt.AlignLeft | Qt.AlignVCenter, config.get("logo_text") or "Horyzont")
        p.setFont(font(12 * k))
        p.drawText(QRectF(b.left() + 82 * k, banner.top() + 44 * k, b.width() - 90 * k, 22 * k),
                   Qt.AlignLeft | Qt.AlignVCenter, config.get("subtitle") or config.os_name())
        line = QRectF(b.left(), banner.bottom(), b.width(), 3 * k)
        p.fillRect(line, hgrad(line, [(0, "#e8901f"), (0.6, "#ffd38a"), (1, "#f6ad3e")]))
        if self.status:
            p.setPen(QColor("#333333"))
            p.setFont(font(12 * k))
            p.drawText(QRectF(b.left() + 22 * k, b.bottom() - 70 * k, b.width() - 44 * k, 24 * k),
                       Qt.AlignLeft | Qt.AlignVCenter, self.status)
