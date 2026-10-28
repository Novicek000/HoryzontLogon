"""Ekran powitalny: lista kont po prawej, logo po lewej, „Wyłącz komputer” na dolnym pasku."""
import os

from PySide6.QtCore import QEvent, QObject, QPoint, QRect, QRectF, Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QColor, QFontMetrics, QGuiApplication, QPainter
from PySide6.QtWidgets import QApplication, QMenu, QScrollArea, QVBoxLayout, QWidget

from .. import config, icons, sessions as sessmod
from ..i18n import T
from . import style
from .auth import Auth
from .dialogs import ClassicLogon, MessageDialog, PromptDialog, TurnOffDialog
from .style import font, with_alpha
from .widgets import Balloon, LinkButton, PowerButton, UserTile

WRAPPER_NAMES = ("session-wrapper",)


def scale_for(screen_size):
    h = screen_size.height()
    w = screen_size.width()
    return max(0.8, min(2.2, min(h / 768.0, w / 1024.0)))


class BlankScreen(QWidget):
    """Wygaszenie po bezczynności (czarny ekran); dowolny klawisz lub ruch myszy przywraca ekran."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setGeometry(parent.rect())
        self.setCursor(Qt.BlankCursor)
        self.hide()

    def paintEvent(self, e):
        QPainter(self).fillRect(self.rect(), QColor("#000000"))


class BackgroundWindow(QWidget):
    """Tło na dodatkowych monitorach."""

    def __init__(self, screen, sc):
        super().__init__(None, Qt.FramelessWindowHint)
        self.sc = sc
        self.setScreen(screen)
        self.setGeometry(screen.geometry())

    def paintEvent(self, e):
        p = QPainter(self)
        k = scale_for(self.size())
        style.paint_background(p, self.rect(), self.sc, int(self.height() * 0.125), int(self.height() * 0.125))


class GreeterWindow(QWidget):
    def __init__(self, client, accounts, session_list, demo=False, windowed=False, wrapper=None):
        super().__init__(None, Qt.FramelessWindowHint if not windowed else Qt.Window)
        self.setWindowTitle(T("Ekran powitalny", "Welcome"))
        self.demo = demo
        self.wrapper = wrapper
        self.accounts = accounts
        self.sessions = session_list or [sessmod.fallback_shell()]
        self.sc = style.scheme(config.get("color_scheme", "teal"))
        scr = QGuiApplication.primaryScreen()
        wsize = os.environ.get("HORYZONT_GREETER_WINDOW", "1024x768")
        try:
            ww, wh = (int(x) for x in wsize.lower().split("x"))
        except ValueError:
            ww, wh = 1024, 768
        self._wsize = (ww, wh)
        size = scr.geometry().size() if not windowed else QRect(0, 0, ww, wh).size()
        self.k = k = scale_for(size)
        self.setStyleSheet(style.stylesheet(self.sc, k))
        self.state = config.state()
        self.auth = Auth(client, self)
        self.auth.prompt.connect(self.on_prompt)
        self.auth.ready.connect(self.on_ready)
        self.auth.failed.connect(self.on_failed)
        self.auth.message.connect(self.on_message)
        self.auth.started.connect(self.on_started)
        self.auth.error.connect(self.on_error)

        self.sel = None              # wybrany kafelek
        self.prompt = None           # (rodzaj, tekst) — PAM czeka na odpowiedź
        self.prompts_answered = 0
        self.queued = None           # hasło wpisane, zanim greetd o nie zapytał
        self.login_requested = False
        self.welcome = False
        self.classic = None
        self.overlay = None
        self._cad = 0

        # --- lista kont
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setFrameShape(QScrollArea.NoFrame)
        self.scroll.viewport().setAutoFillBackground(False)
        self.list = QWidget()
        self.list.setAutoFillBackground(False)
        self.vl = QVBoxLayout(self.list)
        self.vl.setContentsMargins(0, 0, int(8 * k), 0)
        self.vl.setSpacing(int(6 * k))
        self.tiles = []
        for i, a in enumerate(accounts):
            t = UserTile(a, self.sc, k, self.list, i)
            t.activated.connect(self.activate)
            t.submit.connect(self.submit)
            t.hint_requested.connect(self.show_hint)
            t.edit.caps.connect(lambda on, t=t: self.caps_balloon(t, on))
            t.setFixedHeight(t.sizeHint().height())
            self.vl.addWidget(t)
            self.tiles.append(t)
        self.vl.addStretch(1)
        self.scroll.setWidget(self.list)

        # --- dolny pasek
        self.power = PowerButton(T("Wyłącz komputer", "Turn off computer"), k, self)
        self.power.clicked.connect(self.turn_off)
        self.power.setVisible(config.get("allow_power", True))
        self.sess_link = LinkButton(k, self)
        self.sess_link.clicked.connect(self.session_menu)
        self.sess_link.setVisible(config.get("show_sessions", True) and len(self.sessions) > 1)
        self.update_session_link()

        self.balloon = Balloon(k, self)
        self.blank = BlankScreen(self)
        self.idle = QTimer(self)
        self.idle.setSingleShot(True)
        self.idle.timeout.connect(self.blank_screen)
        self.reset_idle()
        QApplication.instance().installEventFilter(self)

        if windowed:
            self.resize(*self._wsize)
        self.secondary = []

    # ================================================================== start
    def start(self, windowed=False):
        if windowed:
            self.show()
        else:
            self.showFullScreen()
            primary = QGuiApplication.primaryScreen()
            for scr in QGuiApplication.screens():
                if scr is not primary:
                    w = BackgroundWindow(scr, self.sc)
                    w.showFullScreen()
                    self.secondary.append(w)
        if self.classic_only():
            self.power.hide()
            self.sess_link.hide()
            QTimer.singleShot(0, lambda: self.open_classic(can_cancel=False))
            return
        last = self.state.get("last_user") if config.get("remember_last_user", True) else None
        tile = next((t for t in self.tiles if t.account.name == last), None)
        if tile is None and len(self.tiles) == 1:
            tile = self.tiles[0]
        if tile:
            QTimer.singleShot(0, lambda: self.activate(tile, requested=False))
        elif self.tiles:
            self.tiles[0].setFocus()

    # ================================================================== układ
    def top_h(self):
        return max(int(56 * self.k), int(self.height() * 0.125))

    def bottom_h(self):
        return max(int(60 * self.k), int(self.height() * 0.125))

    def divider_x(self):
        return int(self.width() * 0.5)

    def resizeEvent(self, e):
        k = self.k
        w, h = self.width(), self.height()
        dx = self.divider_x()
        mid_top, mid_bot = self.top_h(), h - self.bottom_h()
        lw = min(int(430 * k), w - dx - int(40 * k))
        vis = [t for t in self.tiles if not t.isHidden()]
        content = sum(t.sizeHint().height() for t in vis) + self.vl.spacing() * max(0, len(vis) - 1) + int(70 * k)
        lh = min(content, int((mid_bot - mid_top) * 0.86))
        y = mid_top + ((mid_bot - mid_top) - lh) // 2
        self.scroll.setGeometry(dx + int(26 * k), y, lw, lh)
        by = h - self.bottom_h()
        self.power.move(int(28 * k), by + (self.bottom_h() - self.power.height()) // 2)
        self.sess_link.move(self.power.geometry().right() + int(36 * k),
                            by + (self.bottom_h() - self.sess_link.height()) // 2)
        self.blank.setGeometry(self.rect())
        for ch in self.findChildren(QWidget):
            if ch.parent() is self and hasattr(ch, "relayout") and ch.isVisible():
                ch.setGeometry(self.rect())

    def relayout_list(self):
        self.resizeEvent(None)

    # ================================================================== rysowanie
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        k = self.k
        w, h = self.width(), self.height()
        show_div = not self.classic_only()
        style.paint_background(p, self.rect(), self.sc, self.top_h(), self.bottom_h(),
                               self.divider_x() if show_div else None)
        if self.classic_only():
            return
        dx = self.divider_x()
        mid_top, mid_bot = self.top_h(), h - self.bottom_h()
        cy = (mid_top + mid_bot) // 2
        right = dx - int(32 * k)
        if self.welcome:
            p.setPen(QColor("#ffffff"))
            p.setFont(font(44 * k, italic=True, bold=True))
            p.drawText(QRectF(0, cy - 40 * k, right, 70 * k), Qt.AlignRight | Qt.AlignVCenter,
                       T("Zapraszamy", "Welcome"))
        else:
            # logo: słońce + nazwa + podpis
            s = int(78 * k)
            name = config.get("logo_text") or "Horyzont"
            sub = config.get("subtitle") or config.os_name()
            fn = font(40 * k, bold=True, italic=True)
            fm = QFontMetrics(fn)
            tw = fm.horizontalAdvance(name)
            block_w = s + int(10 * k) + tw
            x0 = right - block_w
            ly = cy - int(64 * k)
            p.drawPixmap(QRect(x0, ly, s, s), icons.pixmap("logo", s))
            p.setFont(fn)
            p.setPen(QColor(0, 0, 0, 60))
            p.drawText(QRectF(x0 + s + 10 * k + 2, ly + 2, tw + 4, s), Qt.AlignLeft | Qt.AlignVCenter, name)
            p.setPen(QColor("#ffffff"))
            p.drawText(QRectF(x0 + s + 10 * k, ly, tw + 4, s), Qt.AlignLeft | Qt.AlignVCenter, name)
            p.setFont(font(13 * k))
            p.setPen(with_alpha("#ffffff", 220))
            p.drawText(QRectF(0, ly + s - 6 * k, right, 22 * k), Qt.AlignRight | Qt.AlignVCenter, sub)
            p.setFont(font(16 * k))
            p.setPen(QColor("#ffffff"))
            p.drawText(QRectF(0, cy + 34 * k, right, 28 * k), Qt.AlignRight | Qt.AlignVCenter,
                       T("Aby rozpocząć, kliknij swoją nazwę użytkownika", "To begin, click your user name"))
        # podpowiedź w prawym dolnym rogu
        if config.get("footer_hint", True) and config.horyzont_installed() and not self.welcome:
            txt = T("Po zalogowaniu możesz dodawać i zmieniać konta.\nOtwórz Panel sterowania i kliknij Konta użytkowników.",
                    "After you log on, you can add or change accounts.\nJust go to Control Panel and click User Accounts.")
            p.setFont(font(11.5 * k))
            p.setPen(with_alpha("#ffffff", 225))
            r = QRectF(w * 0.55, h - self.bottom_h(), w * 0.45 - 28 * k, self.bottom_h())
            p.drawText(r, Qt.AlignRight | Qt.AlignVCenter, txt)

    def classic_only(self):
        return config.get("style") == "classic" or not self.tiles

    # ================================================================== bezczynność
    def eventFilter(self, obj, ev):
        t = ev.type()
        if t in (QEvent.KeyPress, QEvent.MouseMove, QEvent.MouseButtonPress, QEvent.Wheel):
            if self.blank.isVisible():
                self.blank.hide()
                self.reset_idle()
                return True
            self.reset_idle()
        if t == QEvent.KeyPress:
            if self._handle_global_key(ev):
                return True
        return False

    def _handle_global_key(self, e):
        mods = e.modifiers()
        if e.key() == Qt.Key_Delete and mods & Qt.ControlModifier and mods & Qt.AltModifier:
            self._cad += 1
            QTimer.singleShot(4000, self._reset_cad)
            if self._cad >= 2 and self.classic is None and not self.welcome:
                self._cad = 0
                self.open_classic(can_cancel=True)
            return True
        if self.overlay is not None or self.classic is not None or self.welcome:
            return False
        fw = QApplication.focusWidget()
        if e.key() in (Qt.Key_Up, Qt.Key_Down) and isinstance(fw, UserTile):
            i = self.tiles.index(fw)
            i = max(0, min(len(self.tiles) - 1, i + (1 if e.key() == Qt.Key_Down else -1)))
            self.tiles[i].setFocus()
            self.scroll.ensureWidgetVisible(self.tiles[i])
            return True
        if e.key() in (Qt.Key_Up, Qt.Key_Down) and self.sel and fw is self.sel.edit:
            i = self.tiles.index(self.sel)
            i = max(0, min(len(self.tiles) - 1, i + (1 if e.key() == Qt.Key_Down else -1)))
            self.tiles[i].setFocus()
            return True
        if e.key() == Qt.Key_Escape and self.sel is not None:
            self.deselect()
            return True
        if isinstance(fw, UserTile) and fw is not self.sel and e.text() and e.text().isprintable() \
                and not (mods & (Qt.ControlModifier | Qt.AltModifier)):
            self.activate(fw)
            fw.edit.insert(e.text())
            return True
        return False

    def _reset_cad(self):
        self._cad = 0

    def reset_idle(self):
        mins = config.get("screen_blank_minutes", 10) or 0
        if mins > 0:
            self.idle.start(int(mins * 60000))

    def blank_screen(self):
        if self.welcome:
            return
        self.balloon.hide()
        self.blank.setGeometry(self.rect())
        self.blank.raise_()
        self.blank.show()

    # ================================================================== wybór konta
    def activate(self, tile, requested=True):
        if self.welcome:
            return
        if tile is self.sel:
            if tile.mode == "arrow":
                self.submit(tile)
            elif tile.mode == "password":
                tile.edit.setFocus()
            return
        self.balloon.hide()
        if self.sel is not None:
            self.sel.set_selected(False)
        self.sel = tile
        self.prompt = None
        self.prompts_answered = 0
        self.queued = None
        self.login_requested = requested
        for t in self.tiles:
            t.set_dimmed(t is not tile)
        tile.set_selected(True)
        tile.set_mode("password", T("Wpisz hasło", "Type your password"))
        tile.edit.setFocus()
        self.relayout_list()
        QTimer.singleShot(0, lambda: self.scroll.ensureWidgetVisible(tile))
        self.update_session_link()
        self.auth.select(tile.account.name)

    def deselect(self):
        if self.sel is None:
            return
        self.auth.cancel()
        self.balloon.hide()
        t = self.sel
        self.sel = None
        self.prompt = None
        t.set_selected(False)
        for x in self.tiles:
            x.set_dimmed(False)
        t.setFocus()
        self.relayout_list()
        self.update_session_link()

    def submit(self, tile):
        if tile is not self.sel or self.welcome:
            return
        self.balloon.hide()
        self.login_requested = True
        if tile.mode == "arrow":
            self.start_session()
            return
        pw = tile.edit.text()
        tile.set_mode("busy", T("Sprawdzanie hasła...", "Checking password..."))
        if self.prompt is not None:
            self.prompt = None
            self.prompts_answered += 1
            self.auth.answer(pw)
        else:
            self.queued = pw

    # ================================================================== odpowiedzi greetd
    def _stale(self, token):
        return token != self.auth.token

    def on_prompt(self, kind, text, token):
        if self._stale(token):
            return
        secret = kind == "secret"
        if self.classic is not None:
            if self.prompts_answered == 0 and self.queued is not None:
                pw, self.queued = self.queued, None
                self.prompts_answered += 1
                self.auth.answer(pw)
                return
            self._ask_extra(kind, text)
            return
        t = self.sel
        if t is None:
            return
        if self.prompts_answered == 0:
            if self.queued is not None:
                pw, self.queued = self.queued, None
                self.prompts_answered += 1
                self.auth.answer(pw)
                return
            self.prompt = (kind, text)
            label = T("Wpisz hasło", "Type your password")
            low = text.lower().strip()
            if low and not low.startswith(("password", "hasło", "haslo")):
                label = text.strip().rstrip(":")
            if t.mode != "busy":
                t.set_mode("password", label, secret)
        else:
            self._ask_extra(kind, text)

    def _ask_extra(self, kind, text):
        d = PromptDialog(self, self.sc, self.k, T("Logowanie", "Log On"), text.strip(), kind == "secret")

        def ans(v):
            self.prompts_answered += 1
            self.overlay = None
            self.auth.answer(v)

        def cancel():
            self.overlay = None
            self.reset_after_failure(silent=True)
        d.answered.connect(ans)
        d.cancelled.connect(cancel)
        self.overlay = d
        d.open()

    def on_ready(self, token):
        if self._stale(token):
            return
        if self.classic is not None or self.login_requested:
            self.start_session()
            return
        if self.sel:
            # konto bez hasła wybrane przy starcie — czekamy na kliknięcie strzałki
            self.sel.set_mode("arrow", T("Kliknij strzałkę, aby się zalogować", "Click the arrow to log on"))
            self.sel.go.setFocus()
            self.relayout_list()

    def on_failed(self, desc, token):
        if self._stale(token):
            return
        if self.classic is not None:
            self.classic.set_busy(False)
            self.classic.password.clear()
            self.classic.password.setFocus()
            self.message(T("Logowanie do systemu", "Log On to System"),
                         T("System nie może Cię zalogować. Upewnij się, że nazwa użytkownika i hasło są poprawne, "
                           "a następnie wpisz hasło ponownie. W hasłach rozróżniane są wielkie i małe litery.",
                           "The system could not log you on. Make sure your User name and password are correct, "
                           "then type your password again. Letters in passwords must be typed using the correct case."))
            self.queued = None
            self.prompts_answered = 0
            return
        self.reset_after_failure()

    def reset_after_failure(self, silent=False):
        t = self.sel
        self.prompt = None
        self.prompts_answered = 0
        self.queued = None
        if self.classic is not None:
            self.classic.set_busy(False)
            return
        if t is None:
            return
        t.edit.clear()
        t.set_mode("password", T("Wpisz hasło", "Type your password"))
        t.edit.setFocus()
        self.relayout_list()
        if not silent:
            text = T("Wpisz hasło ponownie. Pamiętaj, że w hasłach rozróżniane są wielkie i małe litery.",
                     "Please type your password again. Be sure to use the correct uppercase and lowercase letters.")
            if t.account.hint:
                text += "\n\n" + T("Wskazówka do hasła: ", "Password hint: ") + t.account.hint
            QTimer.singleShot(50, lambda: self.balloon.show_at(self.field_rect(t), T("Nie pamiętasz hasła?",
                                                                                       "Did you forget your password?"),
                                                                text, "info"))
        self.login_requested = True
        self.auth.select(t.account.name)

    def on_message(self, kind, text, token):
        if self._stale(token) or not text.strip():
            return
        if self.classic is not None and kind == "info":
            self.classic.set_busy(True, text.strip())
            return
        if self.sel is not None and self.classic is None:
            self.balloon.show_at(self.field_rect(self.sel), T("Informacja", "Information") if kind == "info"
                                 else T("Uwaga", "Warning"), text.strip(), "info" if kind == "info" else "warning")
        else:
            self.message(T("Logowanie do systemu", "Log On to System"), text.strip())

    def on_error(self, desc, token):
        if self._stale(token):
            return
        if self.welcome:
            self.welcome = False
            for t in self.tiles:
                t.show()
            self.power.setVisible(config.get("allow_power", True))
            self.update_session_link()
            self.update()
        self.message(T("Logowanie do systemu", "Log On to System"),
                     T("Nie udało się zalogować:", "Could not log on:") + "\n" + (desc or "?"), "shutdown")
        if self.classic is not None:
            self.classic.set_busy(False)
            self.prompts_answered = 0
            self.queued = None
        elif self.sel is not None:
            self.sel.set_mode("password", T("Wpisz hasło", "Type your password"))
            self.prompt = None
            self.prompts_answered = 0
            self.login_requested = True
            QTimer.singleShot(1500, lambda: self.sel and self.auth.select(self.sel.account.name))

    # ================================================================== uruchamianie sesji
    def current_session(self, user=None):
        user = user or (self.sel.account.name if self.sel else None)
        per_user = self.state.get("sessions", {}) or {}
        sid = per_user.get(user) if user else None
        sid = sid or self.state.get("last_session") or config.get("default_session", "horyzont")
        return sessmod.find(self.sessions, sid) or sessmod.default(self.sessions, config.get("default_session"))

    def start_session(self):
        if self.classic is not None:
            user = self.classic.user.text().strip()
            sess = sessmod.find(self.sessions, self.classic.session_id()) or self.current_session(user)
        else:
            if self.sel is None:
                return
            user = self.sel.account.name
            sess = self.current_session(user)
        cmd, env = sessmod.command(sess, self.wrapper)
        self.pending = (user, sess)
        if self.classic is None:
            self.welcome = True
            self.balloon.hide()
            for t in self.tiles:
                if t is not self.sel:
                    t.hide()
            self.sel.set_mode("welcome", T("Wczytywanie ustawień osobistych...", "Loading your personal settings..."))
            self.power.hide()
            self.sess_link.hide()
            self.relayout_list()
            self.update()
        else:
            self.classic.set_busy(True, T("Wczytywanie ustawień osobistych...", "Loading your personal settings..."))
        self.auth.start(cmd, env)

    def on_started(self):
        user, sess = self.pending
        st = config.state()
        sessions = st.get("sessions", {}) or {}
        sessions[user] = sess.id
        config.save_state(last_user=user, last_session=sess.id, sessions=sessions)
        if self.demo:
            print(f"horyzont-greeter (demo): start_session {user} → {sess.id}")
        QTimer.singleShot(1100 if not self.demo else 1800, self.finish)

    def finish(self):
        self.auth.shutdown()
        QApplication.instance().exit(0)

    # ================================================================== sesje
    def update_session_link(self):
        sess = self.current_session()
        if sess:
            self.sess_link.set_text(T("Sesja: ", "Session: ") + sess.label())
        self.resizeEvent(None) if self.isVisible() else None

    def session_menu(self):
        m = QMenu(self)
        grp = QActionGroup(m)
        cur = self.current_session()
        for s in self.sessions:
            a = QAction(s.label(), m)
            a.setCheckable(True)
            a.setChecked(cur is not None and s.id == cur.id)
            a.setData(s.id)
            grp.addAction(a)
            m.addAction(a)
        chosen = m.exec(self.sess_link.mapToGlobal(QPoint(0, 0)) - QPoint(0, m.sizeHint().height()))
        if chosen:
            sid = chosen.data()
            per_user = self.state.get("sessions", {}) or {}
            if self.sel:
                per_user[self.sel.account.name] = sid
                self.state["sessions"] = per_user
            else:
                self.state["last_session"] = sid
            self.update_session_link()
            if self.sel and self.sel.mode == "password":
                self.sel.edit.setFocus()

    # ================================================================== dymki i okna
    def field_rect(self, tile):
        w = tile.edit if tile.edit.isVisible() else tile
        tl = w.mapTo(self, QPoint(0, 0))
        return QRect(tl, w.size())

    def caps_balloon(self, tile, on):
        if tile is not self.sel:
            return
        if on:
            self.balloon.show_at(self.field_rect(tile), T("Klawisz Caps Lock jest włączony", "Caps Lock is On"),
                                 T("Gdy Caps Lock jest włączony, hasło może zostać wpisane nieprawidłowo.\n\n"
                                   "Naciśnij klawisz Caps Lock, aby go wyłączyć, zanim wpiszesz hasło.",
                                   "Having Caps Lock on may cause you to enter your password incorrectly.\n\n"
                                   "You should press Caps Lock to turn it off before entering your password."),
                                 "warning")
        elif self.balloon.isVisible() and self.balloon.icon == "warning":
            self.balloon.hide()

    def show_hint(self, tile):
        if tile.account.hint:
            self.balloon.show_at(self.field_rect(tile), T("Wskazówka do hasła", "Password hint"), tile.account.hint)

    def message(self, title, text, icon="help"):
        d = MessageDialog(self, self.sc, self.k, title, text, icon)

        def done():
            self.overlay = None
            if self.classic is not None:
                self.classic.setFocus()
                self.classic.password.setFocus()
            elif self.sel is not None and self.sel.edit.isVisible():
                self.sel.edit.setFocus()
        d.closed.connect(done)
        self.overlay = d
        d.open()

    def turn_off(self):
        self.balloon.hide()
        d = TurnOffDialog(self, self.sc, self.k, self.demo)

        def done():
            self.overlay = None
            if self.classic is not None:
                self.classic.setFocus()
        d.closed.connect(done)
        self.overlay = d
        d.open()

    def open_classic(self, can_cancel=False):
        if self.sel is not None:
            self.deselect()
        self.balloon.hide()
        last = self.state.get("last_user", "") if config.get("remember_last_user", True) else ""
        cur = self.current_session(last or None)
        c = ClassicLogon(self, self.sc, self.k, self.sessions, cur.id if cur else "", last, can_cancel)
        c.submitted.connect(self.classic_submit)
        c.power_requested.connect(self.turn_off)

        def closed():
            self.classic = None
            self.auth.cancel()
            self.update()
        c.closed.connect(closed)
        self.classic = c
        c.open()
        self.update()

    def classic_submit(self, user, password):
        self.prompts_answered = 0
        self.queued = password
        self.login_requested = True
        self.classic.set_busy(True, T("Logowanie...", "Logging on..."))
        self.auth.select(user)
