"""Rozmowa z greetd w osobnym wątku (sprawdzanie hasła przez PAM potrafi trwać kilka sekund).

Polecenia (z wątku okna): select(użytkownik), answer(tekst), start(cmd, env), cancel().
Sygnały do okna: prompt(rodzaj, tekst) — PAM pyta o hasło lub inną odpowiedź; ready() — uwierzytelniono,
można uruchomić sesję; failed(opis) — złe hasło; message(rodzaj, tekst) — informacja z PAM;
started() — greetd uruchomi sesję po zamknięciu ekranu powitalnego; error(opis) — inny błąd.
"""
from PySide6.QtCore import QObject, QThread, Signal, Slot

from ..greetd import GreetdError


class _Worker(QObject):
    prompt = Signal(str, str, int)
    ready = Signal(int)
    failed = Signal(str, int)
    message = Signal(str, str, int)
    started = Signal()
    error = Signal(str, int)
    busy = Signal(bool)

    def __init__(self, client):
        super().__init__()
        self.client = client
        self.active = False      # czy greetd ma rozpoczętą sesję logowania

    def _handle(self, resp, token):
        """Obsługa odpowiedzi; komunikaty informacyjne potwierdzamy od razu i czekamy na następną."""
        while True:
            t = resp.get("type")
            if t == "success":
                self.ready.emit(token)
                return
            if t == "error":
                self.active = False
                desc = resp.get("description", "")
                try:
                    self.client.cancel()
                except GreetdError:
                    pass
                if resp.get("error_type") == "auth_error":
                    self.failed.emit(desc, token)
                else:
                    self.error.emit(desc, token)
                return
            if t == "auth_message":
                kind = resp.get("auth_message_type", "secret")
                text = resp.get("auth_message", "")
                if kind in ("info", "error"):
                    self.message.emit(kind, text, token)
                    resp = self.client.answer(None)
                    continue
                self.prompt.emit(kind, text, token)
                return
            self.error.emit(f"nieznana odpowiedź greetd: {resp}", token)
            return

    @Slot(str, int)
    def select(self, user, token):
        self.busy.emit(True)
        try:
            if self.active:
                try:
                    self.client.cancel()
                except GreetdError:
                    pass
                self.active = False
            resp = self.client.create_session(user)
            if resp.get("type") == "error" and "already" in resp.get("description", ""):
                self.client.cancel()
                resp = self.client.create_session(user)
            self.active = True
            self._handle(resp, token)
        except GreetdError as e:
            self.active = False
            self.error.emit(str(e), token)
        finally:
            self.busy.emit(False)

    @Slot(str, int)
    def answer(self, text, token):
        self.busy.emit(True)
        try:
            self._handle(self.client.answer(text), token)
        except GreetdError as e:
            self.active = False
            self.error.emit(str(e), token)
        finally:
            self.busy.emit(False)

    @Slot(list, list, int)
    def start(self, cmd, env, token):
        self.busy.emit(True)
        try:
            resp = self.client.start_session(cmd, env)
            if resp.get("type") == "error" and env:
                # starsze greetd (< 0.9) nie znają pola „env” — zmienne przekazujemy przez env(1)
                resp = self.client.start_session(["/usr/bin/env"] + list(env) + list(cmd))
            if resp.get("type") == "success":
                self.active = False
                self.started.emit()
            else:
                self.error.emit(resp.get("description", "start_session"), token)
        except GreetdError as e:
            self.error.emit(str(e), token)
        finally:
            self.busy.emit(False)

    @Slot()
    def cancel(self):
        if self.active:
            try:
                self.client.cancel()
            except GreetdError:
                pass
            self.active = False


class Auth(QObject):
    """Fasada używana przez okno. Każde polecenie ma numer (token) — odpowiedzi na stare polecenia
    (np. po kliknięciu innego konta) okno pomija."""
    _select = Signal(str, int)
    _answer = Signal(str, int)
    _start = Signal(list, list, int)
    _cancel = Signal()

    def __init__(self, client, parent=None):
        super().__init__(parent)
        self.thread = QThread()
        self.worker = _Worker(client)
        self.worker.moveToThread(self.thread)
        self._select.connect(self.worker.select)
        self._answer.connect(self.worker.answer)
        self._start.connect(self.worker.start)
        self._cancel.connect(self.worker.cancel)
        self.prompt, self.ready, self.failed = self.worker.prompt, self.worker.ready, self.worker.failed
        self.message, self.started, self.error = self.worker.message, self.worker.started, self.worker.error
        self.busy = self.worker.busy
        self.token = 0
        self.thread.start()

    def select(self, user):
        self.token += 1
        self._select.emit(user, self.token)
        return self.token

    def answer(self, text):
        self._answer.emit(text, self.token)

    def start(self, cmd, env):
        self._start.emit(list(cmd), list(env), self.token)

    def cancel(self):
        self.token += 1
        self._cancel.emit()

    def shutdown(self):
        self.thread.quit()
        self.thread.wait(2000)
