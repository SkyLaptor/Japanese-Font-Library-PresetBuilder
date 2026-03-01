import sys

from PySide6.QtWidgets import QApplication

from src.gui.main_window import run_app


def main():
    debug = "--debug" in sys.argv
    app_argv = [arg for arg in sys.argv if arg != "--debug"]

    app = QApplication(app_argv)
    sys.exit(run_app(app, debug=debug))


if __name__ == "__main__":
    main()
