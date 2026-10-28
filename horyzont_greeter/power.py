"""Wyłączanie, ponowne uruchamianie, stan wstrzymania (systemd-logind)."""
import shutil
import subprocess

ACTIONS = {"standby": "suspend", "hibernate": "hibernate", "turnoff": "poweroff", "restart": "reboot"}
CAN = {"standby": "CanSuspend", "hibernate": "CanHibernate", "turnoff": "CanPowerOff", "restart": "CanReboot"}


def can(action):
    """Czy logind pozwala na akcję (yes / challenge / no …). Gdy nie da się sprawdzić — zakładamy, że tak."""
    if not shutil.which("busctl"):
        return True
    try:
        r = subprocess.run(["busctl", "--system", "call", "org.freedesktop.login1", "/org/freedesktop/login1",
                            "org.freedesktop.login1.Manager", CAN[action]], capture_output=True, text=True,
                           timeout=3, stdin=subprocess.DEVNULL)
        if r.returncode != 0:
            return True
        v = r.stdout.split()[-1].strip('"')
        return v in ("yes", "challenge")
    except (OSError, subprocess.TimeoutExpired, IndexError):
        return True


def run(action, demo=False):
    verb = ACTIONS[action]
    if demo:
        print("horyzont-greeter (demo): systemctl", verb)
        return True
    try:
        r = subprocess.run(["systemctl", verb], capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL)
        if r.returncode == 0:
            return True
        r = subprocess.run(["loginctl", verb], capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL)
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False
