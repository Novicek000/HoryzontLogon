#!/bin/bash
# Ekran powitalny Horyzont — aktualizacja istniejącej instalacji.
#
#   ./update.sh                      instaluje wersję z tego katalogu (ustawienia zostają)
#   ./update.sh --github wl/repo     pobiera najnowsze wydanie z GitHuba i je instaluje
#   ./update.sh --yes                bez pytań (używane przez agenta aktualizacji i Horyzont Updates)
#
# Aktualizacja nie przełącza ekranu logowania: jeśli ekran powitalny był włączony, zostaje włączony,
# a nowa wersja pojawi się przy następnym wylogowaniu lub ponownym uruchomieniu komputera.
set -e
umask 022
SRC="$(cd "$(dirname "$0")" && pwd)"
YES=0; GITHUB=""
while [ $# -gt 0 ]; do
    case "$1" in
        --yes|-y) YES=1;;
        --github) GITHUB="$2"; shift;;
        *) echo "Nieznana opcja: $1"; exit 2;;
    esac
    shift
done
. "$SRC/packaging/install-lib.sh"

if [ -n "$GITHUB" ]; then
    say "Pobieranie najnowszej wersji z github.com/$GITHUB ..."
    TMP="$(mktemp -d)"
    NEW="$(PYTHONPATH="$SRC" python3 - "$GITHUB" "$TMP" <<'PY'
import sys
from horyzont_greeter.updates import core
repo, tmp = sys.argv[1], sys.argv[2]
u = core.check(repo, current="0")
if not u:
    sys.exit("nie znaleziono wydania")
print(core.download(u, workdir=tmp))
PY
)" || { err "Nie udało się pobrać wydania."; exit 1; }
    echo "$GITHUB" > "$NEW/REPO"
    exec bash "$NEW/update.sh" $( [ $YES = 1 ] && echo --yes )
fi

SUDO=""
if [ "$(id -u)" -ne 0 ]; then
    if command -v sudo >/dev/null 2>&1 && [ -t 0 ]; then SUDO="sudo"
    else exec pkexec bash "$SRC/update.sh" "$@"; fi
fi

if [ -z "$PREFIX" ]; then
    for p in /usr/local /usr; do [ -d "$p/share/horyzont-greeter/horyzont_greeter" ] && PREFIX="$p" && break; done
fi
PREFIX="${PREFIX:-/usr/local}"
OLD="$(PYTHONPATH="$PREFIX/share/horyzont-greeter" python3 -P -m horyzont_greeter version 2>/dev/null || echo '?')"
NEWV="$(PYTHONPATH="$SRC" python3 -P -m horyzont_greeter version 2>/dev/null || echo '?')"
say "Aktualizacja ekranu powitalnego: $OLD → $NEWV (katalog: $PREFIX)"
if [ $YES = 0 ] && [ -t 0 ]; then
    read -r -p "Kontynuować? [T/n] " a
    case "$a" in n|N) exit 0;; esac
fi
detect_dnf
install_required || warn "Nie wszystkie wymagane pakiety udało się zainstalować."
copy_files "$SRC"
install_system_files
ok "Ekran powitalny $NEWV zainstalowany — pojawi się przy następnym wylogowaniu lub ponownym uruchomieniu."
