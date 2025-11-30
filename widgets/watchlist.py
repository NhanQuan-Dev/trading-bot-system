# widgets/watchlist.py

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QListWidget
from PyQt6.QtCore import pyqtSignal


class WatchlistWidget(QWidget):
    symbolSelected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._all_symbols = []

        layout = QVBoxLayout(self)
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search symbol...")
        self.search_box.textChanged.connect(self._filter_symbols)

        self.list_widget = QListWidget()
        self.list_widget.currentTextChanged.connect(self._on_current_text_changed)

        layout.addWidget(self.search_box)
        layout.addWidget(self.list_widget)

    def set_symbols(self, symbols):
        self._all_symbols = symbols
        self._filter_symbols(self.search_box.text())

    def _filter_symbols(self, text: str):
        self.list_widget.clear()
        text_lower = text.lower()
        for symbol in self._all_symbols:
            if text_lower in symbol.lower():
                self.list_widget.addItem(symbol)

    def _on_current_text_changed(self, text: str):
        if text:
            self.symbolSelected.emit(text)
