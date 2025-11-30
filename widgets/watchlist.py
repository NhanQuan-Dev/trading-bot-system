# widgets/watchlist.py

from PyQt6.QtWidgets import QListWidget
from PyQt6.QtCore import pyqtSignal


class WatchlistWidget(QListWidget):
    symbolSelected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.currentTextChanged.connect(self._on_current_text_changed)

    def set_symbols(self, symbols):
        self.clear()
        self.addItems(symbols)

    def _on_current_text_changed(self, text: str):
        if text:
            self.symbolSelected.emit(text)
