"""Sesje do wyboru: pliki .desktop z wayland-sessions i xsessions."""
import os
import shlex
import shutil

WAYLAND_DIRS = ["/usr/local/share/wayland-sessions", "/usr/share/wayland-sessions"]
X11_DIRS = ["/usr/local/share/xsessions", "/usr/share/xsessions"]


class Session:
    __slots__ = ("id", "name", "exec", "type", "desktop_names", "path")

    def __init__(self, id_, name, exec_, type_, desktop_names, path):
        self.id, self.name, self.exec, self.type = id_, name, exec_, type_
        self.desktop_names, self.path = desktop_names, path

    def label(self):
        return self.name + (" (X11)" if self.type == "x11" else "")

    def __repr__(self):
        return f"Session({self.id!r}, {self.type})"


def _parse(path, lang):
    entry = {}
    in_main = False
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if line.startswith("["):
                    in_main = line == "[Desktop Entry]"
                    continue
                if in_main and "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    entry[k.strip()] = v.strip()
    except OSError:
        return None
    if entry.get("Hidden", "").lower() == "true" or entry.get("NoDisplay", "").lower() == "true":
        return None
    name = entry.get(f"Name[{lang}]") or entry.get("Name") or os.path.basename(path)[:-8]
    return entry, name


def _exists(cmd):
    if not cmd:
        return False
    try:
        prog = shlex.split(cmd)[0]
    except ValueError:
        return False
    return bool(shutil.which(prog)) or (os.path.isabs(prog) and os.access(prog, os.X_OK))


def available(lang="en"):
    out = []
    seen = set()
    have_startx = bool(shutil.which("startx"))
    for dirs, typ in ((WAYLAND_DIRS, "wayland"), (X11_DIRS, "x11")):
        if typ == "x11" and not have_startx:
            continue
        for d in dirs:
            try:
                names = sorted(os.listdir(d))
            except OSError:
                continue
            for fn in names:
                if not fn.endswith(".desktop"):
                    continue
                sid = fn[:-8]
                key = sid if typ == "wayland" else sid + ":x11"
                if key in seen:
                    continue
                parsed = _parse(os.path.join(d, fn), lang)
                if not parsed:
                    continue
                entry, name = parsed
                exe = entry.get("Exec", "")
                if not exe:
                    continue
                if entry.get("TryExec") and not _exists(entry["TryExec"]):
                    continue
                if not _exists(exe):
                    continue
                # GNOME „Wayland” i „Xorg” mają tę samą nazwę — Xorg pomijamy, gdy jest wersja Wayland
                seen.add(key)
                dn = [x for x in entry.get("DesktopNames", "").split(";") if x]
                out.append(Session(key, name, exe, typ, dn, os.path.join(d, fn)))
    wl_names = {s.name for s in out if s.type == "wayland"}
    out = [s for s in out if not (s.type == "x11" and s.name in wl_names and "xorg" not in s.id.lower())]
    return out


def find(sessions, sid):
    for s in sessions:
        if s.id == sid:
            return s
    return None


def default(sessions, preferred="horyzont"):
    return find(sessions, preferred) or find(sessions, "horyzont") or (sessions[0] if sessions else None)


def command(session, wrapper=None):
    """(cmd, env) dla żądania start_session."""
    args = [a for a in shlex.split(session.exec) if not (len(a) == 2 and a.startswith("%"))]
    desktop = session.desktop_names[0] if session.desktop_names else session.id.split(":")[0]
    env = [f"XDG_SESSION_TYPE={session.type}",
           f"XDG_SESSION_DESKTOP={session.id.split(':')[0]}",
           f"XDG_CURRENT_DESKTOP={':'.join(session.desktop_names) or desktop}"]
    if session.type == "x11":
        args = ["startx", "/usr/bin/env"] + args + ["--", "-keeptty"]
    if wrapper and os.access(wrapper, os.X_OK):
        args = [wrapper] + args
    return args, env


def fallback_shell():
    """Brak plików sesji: logowanie do powłoki tekstowej."""
    return Session("shell", "Shell", "/bin/bash -l", "tty", [], "")
