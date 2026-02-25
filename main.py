import sys

from PySide6.QtWidgets import QApplication

from src.gui.main_window import run_app


def main():
    app = QApplication(sys.argv)
    sys.exit(run_app(app))


if __name__ == "__main__":
    main()
