#!/bin/bash
# Usuwa ekran powitalny Horyzont i przywraca poprzedni ekran logowania (np. GDM).
PREFIX="${PREFIX:-/usr/local}"
SUDO=""; [ "$(id -u)" -ne 0 ] && SUDO="sudo"
if [ -x "$PREFIX/bin/horyzont-greeter-config" ]; then
    $SUDO "$PREFIX/bin/horyzont-greeter-config" disable
fi
$SUDO systemctl disable --now horyzont-greeter-updates.timer 2>/dev/null
$SUDO rm -f /etc/systemd/system/horyzont-greeter-updates.service /etc/systemd/system/horyzont-greeter-updates.timer
$SUDO rm -rf "$PREFIX/share/horyzont-greeter" "$PREFIX/libexec/horyzont-greeter" /etc/horyzont-greeter /var/lib/horyzont-greeter
$SUDO rm -f "$PREFIX/bin/horyzont-greeter" "$PREFIX/bin/horyzont-greeter-config" /etc/horyzont/components.d/horyzont-greeter.json
$SUDO systemctl daemon-reload 2>/dev/null
echo "Ekran powitalny Horyzont został usunięty (greetd i labwc zostają w systemie)."
