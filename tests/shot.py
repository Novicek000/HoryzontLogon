"""Zrzuty ekranu do sprawdzania wyglądu: python3 tests/shot.py WxH out.png [scenariusz]"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
size, out = sys.argv[1], sys.argv[2]
scen = sys.argv[3] if len(sys.argv) > 3 else "idle"
os.environ["HORYZONT_GREETER_WINDOW"] = size
os.environ.setdefault("HORYZONT_GREETER_STATE", "/tmp/hg-state")
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from horyzont_greeter import greetd, users, sessions, config
from horyzont_greeter.ui import style
from horyzont_greeter.ui.welcome import GreeterWindow
app = QApplication(["x"])
app.setStyle("Fusion"); app.setFont(style.font(12))
if os.environ.get("SCHEME"): config.settings()["color_scheme"] = os.environ["SCHEME"]
if scen == "classic": config.settings()["style"] = "classic"
sess = [sessions.Session("horyzont", "Horyzont", "true", "wayland", ["Horyzont"], ""),
        sessions.Session("gnome", "GNOME", "true", "wayland", ["GNOME"], "")]
accts = users.demo_accounts()
if scen == "many":
    accts = accts + [users.Account(f"u{i}", 1010+i, f"Użytkownik {i}") for i in range(6)]
client = greetd.DemoClient(passwordless=("gosc",))
w = GreeterWindow(client, accts, sess, demo=True, windowed=True)
w.start(True)
def step(n=[0]):
    n[0]+=1
    if n[0]==1:
        if scen in ("selected","wrong","caps","welcome","turnoff","prompt"): w.activate(w.tiles[0])
        if scen == "many": w.activate(w.tiles[3])
    if n[0]==3:
        if scen=="wrong": w.tiles[0].edit.setText("zle"); w.submit(w.tiles[0])
        if scen=="caps": w.caps_balloon(w.tiles[0], True)
        if scen=="welcome": w.tiles[0].edit.setText("demo"); w.submit(w.tiles[0])
        if scen=="turnoff": w.turn_off()
        if scen=="cad": w.open_classic(can_cancel=True)
        if scen=="prompt": w._ask_extra("secret", "Nowe hasło:")
    if n[0]==14:
        w.grab().save(out); print("saved", out); app.exit(0)
t=QTimer(); t.timeout.connect(step); t.start(150)
app.exec()
