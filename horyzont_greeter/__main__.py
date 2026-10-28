"""Punkt wejścia: ``python3 -m horyzont_greeter <polecenie>``.

    greeter [--preview|--demo|--window]   ekran powitalny (domyślnie)
    config ...                             ustawienia (to samo co horyzont-greeter-config)
    prepare                                konfiguracja labwc dla ekranu powitalnego (start-greeter)
    update-agent --run|--install KATALOG   aktualizacje (jako root)
    version                                numer wersji
"""
import sys


def main():
    argv = sys.argv[1:]
    if argv and (not argv[0].startswith("-") or argv[0] in ("--version", "-h", "--help")):
        cmd, rest = argv[0], argv[1:]
    else:
        cmd, rest = "greeter", argv
    if cmd == "greeter":
        from .ui.app import main as m
        return m(rest)
    if cmd == "prepare":
        from .prepare import main as m
        return m(rest)
    if cmd == "config":
        from .cli import main as m
        return m(rest)
    if cmd == "update-agent":
        from .updates.agent import main as m
        return m(rest)
    if cmd in ("version", "--version"):
        from . import config
        print(config.VERSION)
        return 0
    if cmd in ("help", "-h", "--help"):
        print(__doc__)
        return 0
    print(f"horyzont-greeter: nieznane polecenie '{cmd}'", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main() or 0)
