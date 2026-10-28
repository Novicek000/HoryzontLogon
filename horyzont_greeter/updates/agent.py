"""Agent aktualizacji ekranu powitalnego (jako root, z timera systemd albo z horyzont-greeter-config).

    python3 -m horyzont_greeter update-agent --run              # według /etc/horyzont-greeter/updates.json
    python3 -m horyzont_greeter update-agent --install KATALOG  # instalacja pobranej wersji (update.sh)
    python3 -m horyzont_greeter update-agent --update           # sprawdź, pobierz i zainstaluj teraz
"""
import os
import subprocess
import sys

from .. import config
from . import core


def log(*a):
    print("horyzont-greeter-updates:", *a, flush=True)


def install_dir(directory):
    script = os.path.join(directory, "update.sh")
    if not os.path.isfile(script):
        log("brak update.sh w", directory)
        return 2
    r = subprocess.run(["bash", script, "--yes"], cwd=directory)
    return r.returncode


def update_now(quiet=False):
    s = core.settings()
    if not s["github_repo"]:
        log("brak repozytorium aktualizacji — ustaw je: horyzont-greeter-config repo właściciel/nazwa")
        return 3
    u = core.check(s["github_repo"])
    if not u:
        core.write_status(None)
        if not quiet:
            log(f"zainstalowana wersja {config.VERSION} jest najnowsza")
        return 0
    log(f"pobieranie wersji {u['version']} z github.com/{u['repo']} ...")
    d = core.download(u, workdir="/var/tmp" if os.path.isdir("/var/tmp") else None)
    rc = install_dir(d)
    core.write_status(None if rc == 0 else u, None if rc == 0 else f"update.sh: kod {rc}",
                      f"zainstalowano {u['version']}" if rc == 0 else None)
    return rc


def run():
    s = core.settings()
    mode = core.effective_mode(s)
    if mode == "off":
        return 0
    try:
        if mode == "auto":
            return update_now(quiet=True)
        u = core.check(s["github_repo"])
        core.write_status(u)
        if u:
            log(f"dostępna wersja {u['version']} (tryb: {mode})")
    except Exception as e:
        core.write_status(None, str(e))
        log("błąd:", e)
    return 0


def main(argv):
    if os.geteuid() != 0:
        print("horyzont-greeter update-agent: wymaga uprawnień administratora", file=sys.stderr)
        return 1
    if not argv or argv[0] == "--run":
        return run()
    if argv[0] == "--install" and len(argv) > 1:
        return install_dir(argv[1])
    if argv[0] == "--update":
        try:
            return update_now()
        except Exception as e:
            log("błąd:", e)
            return 1
    print(__doc__)
    return 2
