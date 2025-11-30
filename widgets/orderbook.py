# widgets/orderbook.py

from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem
from PyQt6.QtCore import Qt


class OrderBookTable(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["Side", "Price", "Qty"])
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)

    def load_data(self, data):
        """
        data: list of tuples (side, price, qty)
        """
        self.setRowCount(len(data))

        for row, (side, price, qty) in enumerate(data):
            side_item = QTableWidgetItem(side)
            price_item = QTableWidgetItem(str(price))
            qty_item = QTableWidgetItem(str(qty))

            if side.upper() == "ASK":
                side_item.setForeground(Qt.GlobalColor.red)
            else:
                side_item.setForeground(Qt.GlobalColor.darkGreen)

            price_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            qty_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            self.setItem(row, 0, side_item)
            self.setItem(row, 1, price_item)
            self.setItem(row, 2, qty_item)

        self.resizeColumnsToContents()
