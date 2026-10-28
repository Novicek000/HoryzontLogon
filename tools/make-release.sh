#!/bin/bash
# Buduje paczkę wydania: dist/horyzont-greeter-<wersja>.tar.gz oraz dist/SHA256SUMS.
# Użycie: tools/make-release.sh   (z katalogu głównego repozytorium)
set -e
cd "$(dirname "$0")/.."
VER="$(python3 -m horyzont_greeter version)"
NAME="horyzont-greeter-$VER"
OUT="dist"
mkdir -p "$OUT"
TMP="$(mktemp -d)"
mkdir "$TMP/$NAME"
tar --exclude=__pycache__ --exclude='*.pyc' --exclude=.git --exclude=dist --exclude=tests -cf - . | tar -xf - -C "$TMP/$NAME"
tar czf "$OUT/$NAME.tar.gz" --owner=0 --group=0 -C "$TMP" "$NAME"
(cd "$OUT" && sha256sum "$NAME.tar.gz" > SHA256SUMS)
rm -rf "$TMP"
echo "Gotowe: $OUT/$NAME.tar.gz"
echo "Utwórz wydanie: gh release create v$VER $OUT/$NAME.tar.gz $OUT/SHA256SUMS --title \"Ekran powitalny Horyzont $VER\""
