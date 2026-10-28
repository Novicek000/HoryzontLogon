"""Uruchomienie ekranu powitalnego.

    horyzont-greeter                 # normalnie (uruchamiane przez greetd w kompozytorze labwc)
    horyzont-greeter --preview       # podgląd w oknie: prawdziwe konta, logowanie wyłączone (hasło „demo”)
    horyzont-greeter --demo          # podgląd z przykładowymi kontami
    horyzont-greeter --window        # w oknie zamiast na pełnym ekranie
"""
import os
import sys


def main(argv):
    demo = "--demo" in argv
    preview = "--preview" in argv or demo
    windowed = "--window" in argv or preview
    if "--fullscreen" in argv:
        windowed = False
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    from .. import config, greetd, sessions, users
    from ..i18n import T, lang_code
    from . import style
    from .welcome import GreeterWindow

    app = QApplication([sys.argv[0]] + [a for a in argv if not a.startswith("--")])
    app.setApplicationName("horyzont-greeter")
    app.setDesktopFileName("horyzont-greeter")
    app.setStyle("Fusion")
    app.setFont(style.font(12))
    app.setQuitOnLastWindowClosed(False)

    hidden = config.get("hidden_users", []) or []
    if demo:
        accounts = users.demo_accounts()
    else:
        accounts = users.accounts(hidden, check_logged_in=config.get("show_logged_in", True))
    sess = sessions.available(lang_code())
    if preview:
        client = greetd.DemoClient(passwordless=("gosc",) if demo else ())
    else:
        client = greetd.Client()
        try:
            client.connect()
        except (greetd.GreetdError, OSError) as e:
            print("horyzont-greeter:", e, file=sys.stderr)
            print(T("Użyj --preview, aby obejrzeć ekran powitalny bez logowania.",
                    "Use --preview to look at the welcome screen without logging in."), file=sys.stderr)
            return 1
    for cand in (os.environ.get("HORYZONT_GREETER_WRAPPER", ""), os.path.join(config.LIBEXEC_DIR, "session-wrapper"),
                 "/usr/local/libexec/horyzont-greeter/session-wrapper", "/usr/libexec/horyzont-greeter/session-wrapper"):
        if cand and os.access(cand, os.X_OK):
            wrapper = cand
            break
    else:
        wrapper = None
    w = GreeterWindow(client, accounts, sess, demo=preview, windowed=windowed, wrapper=wrapper)
    w.start(windowed)
    rc = app.exec()
    if preview and getattr(client, "started", None):
        print("start_session:", client.started)
    return rc
