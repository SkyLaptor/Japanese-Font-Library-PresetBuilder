import argparse
import sys

from PySide6.QtWidgets import QApplication

from src.gui.main_window import run_app


def parse_cli_args(argv: list[str]) -> tuple[bool, str | None, list[str]]:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--lang", type=str, default=None)
    parsed, qt_args = parser.parse_known_args(argv[1:])

    app_argv = [argv[0], *qt_args]
    return parsed.debug, parsed.lang, app_argv


def main():
    debug, lang, app_argv = parse_cli_args(sys.argv)

    app = QApplication(app_argv)
    sys.exit(run_app(app, debug=debug, lang=lang))


if __name__ == "__main__":
    main()
