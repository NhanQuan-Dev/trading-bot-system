# widgets/chart_area.py

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt


class ChartArea(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        self.label = QLabel(
            "📈 Chart Area\n\n(Placeholder)\nNhúng matplotlib / pyqtgraph ở đây."
        )
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet(
            "QLabel { border: 1px solid #555; font-size: 16px; padding: 20px; }"
        )
        layout.addWidget(self.label)

    def set_symbol(self, symbol: str):
        # Sau này bạn có thể load/refresh chart theo symbol
        self.label.setText(f"📈 Chart for {symbol}\n\n(Placeholder)")
