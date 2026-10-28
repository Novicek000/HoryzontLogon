"""Aktualizacje ekranu powitalnego — tak samo jak w Horyzont Updates:
najnowsze wydanie z GitHuba (archiwum .tar.gz z SHA256SUMS), a gdy wydań nie ma — najnowszy tag,
a w ostateczności wersja z pliku horyzont_greeter/config.py w głównej gałęzi repozytorium.
Pobrane archiwum zawiera update.sh, który instaluje nową wersję (ustawienia zostają).
"""
import datetime as _dt
import hashlib
import json
import os
import re
import tarfile
import tempfile
import urllib.request

from .. import config

SYSTEM_CONFIG = os.path.join(config.ETC_DIR, "updates.json")
STATUS_FILE = os.path.join(config.STATE_DIR, "updates-status.json")
COMPONENT_FILE = "/etc/horyzont/components.d/horyzont-greeter.json"
VERSION_FILE = "horyzont_greeter/config.py"
MARKER_DIR = "horyzont_greeter"
ASSET_PREFIX = "horyzont-greeter"

# auto — instaluj sam; notify — tylko sprawdzaj; off — wyłączone;
# horyzont — aktualizacjami zajmuje się Horyzont Updates (gdy jest zainstalowany środowisko Horyzont)
MODES = ("default", "auto", "notify", "off", "horyzont")


def settings():
    s = {"mode": "default", "github_repo": ""}
    try:
        with open(SYSTEM_CONFIG, encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, dict):
            s.update({k: v for k, v in d.items() if k in s})
    except (OSError, ValueError):
        pass
    if s["mode"] not in MODES:
        s["mode"] = "default"
    if not s["github_repo"]:
        s["github_repo"] = default_repo()
    return s


def save_settings(**values):
    cur = {}
    try:
        with open(SYSTEM_CONFIG, encoding="utf-8") as f:
            cur = json.load(f)
    except (OSError, ValueError):
        pass
    cur.update(values)
    os.makedirs(os.path.dirname(SYSTEM_CONFIG), exist_ok=True)
    with open(SYSTEM_CONFIG, "w", encoding="utf-8") as f:
        json.dump(cur, f, indent=1)
    os.chmod(SYSTEM_CONFIG, 0o644)


def default_repo():
    """Repozytorium zapisane przy instalacji (plik REPO obok kodu albo /etc/horyzont-greeter/repo)."""
    for p in (os.path.join(config.PKG_DIR, "REPO"), os.path.join(config.ETC_DIR, "repo")):
        try:
            with open(p, encoding="utf-8") as f:
                v = f.read().strip()
            if valid_repo(v):
                return v
        except OSError:
            continue
    return ""


def valid_repo(v):
    return bool(v) and re.fullmatch(r"[\w.-]+/[\w.-]+", v) is not None


def horyzont_handles_updates():
    """Czy zainstalowany Horyzont (0.4.5+) sam sprawdza aktualizacje dodatków (katalog components.d)."""
    for base in ("/usr/local/share/horyzont", "/usr/share/horyzont"):
        try:
            with open(os.path.join(base, "horyzont", "updates", "core.py"), encoding="utf-8") as f:
                if "components.d" in f.read():
                    return True
        except OSError:
            continue
    return False


def effective_mode(s=None):
    s = s or settings()
    mode = s["mode"]
    if mode == "default":
        mode = "horyzont" if horyzont_handles_updates() else "auto"
    return mode


def parse_version(v):
    v = (v or "").strip().lstrip("vV")
    parts = re.findall(r"\d+", v.split("-")[0])
    return tuple(int(x) for x in parts[:4]) or (0,)


def _github(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": f"HoryzontGreeter/{config.VERSION}",
                                               "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


def _branch_version(repo):
    info = _github(f"https://api.github.com/repos/{repo}") or {}
    branches = [info.get("default_branch")] if info.get("default_branch") else ["main", "master"]
    for br in branches:
        try:
            req = urllib.request.Request(f"https://raw.githubusercontent.com/{repo}/{br}/{VERSION_FILE}",
                                         headers={"User-Agent": f"HoryzontGreeter/{config.VERSION}"})
            with urllib.request.urlopen(req, timeout=20) as r:
                text = r.read().decode("utf-8", "replace")
        except Exception:
            continue
        m = re.search(r'^VERSION\s*=\s*["\']([^"\']+)["\']', text, re.M)
        if not m:
            continue
        body = ""
        commit = _github(f"https://api.github.com/repos/{repo}/commits/{br}")
        if commit:
            body = (commit.get("commit") or {}).get("message", "")
        return {"tag_name": m.group(1), "body": body, "assets": [], "name": f"{m.group(1)} ({br})",
                "tarball_url": f"https://github.com/{repo}/archive/refs/heads/{br}.tar.gz"}
    return None


def check(repo=None, current=None):
    """Najnowsza wersja z GitHuba: słownik {version, url, sums, size, notes, title, repo} albo None."""
    repo = repo or settings()["github_repo"]
    if not valid_repo(repo):
        return None
    data = _github(f"https://api.github.com/repos/{repo}/releases/latest")
    if not data:
        tags = _github(f"https://api.github.com/repos/{repo}/tags")
        if tags:
            tag = tags[0]["name"]
            data = {"tag_name": tag, "body": "", "assets": [], "name": tag,
                    "tarball_url": f"https://api.github.com/repos/{repo}/tarball/{tag}"}
        else:
            data = _branch_version(repo)
            if not data:
                return None
    tag = data.get("tag_name", "")
    if parse_version(tag) <= parse_version(current or config.VERSION):
        return None
    url, size, sums = None, 0, None
    for a in data.get("assets", []):
        n = a.get("name", "")
        if n.endswith((".tar.gz", ".tgz")) and ASSET_PREFIX in n.lower():
            url, size = a.get("browser_download_url"), a.get("size", 0)
        elif n.upper().startswith("SHA256SUM"):
            sums = a.get("browser_download_url")
    url = url or data.get("tarball_url")
    return {"version": tag.lstrip("vV"), "url": url, "sums": sums, "size": size, "notes": data.get("body") or "",
            "title": data.get("name") or tag, "repo": repo}


def download(update, progress=None, workdir=None):
    """Pobiera i rozpakowuje wydanie. Zwraca katalog ze skryptem update.sh."""
    url = update["url"]
    work = tempfile.mkdtemp(prefix="horyzont-greeter-update-", dir=workdir)
    path = os.path.join(work, "greeter.tar.gz")
    req = urllib.request.Request(url, headers={"User-Agent": f"HoryzontGreeter/{config.VERSION}"})
    h = hashlib.sha256()
    with urllib.request.urlopen(req, timeout=60) as r, open(path, "wb") as f:
        total = int(r.headers.get("Content-Length") or update.get("size") or 0)
        done = 0
        while True:
            b = r.read(65536)
            if not b:
                break
            f.write(b)
            h.update(b)
            done += len(b)
            if progress and total:
                progress(int(done * 100 / total))
    if update.get("sums"):
        req = urllib.request.Request(update["sums"], headers={"User-Agent": "HoryzontGreeter"})
        sums = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
        name = os.path.basename(url)
        expected = [l.split()[0] for l in sums.splitlines() if l.strip().endswith(name)]
        if expected and expected[0].lower() != h.hexdigest():
            raise RuntimeError("suma kontrolna pobranego pliku się nie zgadza — aktualizacja przerwana")
    with tarfile.open(path) as t:
        try:
            t.extractall(work, filter="data")
        except TypeError:
            t.extractall(work)
    for root, dirs, files in os.walk(work):
        if "update.sh" in files and MARKER_DIR in dirs:
            return root
    raise RuntimeError("w pobranym archiwum nie ma skryptu update.sh")


def write_status(update=None, error=None, message=None):
    data = {"checked": _dt.datetime.now().isoformat(timespec="seconds"), "current": config.VERSION,
            "available": update, "error": error, "message": message}
    try:
        os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)
        tmp = STATUS_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        os.chmod(tmp, 0o644)
        os.replace(tmp, STATUS_FILE)
    except OSError:
        pass
    return data


def read_status():
    try:
        with open(STATUS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def component_descriptor(version=None, repo=None):
    """Opis dodatku dla Horyzont Updates (/etc/horyzont/components.d/horyzont-greeter.json)."""
    return {"id": "horyzont-greeter", "name": {"pl": config.NAME_PL, "en": config.NAME_EN},
            "version": version or config.VERSION, "repo": repo if repo is not None else settings()["github_repo"],
            "version_file": VERSION_FILE, "marker": MARKER_DIR, "asset_prefix": ASSET_PREFIX,
            "install": "update.sh --yes", "icon": "users"}
