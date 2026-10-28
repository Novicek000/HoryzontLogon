"""Klient protokołu greetd (gniazdo z zmiennej GREETD_SOCK).

Każda wiadomość to 4 bajty długości (kolejność bajtów maszyny) i obiekt JSON.
Żądania: create_session, post_auth_message_response, start_session, cancel_session.
Odpowiedzi: success, error, auth_message.

``DemoClient`` udaje greetd (podgląd ekranu bez logowania; hasło „demo”).
"""
import json
import os
import socket
import struct
import time


class GreetdError(Exception):
    pass


class Client:
    def __init__(self, path=None):
        self.path = path or os.environ.get("GREETD_SOCK", "")
        self.sock = None

    def connect(self):
        if not self.path:
            raise GreetdError("GREETD_SOCK nie jest ustawione — ekran powitalny musi być uruchomiony przez greetd")
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(self.path)
        self.sock = s

    def close(self):
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None

    def _recv_exact(self, n):
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise GreetdError("greetd zamknął połączenie")
            buf += chunk
        return buf

    def request(self, obj):
        if self.sock is None:
            self.connect()
        data = json.dumps(obj).encode("utf-8")
        try:
            self.sock.sendall(struct.pack("=I", len(data)) + data)
            n = struct.unpack("=I", self._recv_exact(4))[0]
            return json.loads(self._recv_exact(n).decode("utf-8"))
        except (OSError, ValueError, struct.error) as e:
            self.close()
            raise GreetdError(str(e))

    # wygodne skróty
    def create_session(self, username):
        return self.request({"type": "create_session", "username": username})

    def answer(self, response):
        return self.request({"type": "post_auth_message_response", "response": response})

    def start_session(self, cmd, env=None):
        req = {"type": "start_session", "cmd": list(cmd)}
        if env:
            req["env"] = list(env)
        return self.request(req)

    def cancel(self):
        return self.request({"type": "cancel_session"})


class DemoClient:
    """Udawany greetd do podglądu (``horyzont-greeter --demo``). Hasło dla każdego konta: demo."""

    PASSWORD = "demo"

    def __init__(self, passwordless=()):
        self.user = None
        self.stage = None
        self.passwordless = set(passwordless)
        self.started = None

    def close(self):
        pass

    def create_session(self, username):
        if self.user:
            return {"type": "error", "error_type": "error", "description": "a session is already being configured"}
        self.user = username
        if username in self.passwordless:
            self.stage = "ready"
            return {"type": "success"}
        self.stage = "password"
        return {"type": "auth_message", "auth_message_type": "secret", "auth_message": "Password: "}

    def answer(self, response):
        if self.stage == "password":
            time.sleep(0.6)
            if response == self.PASSWORD:
                self.stage = "ready"
                return {"type": "success"}
            self.user = self.stage = None
            return {"type": "error", "error_type": "auth_error", "description": "pam_authenticate: AUTH_ERR"}
        return {"type": "error", "error_type": "error", "description": "no auth question pending"}

    def start_session(self, cmd, env=None):
        if self.stage != "ready":
            return {"type": "error", "error_type": "error", "description": "session not ready"}
        self.started = (self.user, list(cmd), list(env or []))
        return {"type": "success"}

    def cancel(self):
        self.user = self.stage = None
        return {"type": "success"}
