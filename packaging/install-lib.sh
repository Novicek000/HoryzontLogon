# Ekran powitalny Horyzont — wspólne funkcje instalatora (install.sh) i aktualizatora (update.sh).
# Plik jest wczytywany przez „source”, nie uruchamiaj go bezpośrednio.

say()  { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m ✓\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m !!\033[0m %s\n' "$*"; }
err()  { printf '\033[1;31m xx\033[0m %s\n' "$*" >&2; }

# greetd — demon logowania (PAM, uruchamianie sesji); labwc — kompozytor, w którym działa ekran powitalny
REQUIRED_PKGS="greetd labwc python3-pyside6 qt6-qtwayland polkit"
# zalecane: nazwa:opis
RECOMMENDED_PKGS="
greetd-selinux:reguły SELinux dla greetd (Fedora)
accountsservice:obrazy kont i pełne nazwy użytkowników
wine-tahoma-fonts-system:czcionka Tahoma (jak w środowisku Horyzont)
dejavu-sans-fonts:czcionka zapasowa
policycoreutils-python-utils:semanage — etykieta SELinux dla katalogu stanu ekranu powitalnego
"
INSTALLED_OK=""
SKIPPED=""

detect_dnf() {
    DNF="$(command -v dnf5 || command -v dnf || true)"
    DNF_SKIP=""
    if [ -n "$DNF" ]; then
        if "$DNF" --version 2>/dev/null | grep -qi "dnf5\|^5\."; then DNF_SKIP="--skip-unavailable"
        else DNF_SKIP="--setopt=strict=0"; fi
    fi
}

pkg_installed() { rpm -q "$1" >/dev/null 2>&1 || rpm -q --whatprovides "$1" >/dev/null 2>&1; }

install_required() {
    [ -n "$DNF" ] || { warn "Brak dnf — pomijam instalację pakietów."; return 0; }
    local missing=""
    for p in $REQUIRED_PKGS; do pkg_installed "$p" || missing="$missing $p"; done
    if [ -z "$missing" ]; then ok "Wymagane pakiety są już zainstalowane."; return 0; fi
    say "Instalowanie wymaganych pakietów:$missing"
    $SUDO "$DNF" install -y $DNF_SKIP $missing || { err "Nie udało się zainstalować:$missing"; return 1; }
    for p in $missing; do pkg_installed "$p" || err "Pakiet $p jest niedostępny w repozytoriach."; done
}

install_recommended() {
    [ -n "$DNF" ] || return 0
    local todo=""
    while IFS=: read -r p desc; do
        [ -z "$p" ] && continue
        pkg_installed "$p" || todo="$todo $p"
    done <<EOT
$RECOMMENDED_PKGS
EOT
    [ -n "$todo" ] && $SUDO "$DNF" install -y $DNF_SKIP $todo >/tmp/horyzont-greeter-dnf.log 2>&1 || true
    # gdy cała transakcja się nie uda (np. konflikt jednego pakietu) — próbujemy każdy osobno
    for p in $todo; do
        pkg_installed "$p" || $SUDO "$DNF" install -y "$p" >>/tmp/horyzont-greeter-dnf.log 2>&1 || true
    done
    for p in $todo; do
        desc="$(printf '%s\n' "$RECOMMENDED_PKGS" | sed -n "s/^$p://p")"
        if pkg_installed "$p"; then INSTALLED_OK="$INSTALLED_OK\n   $p — $desc"
        else SKIPPED="$SKIPPED\n   $p — $desc (niedostępny)"; fi
    done
}

verify_required() {
    local bad=0
    command -v greetd >/dev/null 2>&1 || { err "Brak greetd:  sudo dnf install greetd"; bad=1; }
    command -v labwc >/dev/null 2>&1 || { err "Brak kompozytora labwc:  sudo dnf install labwc"; bad=1; }
    for mod in PySide6.QtWidgets PySide6.QtSvg; do
        python3 -c "import $mod" 2>/dev/null || { err "Brak modułu Pythona $mod (python3-pyside6)."; bad=1; }
    done
    command -v agreety >/dev/null 2>&1 || warn "Brak agreety — zapasowe logowanie tekstowe będzie niedostępne."
    [ $bad = 0 ] && ok "Wszystkie wymagane składniki są obecne."
    return $bad
}

# kopiowanie plików do $PREFIX (podmiana katalogu w jednym kroku — działający ekran powitalny się nie psuje)
copy_files() {
    local SRC="$1"
    PKGDIR="$PREFIX/share/horyzont-greeter"
    LIBEXEC="$PREFIX/libexec/horyzont-greeter"
    say "Kopiowanie plików do $PKGDIR ..."
    $SUDO mkdir -p "$PKGDIR" "$PREFIX/bin" "$LIBEXEC"
    $SUDO chmod 755 "$PKGDIR" "$LIBEXEC"
    $SUDO rm -rf "$PKGDIR/horyzont_greeter.new"
    $SUDO cp -r "$SRC/horyzont_greeter" "$PKGDIR/horyzont_greeter.new"
    $SUDO find "$PKGDIR/horyzont_greeter.new" -name "__pycache__" -type d -prune -exec rm -rf {} +
    # repozytorium aktualizacji: z HORYZONT_GREETER_REPO, z archiwum albo z poprzedniej instalacji
    if [ -n "$HORYZONT_GREETER_REPO" ]; then
        echo "$HORYZONT_GREETER_REPO" | $SUDO tee "$PKGDIR/horyzont_greeter.new/REPO" >/dev/null
    elif [ -f "$SRC/REPO" ]; then
        $SUDO cp "$SRC/REPO" "$PKGDIR/horyzont_greeter.new/REPO"
    elif [ ! -s "$PKGDIR/horyzont_greeter.new/REPO" ] && [ -s "$PKGDIR/horyzont_greeter/REPO" ]; then
        $SUDO cp "$PKGDIR/horyzont_greeter/REPO" "$PKGDIR/horyzont_greeter.new/REPO"
    fi
    $SUDO rm -rf "$PKGDIR/horyzont_greeter.old"
    [ -d "$PKGDIR/horyzont_greeter" ] && $SUDO mv "$PKGDIR/horyzont_greeter" "$PKGDIR/horyzont_greeter.old"
    $SUDO mv "$PKGDIR/horyzont_greeter.new" "$PKGDIR/horyzont_greeter"
    $SUDO rm -rf "$PKGDIR/horyzont_greeter.old"
    for d in labwc greetd systemd; do
        $SUDO rm -rf "$PKGDIR/$d"; $SUDO cp -r "$SRC/share/$d" "$PKGDIR/$d"
    done
    $SUDO cp "$SRC/update.sh" "$SRC/uninstall.sh" "$PKGDIR/"
    $SUDO mkdir -p "$PKGDIR/packaging"
    $SUDO cp "$SRC/packaging/install-lib.sh" "$PKGDIR/packaging/"
    for f in "$SRC"/share/libexec/*; do
        $SUDO sh -c "sed 's#@PKGDIR@#$PKGDIR#g; s#@LIBEXEC@#$LIBEXEC#g' '$f' > '$LIBEXEC/$(basename "$f").new'"
        $SUDO chmod 755 "$LIBEXEC/$(basename "$f").new"
        $SUDO mv "$LIBEXEC/$(basename "$f").new" "$LIBEXEC/$(basename "$f")"
    done
    $SUDO sh -c "cat > '$LIBEXEC/update-agent'" <<EOT
#!/bin/sh
# Ekran powitalny Horyzont — agent aktualizacji (jako root)
export PYTHONPATH="$PKGDIR"
exec /usr/bin/python3 -P -m horyzont_greeter update-agent "\$@"
EOT
    $SUDO chmod 755 "$LIBEXEC/update-agent"
    for f in "$SRC"/bin/*; do
        $SUDO sh -c "sed 's#@PKGDIR@#$PKGDIR#g' '$f' > '$PREFIX/bin/$(basename "$f")'"
        $SUDO chmod 755 "$PREFIX/bin/$(basename "$f")"
    done
    $SUDO python3 -m compileall -q "$PKGDIR/horyzont_greeter" >/dev/null 2>&1 || true
    install_cursors
}

# wskaźniki myszy Horyzontu na ekranie powitalnym (gdy jest zainstalowane środowisko Horyzont)
install_cursors() {
    local H=""
    for p in /usr/local/share/horyzont /usr/share/horyzont; do [ -d "$p/horyzont" ] && H="$p" && break; done
    [ -n "$H" ] || return 0
    local T; T="$(mktemp -d)"
    if HOME="$T" XDG_DATA_HOME="$T/.local/share" QT_QPA_PLATFORM=offscreen PYTHONPATH="$H" \
        timeout 120 python3 -m horyzont gen-cursors >/dev/null 2>&1 && [ -d "$T/.icons/Horyzont/cursors" ]; then
        $SUDO rm -rf "$PKGDIR/icons"
        $SUDO mkdir -p "$PKGDIR/icons"
        $SUDO cp -r "$T/.icons/Horyzont" "$PKGDIR/icons/Horyzont"
        $SUDO chmod -R a+rX "$PKGDIR/icons"
        ok "Wskaźniki myszy Horyzontu dla ekranu powitalnego"
    fi
    rm -rf "$T"
}

install_system_files() {
    $SUDO sh -c "sed 's#@AGENT@#$LIBEXEC/update-agent#g' '$PKGDIR/systemd/horyzont-greeter-updates.service' > /etc/systemd/system/horyzont-greeter-updates.service"
    $SUDO cp "$PKGDIR/systemd/horyzont-greeter-updates.timer" /etc/systemd/system/
    $SUDO mkdir -p /etc/horyzont-greeter /var/lib/horyzont-greeter
    if command -v systemctl >/dev/null; then
        $SUDO systemctl daemon-reload 2>/dev/null || true
        $SUDO systemctl enable horyzont-greeter-updates.timer >/dev/null 2>&1 || true
    fi
    # opis dla Horyzont Updates i odświeżenie konfiguracji greetd (jeśli ekran powitalny jest włączony)
    $SUDO "$PREFIX/bin/horyzont-greeter-config" refresh || warn "Nie udało się odświeżyć konfiguracji."
}

print_summary() {
    echo
    say "Podsumowanie"
    [ -n "$INSTALLED_OK" ] && { echo "  Zainstalowane dodatki:"; printf "$INSTALLED_OK\n"; }
    [ -n "$SKIPPED" ] && { echo "  Pominięte:"; printf "$SKIPPED\n"; }
    return 0
}
