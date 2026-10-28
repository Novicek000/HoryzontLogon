"""Język interfejsu: polski albo angielski (ustawienie ``language`` albo zmienne LANG/LC_ALL)."""
import os

_code = None


def lang_code():
    global _code
    if _code is None:
        from . import config
        lang = (config.get("language") or "").lower()
        if lang not in ("pl", "en"):
            env = os.environ.get("LC_ALL") or os.environ.get("LC_MESSAGES") or os.environ.get("LANG") or ""
            if not env:
                env = _locale_conf()
            lang = "pl" if env.lower().startswith("pl") else "en"
        _code = lang
    return _code


def _locale_conf():
    try:
        with open("/etc/locale.conf", encoding="utf-8") as f:
            for line in f:
                if line.startswith("LANG="):
                    return line.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    return ""


def T(pl, en):
    return pl if lang_code() == "pl" else en
