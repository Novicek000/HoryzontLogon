"""Przygotowanie konfiguracji labwc dla ekranu powitalnego (wywoływane przez start-greeter, bez Qt).

Tworzy katalog z rc.xml, menu.xml i plikiem environment (układ klawiatury systemu, motyw wskaźników)
i wypisuje jego ścieżkę.
"""
import os
import re
import shutil
import sys
import tempfile

from . import config


def keyboard():
    """(layout, variant, model, options) — ustawienia z localectl (00-keyboard.conf) albo /etc/vconsole.conf."""
    res = {"layout": "", "variant": "", "model": "", "options": ""}
    for path in ("/etc/X11/xorg.conf.d/00-keyboard.conf", "/etc/X11/xorg.conf.d/00-keyboard.conf.d"):
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except OSError:
            continue
        for key, opt in (("layout", "XkbLayout"), ("variant", "XkbVariant"), ("model", "XkbModel"),
                         ("options", "XkbOptions")):
            m = re.search(r'Option\s+"%s"\s+"([^"]*)"' % opt, text)
            if m:
                res[key] = m.group(1)
        if res["layout"]:
            return res
    try:
        with open("/etc/vconsole.conf", encoding="utf-8") as f:
            for line in f:
                if line.startswith("KEYMAP="):
                    km = line.split("=", 1)[1].strip().strip('"')
                    # pl2 → pl, de-latin1-nodeadkeys → de, us → us
                    m = re.match(r"([a-z]{2,3})", km)
                    if m:
                        res["layout"] = m.group(1)
                elif line.startswith("XKBLAYOUT="):
                    res["layout"] = line.split("=", 1)[1].strip().strip('"')
                elif line.startswith("XKBVARIANT="):
                    res["variant"] = line.split("=", 1)[1].strip().strip('"')
                elif line.startswith("XKBOPTIONS="):
                    res["options"] = line.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    return res


def cursor_env():
    own = os.path.join(config.SHARE_DIR, "icons")
    if os.path.isdir(os.path.join(own, "Horyzont", "cursors")):
        return {"XCURSOR_THEME": "Horyzont", "XCURSOR_SIZE": "24",
                "XCURSOR_PATH": f"{own}:/usr/local/share/icons:/usr/share/icons"}
    for theme in ("Adwaita", "breeze_cursors"):
        if os.path.isdir(f"/usr/share/icons/{theme}/cursors"):
            return {"XCURSOR_THEME": theme, "XCURSOR_SIZE": "24"}
    return {}


def main(argv):
    run = os.environ.get("XDG_RUNTIME_DIR")
    if run and os.path.isdir(run) and os.access(run, os.W_OK):
        cfg = os.path.join(run, "horyzont-greeter-labwc")
    else:
        cfg = tempfile.mkdtemp(prefix="horyzont-greeter-labwc-")
    os.makedirs(cfg, mode=0o700, exist_ok=True)
    src = os.path.join(config.SHARE_DIR, "labwc")
    with open(os.path.join(src, "rc.xml"), encoding="utf-8") as f:
        rc = f.read()
    rc = rc.replace("<!--NUMLOCK-->", "<numlock>on</numlock>" if config.get("numlock", False) else "")
    with open(os.path.join(cfg, "rc.xml"), "w", encoding="utf-8") as f:
        f.write(rc)
    shutil.copyfile(os.path.join(src, "menu.xml"), os.path.join(cfg, "menu.xml"))
    env = {}
    kb = keyboard()
    if kb["layout"]:
        env["XKB_DEFAULT_LAYOUT"] = kb["layout"]
        for k in ("variant", "model", "options"):
            if kb[k]:
                env["XKB_DEFAULT_" + k.upper()] = kb[k]
    env.update(cursor_env())
    env["QT_QPA_PLATFORM"] = "wayland;xcb"
    env["QT_WAYLAND_DISABLE_WINDOWDECORATION"] = "1"
    env["PYTHONPATH"] = config.SHARE_DIR
    with open(os.path.join(cfg, "environment"), "w", encoding="utf-8") as f:
        for k, v in env.items():
            f.write(f"{k}={v}\n")
    # bez autostartu i bez skrótów z ~/.config/labwc użytkownika greetd
    open(os.path.join(cfg, "autostart"), "w").close()
    print(cfg)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
