"""horyzont-greeter-config — ustawienia ekranu powitalnego.

    horyzont-greeter-config status                 stan (włączony ekran logowania, wersja, aktualizacje)
    horyzont-greeter-config enable                 ustaw ekran powitalny Horyzont jako ekran logowania
    horyzont-greeter-config disable                przywróć poprzedni ekran logowania (np. GDM)
    horyzont-greeter-config preview                podgląd w oknie (logowanie wyłączone)
    horyzont-greeter-config style welcome|classic  ekran powitalny z listą kont / klasyczne okno logowania
    horyzont-greeter-config scheme teal|graphite|plum|blue   schemat kolorów
    horyzont-greeter-config hide KONTO | show KONTO          ukryj / pokaż konto na liście
    horyzont-greeter-config autologin KONTO [SESJA] | autologin off
    horyzont-greeter-config session SESJA          sesja domyślna (np. horyzont, gnome)
    horyzont-greeter-config set KLUCZ WARTOŚĆ      dowolne ustawienie z /etc/horyzont-greeter/greeter.json
    horyzont-greeter-config check-updates          sprawdź, czy jest nowsza wersja
    horyzont-greeter-config update                 pobierz i zainstaluj nowszą wersję
    horyzont-greeter-config updates auto|notify|off|horyzont|default   tryb aktualizacji
    horyzont-greeter-config repo WŁAŚCICIEL/NAZWA  repozytorium GitHub z wydaniami
"""
import json
import os
import pwd
import re
import shlex
import shutil
import subprocess
import sys

from . import config, sessions
from .updates import core as upd

GREETD_DIR = os.environ.get("HORYZONT_GREETD_DIR", "/etc/greetd")
GREETD_CONF = os.path.join(GREETD_DIR, "config.toml")
BACKUP = GREETD_CONF + ".horyzont-orig"
PREV_DM = os.path.join(config.ETC_DIR, "previous-dm")
MARK = "# Horyzont — konfiguracja greetd"
DMS = ("gdm", "sddm", "lightdm", "lxdm", "xdm", "ly", "greetd")
SYSTEMD = "/etc/systemd/system"


def say(*a):
    print(*a, flush=True)


def need_root(argv):
    if os.geteuid() == 0:
        return
    exe = shutil.which("horyzont-greeter-config") or sys.argv[0]
    for tool in (["sudo"], ["pkexec"]):
        if shutil.which(tool[0]):
            os.execvp(tool[0], tool + [exe] + argv)
    say("Wymagane uprawnienia administratora (sudo).")
    sys.exit(1)


def sh(args, check=False):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=120)
        if check and r.returncode != 0:
            say(f"  !! {' '.join(args)}: {(r.stderr or r.stdout).strip()}")
        return r.returncode, (r.stdout + r.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return 127, str(e)


# ------------------------------------------------------------------ greetd
def read_greetd():
    try:
        with open(GREETD_CONF, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def is_ours(text=None):
    text = read_greetd() if text is None else text
    return MARK in text or "horyzont-greeter/start-greeter" in text


def greeter_user(text=None):
    """Użytkownik ekranu powitalnego z sekcji [default_session] (Fedora: greetd)."""
    text = read_greetd() if text is None else text
    sect = re.split(r"^\[default_session\]\s*$", text, flags=re.M)
    if len(sect) > 1:
        m = re.search(r'^\s*user\s*=\s*"([^"]+)"', sect[1].split("\n[")[0], re.M)
        if m:
            return m.group(1)
    for cand in ("greetd", "greeter", "_greetd"):
        try:
            pwd.getpwnam(cand)
            return cand
        except KeyError:
            continue
    return "greetd"


def vt_number(text=None):
    text = read_greetd() if text is None else text
    m = re.search(r"^\s*vt\s*=\s*(\S+)", text, re.M)
    return m.group(1) if m else "1"


def toml_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def autologin_block():
    al = config.get("autologin")
    if not isinstance(al, dict) or not al.get("user"):
        return ""
    sess = sessions.find(sessions.available("en"), al.get("session") or config.get("default_session", "horyzont"))
    if sess is None:
        sess = sessions.default(sessions.available("en"), config.get("default_session", "horyzont"))
    if sess is None:
        return ""
    cmd, env = sessions.command(sess, os.path.join(config.LIBEXEC_DIR, "session-wrapper"))
    full = ["/usr/bin/env"] + env + cmd
    return ("\n# automatyczne logowanie po starcie komputera (horyzont-greeter-config autologin)\n"
            "[initial_session]\n"
            f"command = {toml_str(' '.join(shlex.quote(a) for a in full))}\n"
            f"user = {toml_str(al['user'])}\n")


def write_greetd(user=None):
    old = read_greetd()
    if old and not is_ours(old) and not os.path.exists(BACKUP):
        shutil.copy2(GREETD_CONF, BACKUP)
    user = user or greeter_user(old)
    with open(os.path.join(config.SHARE_DIR, "greetd", "config.toml"), encoding="utf-8") as f:
        tpl = f.read()
    text = (tpl.replace("@VT@", vt_number(old) if old else "1").replace("@LIBEXEC@", config.LIBEXEC_DIR)
            .replace("@USER@", user).replace("@INITIAL@", autologin_block()))
    os.makedirs(GREETD_DIR, exist_ok=True)
    tmp = GREETD_CONF + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.chmod(tmp, 0o644)
    os.replace(tmp, GREETD_CONF)
    return user


def ensure_user(user):
    try:
        pwd.getpwnam(user)
        return True
    except KeyError:
        pass
    say(f"==> Tworzenie użytkownika systemowego {user} (ekran powitalny)")
    rc, out = sh(["useradd", "-r", "-M", "-d", "/var/lib/greetd", "-s", "/sbin/nologin", "-c", "greetd greeter", user],
                 check=True)
    return rc == 0


def ensure_state_dir(user):
    d = config.STATE_DIR
    os.makedirs(d, exist_ok=True)
    try:
        p = pwd.getpwnam(user)
        os.chown(d, p.pw_uid, p.pw_gid)
        for fn in os.listdir(d):
            try:
                os.chown(os.path.join(d, fn), p.pw_uid, p.pw_gid)
            except OSError:
                pass
    except KeyError:
        pass
    os.chmod(d, 0o755)
    selinux_label()


def selinux_label():
    if not shutil.which("selinuxenabled") or sh(["selinuxenabled"])[0] != 0:
        return
    if shutil.which("semanage"):
        rc, out = sh(["semanage", "fcontext", "-a", "-t", "xdm_var_lib_t", config.STATE_DIR + "(/.*)?"])
        if rc != 0 and "already defined" not in out:
            sh(["semanage", "fcontext", "-m", "-t", "xdm_var_lib_t", config.STATE_DIR + "(/.*)?"])
        sh(["restorecon", "-R", config.STATE_DIR])
    else:
        sh(["chcon", "-R", "-t", "xdm_var_lib_t", config.STATE_DIR])
    for d in (config.SHARE_DIR, config.LIBEXEC_DIR, GREETD_DIR):
        sh(["restorecon", "-R", d])


# ------------------------------------------------------------------ menedżer logowania (systemd)
def current_dm():
    link = os.path.join(SYSTEMD, "display-manager.service")
    try:
        target = os.readlink(link)
    except OSError:
        return ""
    return os.path.basename(target).replace(".service", "")


def unit_exists(name):
    return any(os.path.exists(os.path.join(d, f"{name}.service"))
               for d in ("/etc/systemd/system", "/usr/lib/systemd/system", "/lib/systemd/system"))


def switch_dm(to):
    """Ustawia display-manager.service na podaną usługę (zmiana działa po ponownym uruchomieniu)."""
    cur = current_dm()
    if cur and cur != to:
        sh(["systemctl", "disable", f"{cur}.service"])
    rc, out = sh(["systemctl", "enable", "--force", f"{to}.service"], check=True)
    if current_dm() != to:
        # usługa bez Alias=display-manager.service — dowiązanie zakładamy sami
        path = None
        for d in ("/etc/systemd/system", "/usr/lib/systemd/system", "/lib/systemd/system"):
            if os.path.exists(os.path.join(d, f"{to}.service")):
                path = os.path.join(d, f"{to}.service")
                break
        if path:
            link = os.path.join(SYSTEMD, "display-manager.service")
            try:
                os.remove(link)
            except OSError:
                pass
            os.symlink(path, link)
    sh(["systemctl", "set-default", "graphical.target"])
    sh(["systemctl", "daemon-reload"])
    return current_dm() == to


def preflight(user):
    """Czy ekran powitalny ma szansę wystartować (zanim przełączymy menedżer logowania)."""
    problems = []
    if not shutil.which("greetd"):
        problems.append("brak programu greetd (sudo dnf install greetd)")
    if not shutil.which("labwc"):
        problems.append("brak kompozytora labwc (sudo dnf install labwc)")
    env = dict(os.environ, PYTHONPATH=config.SHARE_DIR, QT_QPA_PLATFORM="offscreen")
    test = "import PySide6.QtWidgets, PySide6.QtSvg; import horyzont_greeter.ui.welcome"
    args = ["python3", "-c", test]
    if os.geteuid() == 0 and shutil.which("runuser"):
        try:
            pwd.getpwnam(user)
            args = ["runuser", "-u", user, "--", "env", f"PYTHONPATH={config.SHARE_DIR}", "QT_QPA_PLATFORM=offscreen",
                    "python3", "-c", test]
        except KeyError:
            pass
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=60, env=env, cwd="/")
        if r.returncode != 0:
            problems.append("ekran powitalny nie uruchamia się: " + (r.stderr.strip().splitlines() or ["?"])[-1])
    except (OSError, subprocess.TimeoutExpired) as e:
        problems.append(str(e))
    return problems


def write_component():
    """Opis dla Horyzont Updates — żeby aktualizacje ekranu powitalnego były widoczne w Horyzoncie."""
    d = os.path.dirname(upd.COMPONENT_FILE)
    try:
        os.makedirs(d, exist_ok=True)
        with open(upd.COMPONENT_FILE, "w", encoding="utf-8") as f:
            json.dump(upd.component_descriptor(), f, ensure_ascii=False, indent=1)
        os.chmod(upd.COMPONENT_FILE, 0o644)
    except OSError as e:
        say("  !! nie udało się zapisać", upd.COMPONENT_FILE, e)


# ------------------------------------------------------------------ polecenia
def cmd_enable(args):
    force = "--force" in args
    quiet = "--quiet" in args
    old = read_greetd()
    user = greeter_user(old)
    ensure_user(user)
    problems = preflight(user)
    if problems and not force:
        for p in problems:
            say("  xx", p)
        say("Ekran logowania NIE został zmieniony. Popraw błędy albo użyj: horyzont-greeter-config enable --force")
        return 1
    cur = current_dm()
    if cur and cur not in ("greetd",) and not os.path.exists(PREV_DM):
        os.makedirs(config.ETC_DIR, exist_ok=True)
        with open(PREV_DM, "w") as f:
            f.write(cur + "\n")
    write_greetd(user)
    ensure_state_dir(user)
    write_component()
    ok = switch_dm("greetd")
    if not quiet:
        if ok:
            say(f"Ekran powitalny Horyzont jest ekranem logowania (greetd, użytkownik {user}).")
            if cur and cur != "greetd":
                say(f"Poprzedni ekran logowania ({cur}) został wyłączony — przywrócisz go poleceniem:"
                    " horyzont-greeter-config disable")
            say("Zmiana zadziała po ponownym uruchomieniu komputera.")
        else:
            say("  !! Nie udało się ustawić greetd jako ekranu logowania (systemctl enable greetd).")
    return 0 if ok else 1


def cmd_disable(args):
    prev = ""
    try:
        with open(PREV_DM) as f:
            prev = f.read().strip()
    except OSError:
        pass
    if os.path.exists(BACKUP):
        shutil.copy2(BACKUP, GREETD_CONF)
        os.remove(BACKUP)
    elif is_ours():
        os.remove(GREETD_CONF)
    if not prev:
        for dm in ("gdm", "sddm", "lightdm", "lxdm"):
            if unit_exists(dm):
                prev = dm
                break
    if prev and prev != "greetd" and unit_exists(prev):
        switch_dm(prev)
        say(f"Przywrócono ekran logowania: {prev} (po ponownym uruchomieniu komputera).")
    elif prev == "greetd":
        say("Przywrócono poprzednią konfigurację greetd.")
    else:
        sh(["systemctl", "disable", "greetd.service"])
        say("Wyłączono ekran powitalny. Nie znaleziono innego ekranu logowania — po restarcie pojawi się konsola.")
    try:
        os.remove(PREV_DM)
    except OSError:
        pass
    return 0


def refresh():
    """Po aktualizacji: odświeżenie konfiguracji greetd (nowe ścieżki, automatyczne logowanie) — tylko gdy
    ekran powitalny jest włączony."""
    write_component()
    if is_ours():
        user = greeter_user()
        write_greetd(user)
        ensure_state_dir(user)


def cmd_status(args):
    say(f"{config.NAME_PL} {config.VERSION}  ({config.SHARE_DIR})")
    dm = current_dm() or "?"
    say(f"Ekran logowania (display-manager.service): {dm}")
    say(f"greetd używa ekranu powitalnego Horyzont: {'tak' if is_ours() else 'nie'}"
        f"{' (użytkownik ' + greeter_user() + ')' if is_ours() else ''}")
    s = config.settings()
    say(f"Styl: {s['style']}, schemat: {s['color_scheme']}, ukryte konta: {', '.join(s['hidden_users']) or 'brak'}")
    al = s.get("autologin")
    say(f"Automatyczne logowanie: {al['user'] + ' (' + (al.get('session') or 'domyślna sesja') + ')' if isinstance(al, dict) and al.get('user') else 'wyłączone'}")
    us = upd.settings()
    say(f"Aktualizacje: tryb {upd.effective_mode(us)} ({us['mode']}), repozytorium: {us['github_repo'] or '(nieustawione)'}")
    st = upd.read_status()
    if st.get("checked"):
        av = st.get("available")
        say(f"Ostatnie sprawdzenie: {st['checked']}" + (f" — dostępna wersja {av['version']}" if av else " — brak nowszej wersji")
            + (f" (błąd: {st['error']})" if st.get("error") else ""))
    return 0


def cmd_set(key, value):
    if key not in config.DEFAULTS:
        say(f"Nieznane ustawienie: {key}. Dostępne: {', '.join(sorted(config.DEFAULTS))}")
        return 2
    default = config.DEFAULTS[key]
    if isinstance(default, bool):
        v = value.lower() in ("1", "true", "tak", "yes", "on")
    elif isinstance(default, int):
        v = int(value)
    elif isinstance(default, list):
        v = [x for x in re.split(r"[,\s]+", value) if x]
    elif default is None:
        v = json.loads(value) if value not in ("", "off", "null") else None
    else:
        v = value
    config.save_settings({key: v})
    say(f"{key} = {json.dumps(v, ensure_ascii=False)}")
    return 0


def main(argv):
    import signal
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd == "status":
        return cmd_status(rest)
    if cmd == "preview":
        os.execvp("python3", ["python3", "-m", "horyzont_greeter", "greeter", "--preview"] + rest)
    if cmd == "check-updates":
        u = upd.check()
        if not upd.settings()["github_repo"]:
            say("Repozytorium aktualizacji nie jest ustawione: horyzont-greeter-config repo właściciel/nazwa")
            return 3
        say(f"Dostępna wersja {u['version']} ({u['title']})" if u else f"Wersja {config.VERSION} jest najnowsza.")
        return 0
    need_root(argv)
    if cmd == "enable":
        return cmd_enable(rest)
    if cmd == "disable":
        return cmd_disable(rest)
    if cmd == "refresh":
        refresh()
        return 0
    if cmd == "style" and rest and rest[0] in ("welcome", "classic"):
        return cmd_set("style", rest[0])
    if cmd == "scheme" and rest:
        return cmd_set("color_scheme", rest[0])
    if cmd in ("hide", "show") and rest:
        hidden = [u for u in config.get("hidden_users", []) if u != rest[0]]
        if cmd == "hide":
            hidden.append(rest[0])
        config.save_settings({"hidden_users": hidden})
        say("Ukryte konta: " + (", ".join(hidden) or "brak"))
        return 0
    if cmd == "session" and rest:
        return cmd_set("default_session", rest[0])
    if cmd == "autologin" and rest:
        if rest[0] in ("off", "wyłącz", "none"):
            config.save_settings({"autologin": None})
            say("Automatyczne logowanie wyłączone.")
        else:
            try:
                pwd.getpwnam(rest[0])
            except KeyError:
                say(f"Nie ma konta {rest[0]}.")
                return 2
            config.save_settings({"autologin": {"user": rest[0], "session": rest[1] if len(rest) > 1 else ""}})
            say(f"Automatyczne logowanie: {rest[0]}.")
        if is_ours():
            write_greetd(greeter_user())
        return 0
    if cmd == "set" and len(rest) >= 2:
        return cmd_set(rest[0], " ".join(rest[1:]))
    if cmd == "update":
        from .updates.agent import update_now
        return update_now()
    if cmd == "updates" and rest and rest[0] in upd.MODES:
        upd.save_settings(mode=rest[0])
        say(f"Tryb aktualizacji: {rest[0]} (działa jako: {upd.effective_mode()})")
        return 0
    if cmd == "repo" and rest:
        if not upd.valid_repo(rest[0]):
            say("Podaj repozytorium w postaci właściciel/nazwa.")
            return 2
        upd.save_settings(github_repo=rest[0])
        os.makedirs(config.ETC_DIR, exist_ok=True)
        with open(os.path.join(config.ETC_DIR, "repo"), "w") as f:
            f.write(rest[0] + "\n")
        write_component()
        say(f"Repozytorium aktualizacji: {rest[0]}")
        return 0
    print(__doc__)
    return 2
