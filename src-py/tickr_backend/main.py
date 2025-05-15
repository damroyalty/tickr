import sys
import os
from PySide6.QtWidgets import QApplication
from tickr_backend.ui import TickrUI
import qtmodernredux6


def run_app():
    app = QApplication(sys.argv)
    window = TickrUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    run_app()