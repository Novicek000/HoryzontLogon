#!/bin/bash
# Instalator ekranu powitalnego Horyzont (menedżer logowania w stylu klasycznego pulpitu) dla Fedory.
#
# Użycie:  ./install.sh                         instalacja do /usr/local i ustawienie jako ekran logowania
#          ./install.sh --no-enable             tylko instalacja (włączysz później: sudo horyzont-greeter-config enable)
#          ./install.sh --yes                   bez pytań
#          PREFIX=/usr ./install.sh
#          HORYZONT_GREETER_REPO=uzytkownik/repo ./install.sh   (repozytorium GitHub z aktualizacjami)
#
# Instalator sam pobiera przez dnf: greetd (demon logowania), labwc (kompozytor), PySide6 (Qt) i dodatki.
# Działa niezależnie od środowiska Horyzont, ale gdy Horyzont jest zainstalowany, używa jego wskaźników myszy,
# a Horyzont Updates pokazuje też aktualizacje ekranu powitalnego.
set -e
umask 022
PREFIX="${PREFIX:-/usr/local}"
SRC="$(cd "$(dirname "$0")" && pwd)"
SUDO=""
[ "$(id -u)" -ne 0 ] && SUDO="sudo"
ENABLE=1; YES=0
for a in "$@"; do
    case "$a" in
        --no-enable) ENABLE=0;;
        --yes|-y) YES=1;;
        *) echo "Nieznana opcja: $a"; exit 2;;
    esac
done
. "$SRC/packaging/install-lib.sh"

grep -qi fedora /etc/os-release 2>/dev/null || warn "To nie wygląda na Fedorę — instalacja pakietów przez dnf może się nie udać."
detect_dnf
install_required || { err "Przerwano. Sprawdź połączenie z Internetem i repozytoria dnf."; exit 1; }
install_recommended
verify_required || { err "Instalacja przerwana — brakuje składników wymienionych wyżej."; exit 1; }
copy_files "$SRC"
install_system_files
print_summary
echo
if [ $ENABLE = 1 ]; then
    CUR="$(basename "$(readlink /etc/systemd/system/display-manager.service 2>/dev/null)" .service)"
    if [ $YES = 0 ] && [ -t 0 ]; then
        echo "Ekran powitalny Horyzont zastąpi obecny ekran logowania (${CUR:-brak})."
        echo "Poprzedni przywrócisz poleceniem: sudo horyzont-greeter-config disable"
        read -r -p "Ustawić go teraz jako ekran logowania? [T/n] " a
        case "$a" in n|N) ENABLE=0;; esac
    fi
fi
if [ $ENABLE = 1 ]; then
    if $SUDO "$PREFIX/bin/horyzont-greeter-config" enable; then
        ok "Gotowe. Uruchom ponownie komputer, żeby zobaczyć ekran powitalny."
    else
        err "Ekran powitalny jest zainstalowany, ale nie został ustawiony jako ekran logowania."
        exit 1
    fi
else
    ok "Zainstalowano. Podgląd: horyzont-greeter --preview; włączenie: sudo horyzont-greeter-config enable"
fi
