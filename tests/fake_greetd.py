"""Udawany greetd do testów: python3 tests/fake_greetd.py /ścieżka/gniazda
Konta: jan / haslo (z komunikatem informacyjnym PAM), anna / bez hasła, otp / haslo + kod 123."""
import json, os, socket, struct, sys, threading

USERS = {"jan": ["haslo"], "anna": [], "otp": ["haslo", "123"]}
log = []

def serve(conn):
    st = {"user": None, "step": 0, "ok": False}
    def send(o):
        d = json.dumps(o).encode(); conn.sendall(struct.pack("=I", len(d)) + d)
    def prompt():
        steps = USERS[st["user"]]
        if st["step"] < len(steps):
            msg = "Password:" if st["step"] == 0 else "Verification code:"
            send({"type": "auth_message", "auth_message_type": "secret", "auth_message": msg})
        else:
            st["ok"] = True; send({"type": "success"})
    while True:
        h = conn.recv(4)
        if not h: return
        n = struct.unpack("=I", h)[0]; buf = b""
        while len(buf) < n: buf += conn.recv(n - len(buf))
        req = json.loads(buf); log.append(req if req.get("type") != "post_auth_message_response" else {"type": "answer", "len": len(req.get("response") or "")})
        print("REQ", log[-1], flush=True)
        t = req["type"]
        if t == "create_session":
            if st["user"]:
                send({"type": "error", "error_type": "error", "description": "a session is already being configured"}); continue
            u = req["username"]
            if u not in USERS:
                send({"type": "auth_message", "auth_message_type": "secret", "auth_message": "Password:"}); st.update(user="__bad__", step=0); continue
            st.update(user=u, step=0, ok=False, info=(u == "jan"))
            if st.get("info"):
                send({"type": "auth_message", "auth_message_type": "info", "auth_message": "Ostatnie logowanie: wczoraj"}); st["info_pending"] = True
            else:
                prompt()
        elif t == "post_auth_message_response":
            if st.get("info_pending"):
                st["info_pending"] = False; prompt(); continue
            if st["user"] == "__bad__":
                st["user"] = None; send({"type": "error", "error_type": "auth_error", "description": "AUTH_ERR"}); continue
            exp = USERS[st["user"]][st["step"]]
            if req.get("response") == exp:
                st["step"] += 1; prompt()
            else:
                st["user"] = None; send({"type": "error", "error_type": "auth_error", "description": "AUTH_ERR"})
        elif t == "start_session":
            if not st["ok"]:
                send({"type": "error", "error_type": "error", "description": "not ready"}); continue
            print("START", st["user"], req.get("cmd"), req.get("env"), flush=True); send({"type": "success"})
        elif t == "cancel_session":
            st.update(user=None, step=0, ok=False); send({"type": "success"})

path = sys.argv[1]
if os.path.exists(path): os.remove(path)
s = socket.socket(socket.AF_UNIX); s.bind(path); s.listen(5)
while True:
    c, _ = s.accept(); threading.Thread(target=serve, args=(c,), daemon=True).start()
