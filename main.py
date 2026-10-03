import sys

from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication

from src.constants import APP_NAME
from src.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setOrganizationName("ClentIndustries")
    app.setApplicationName(APP_NAME)
    app.setFont(QFont("Segoe UI", 10))
    app.setWindowIcon(QIcon("edu-automata.ico"))

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
