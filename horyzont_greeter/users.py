"""Konta pokazywane na ekranie powitalnym.

Źródła: /etc/passwd (zakres UID z /etc/login.defs) oraz AccountsService — obraz konta
(ten sam, który ustawia Horyzont w Panelu sterowania → Konta użytkowników), pełna nazwa,
wskazówka do hasła, konta systemowe i zablokowane.
"""
import json
import os
import pwd
import shutil
import subprocess

NOLOGIN = ("nologin", "false", "sync", "shutdown", "halt")


class Account:
    __slots__ = ("name", "uid", "real_name", "home", "shell", "icon", "hint", "logged_in")

    def __init__(self, name, uid, real_name="", home="", shell="", icon="", hint="", logged_in=False):
        self.name, self.uid = name, uid
        self.real_name = real_name or name
        self.home, self.shell = home, shell
        self.icon, self.hint = icon, hint
        self.logged_in = logged_in

    def __repr__(self):
        return f"Account({self.name!r}, {self.uid})"


def uid_range():
    lo, hi = 1000, 60000
    try:
        with open("/etc/login.defs", encoding="utf-8") as f:
            for line in f:
                p = line.split()
                if len(p) >= 2 and p[0] == "UID_MIN" and p[1].isdigit():
                    lo = int(p[1])
                elif len(p) >= 2 and p[0] == "UID_MAX" and p[1].isdigit():
                    hi = int(p[1])
    except OSError:
        pass
    return lo, hi


def _busctl_json(args, timeout=3):
    if not shutil.which("busctl"):
        return None
    try:
        r = subprocess.run(["busctl", "--system", "--json=short"] + args, capture_output=True, text=True,
                           timeout=timeout, stdin=subprocess.DEVNULL)
        if r.returncode != 0:
            return None
        return json.loads(r.stdout)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def accountsservice_info():
    """{nazwa: {icon, real_name, hint, system, locked}} z AccountsService (pusty słownik, gdy niedostępny)."""
    res = {}
    d = _busctl_json(["call", "org.freedesktop.Accounts", "/org/freedesktop/Accounts",
                      "org.freedesktop.Accounts", "ListCachedUsers"])
    if not d:
        return res
    try:
        paths = d["data"][0]
    except (KeyError, IndexError, TypeError):
        return res
    for path in paths[:64]:
        props = _busctl_json(["call", "org.freedesktop.Accounts", path, "org.freedesktop.DBus.Properties",
                              "GetAll", "s", "org.freedesktop.Accounts.User"])
        try:
            data = props["data"][0]
        except (KeyError, IndexError, TypeError):
            continue

        def val(k, default=""):
            v = data.get(k)
            return v.get("data", default) if isinstance(v, dict) else default
        name = val("UserName")
        if not name:
            continue
        res[name] = {"icon": val("IconFile"), "real_name": val("RealName"), "hint": val("PasswordHint"),
                     "system": bool(val("SystemAccount", False)), "locked": bool(val("Locked", False))}
    return res


def logged_in_users():
    """Nazwy kont, które mają otwartą sesję graficzną lub tekstową."""
    names = set()
    try:
        r = subprocess.run(["loginctl", "list-sessions", "--no-legend"], capture_output=True, text=True, timeout=3,
                           stdin=subprocess.DEVNULL)
        for line in r.stdout.splitlines():
            p = line.split()
            if len(p) >= 3 and p[1].isdigit():
                names.add(p[2])
    except (OSError, subprocess.TimeoutExpired):
        pass
    return names


def accounts(hidden=(), use_accountsservice=True, check_logged_in=True):
    lo, hi = uid_range()
    info = accountsservice_info() if use_accountsservice else {}
    logged = logged_in_users() if check_logged_in else set()
    out = []
    seen = set()
    for p in sorted(pwd.getpwall(), key=lambda p: p.pw_uid):
        if p.pw_name in seen or p.pw_name in hidden:
            continue
        if not (lo <= p.pw_uid <= hi):
            continue
        if os.path.basename(p.pw_shell or "") in NOLOGIN:
            continue
        a = info.get(p.pw_name, {})
        if a.get("system") or a.get("locked"):
            continue
        seen.add(p.pw_name)
        gecos = (p.pw_gecos or "").split(",")[0].strip()
        icon = a.get("icon") or ""
        if not icon or not os.access(icon, os.R_OK):
            icon = ""
            for cand in (f"/var/lib/AccountsService/icons/{p.pw_name}", os.path.join(p.pw_dir or "/nonexistent", ".face")):
                if os.access(cand, os.R_OK):
                    icon = cand
                    break
        out.append(Account(p.pw_name, p.pw_uid, a.get("real_name") or gecos, p.pw_dir, p.pw_shell, icon,
                           a.get("hint") or "", p.pw_name in logged))
    return out


def lookup(name):
    """Konto podane z ręki (tryb klasyczny): None, gdy nie istnieje."""
    try:
        p = pwd.getpwnam(name)
    except KeyError:
        return None
    gecos = (p.pw_gecos or "").split(",")[0].strip()
    return Account(p.pw_name, p.pw_uid, gecos, p.pw_dir, p.pw_shell)


def demo_accounts():
    return [Account("jan", 1000, "Jan Kowalski", hint="imię psa"),
            Account("anna", 1001, "Anna", logged_in=True),
            Account("gosc", 1002, "Gość")]
