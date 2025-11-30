# main.py

import sys
from PyQt6.QtWidgets import QApplication
from main_window import TradingTerminalWindow


def main():
    app = QApplication(sys.argv)
    window = TradingTerminalWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
