"""Test przebiegu logowania przez prawdziwy klient greetd i udawany serwer.
python3 tests/flow.py SCENARIUSZ (good | wrong | nopass | otp | classic)"""
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["HORYZONT_GREETER_STATE"] = "/tmp/hg-flow-state"
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from horyzont_greeter import greetd, users, sessions, config
from horyzont_greeter.ui.welcome import GreeterWindow
from horyzont_greeter.ui.dialogs import PromptDialog
scen = sys.argv[1]
app = QApplication(["x"])
if scen == "classic": config.settings()["style"] = "classic"
sess = [sessions.Session("horyzont", "Horyzont", "horyzont-session", "wayland", ["Horyzont", "wlroots"], ""),
        sessions.Session("gnome", "GNOME", "gnome-session", "wayland", ["GNOME"], "")]
accts = [users.Account("jan", 1000, "Jan"), users.Account("anna", 1001, "Anna"), users.Account("otp", 1002, "Otp")]
c = greetd.Client(os.environ["GREETD_SOCK"]); c.connect()
w = GreeterWindow(c, accts, sess, windowed=True, wrapper=None)
w.start(True)
res = {"rc": None}
def later(ms, fn): QTimer.singleShot(ms, fn)
def find_prompt():
    return [d for d in w.findChildren(PromptDialog) if d.isVisible()]
if scen == "good":
    later(300, lambda: (w.activate(w.tiles[0]), None))
    later(900, lambda: (w.tiles[0].edit.setText("haslo"), w.submit(w.tiles[0])))
elif scen == "wrong":
    later(300, lambda: w.activate(w.tiles[0]))
    later(900, lambda: (w.tiles[0].edit.setText("zle"), w.submit(w.tiles[0])))
    later(1800, lambda: print("BALLOON", w.balloon.isVisible(), w.balloon.title, "MODE", w.tiles[0].mode))
    later(2200, lambda: (w.tiles[0].edit.setText("haslo"), w.submit(w.tiles[0])))
elif scen == "fast":   # Enter zanim greetd zapyta o hasło
    later(300, lambda: (w.activate(w.tiles[0]), w.tiles[0].edit.setText("haslo"), w.submit(w.tiles[0])))
elif scen == "nopass":
    later(300, lambda: w.activate(w.tiles[1]))
elif scen == "otp":
    later(300, lambda: w.activate(w.tiles[2]))
    later(900, lambda: (w.tiles[2].edit.setText("haslo"), w.submit(w.tiles[2])))
    later(1600, lambda: (print("PROMPT", [d.label.text() for d in find_prompt()]), find_prompt()[0].edit.setText("123"), find_prompt()[0]._ok()))
elif scen == "switch":
    later(300, lambda: w.activate(w.tiles[0]))
    later(700, lambda: w.activate(w.tiles[2]))
    later(1100, lambda: (w.tiles[2].edit.setText("haslo"), w.submit(w.tiles[2])))
    later(1600, lambda: (find_prompt()[0].edit.setText("123"), find_prompt()[0]._ok()))
elif scen == "classic":
    later(500, lambda: (w.classic.user.setText("jan"), w.classic.password.setText("zle"), w.classic._submit()))
    later(1500, lambda: (print("MSG", [o.label.text()[:30] for o in w.findChildren(QWidget_) if hasattr(o,"label") and hasattr(o.label,"text") and o.isVisible()]), w.overlay and w.overlay.close_overlay()))
    later(1800, lambda: (w.classic.password.setText("haslo"), w.classic._submit()))
from PySide6.QtWidgets import QWidget as QWidget_
later(6000, lambda: (print("TIMEOUT"), app.exit(3)))
rc = app.exec()
print("RC", rc, "STATE", config.state())
