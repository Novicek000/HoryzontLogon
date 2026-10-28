"""Ustawienia ekranu powitalnego.

Ustawienia administratora: /etc/horyzont-greeter/greeter.json (zapisuje je ``horyzont-greeter-config``).
Stan (ostatni użytkownik, wybrane sesje): /var/lib/horyzont-greeter/state.json — katalog należy do
użytkownika, jako który działa ekran powitalny (domyślnie ``greetd``).
"""
import json
import os

VERSION = "0.1.0"
NAME_PL = "Ekran powitalny Horyzont"
NAME_EN = "Horyzont Welcome Screen"

PKG_DIR = os.path.dirname(os.path.abspath(__file__))
SHARE_DIR = os.path.dirname(PKG_DIR)          # $PREFIX/share/horyzont-greeter
PREFIX = os.path.dirname(os.path.dirname(SHARE_DIR))
LIBEXEC_DIR = os.path.join(PREFIX, "libexec", "horyzont-greeter")
ETC_DIR = os.environ.get("HORYZONT_GREETER_ETC", "/etc/horyzont-greeter")
SETTINGS_FILE = os.path.join(ETC_DIR, "greeter.json")
STATE_DIR = os.environ.get("HORYZONT_GREETER_STATE", "/var/lib/horyzont-greeter")
STATE_FILE = os.path.join(STATE_DIR, "state.json")

DEFAULTS = {
    "style": "welcome",          # welcome (ekran powitalny z listą kont) / classic (okno „Logowanie”)
    "color_scheme": "teal",      # teal / graphite / plum / blue — jak schematy Horyzontu
    "language": "",              # "" = według LANG, albo pl / en
    "hidden_users": [],          # konta niewidoczne na liście
    "show_sessions": True,       # wybór sesji (Horyzont, GNOME…) w dolnym pasku
    "default_session": "horyzont",
    "show_logged_in": True,      # „Zalogowany” pod nazwą konta z otwartą sesją
    "remember_last_user": True,
    "screen_blank_minutes": 10,  # wygaszenie (czarny ekran) po bezczynności; 0 = nigdy
    "logo_text": "Horyzont",
    "subtitle": "",              # pusty = nazwa systemu z /etc/os-release
    "footer_hint": True,         # podpowiedź o Kontach użytkowników w prawym dolnym rogu
    "allow_power": True,         # przycisk „Wyłącz komputer”
    "numlock": False,            # Num Lock włączony przy starcie
    "autologin": None,           # {"user": ..., "session": ...} — automatyczne logowanie po starcie komputera
}


def _load(path):
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
            return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


_settings = None


def settings(reload=False):
    global _settings
    if _settings is None or reload:
        s = dict(DEFAULTS)
        s.update(_load(SETTINGS_FILE))
        _settings = s
    return _settings


def get(key, default=None):
    return settings().get(key, DEFAULTS.get(key, default))


def save_settings(values):
    """Zapis ustawień administratora (wymaga uprawnień do /etc/horyzont-greeter)."""
    cur = _load(SETTINGS_FILE)
    cur.update(values)
    os.makedirs(ETC_DIR, exist_ok=True)
    tmp = SETTINGS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cur, f, ensure_ascii=False, indent=1)
    os.chmod(tmp, 0o644)
    os.replace(tmp, SETTINGS_FILE)
    settings(reload=True)


# ------------------------------------------------------------------ stan ekranu powitalnego
def state():
    return _load(STATE_FILE)


def save_state(**values):
    """Zapisuje stan (najlepiej, jak się da — brak uprawnień nie jest błędem)."""
    cur = state()
    cur.update(values)
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        tmp = STATE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cur, f, ensure_ascii=False)
        os.replace(tmp, STATE_FILE)
        return True
    except OSError:
        return False


def os_name():
    """Nazwa systemu do podpisu pod logo (np. „Fedora Linux 43”)."""
    info = {}
    for p in ("/etc/os-release", "/usr/lib/os-release"):
        try:
            with open(p, encoding="utf-8") as f:
                for line in f:
                    if "=" in line:
                        k, v = line.rstrip("\n").split("=", 1)
                        info[k] = v.strip().strip('"')
            break
        except OSError:
            continue
    name = info.get("NAME", "Linux")
    ver = info.get("VERSION_ID", "")
    return f"{name} {ver}".strip()


def horyzont_installed():
    """Czy na komputerze jest środowisko Horyzont (wtedy domyślną sesją jest Horyzont)."""
    return any(os.path.exists(p) for p in ("/usr/share/wayland-sessions/horyzont.desktop",
                                           "/usr/local/share/horyzont/horyzont", "/usr/share/horyzont/horyzont"))
