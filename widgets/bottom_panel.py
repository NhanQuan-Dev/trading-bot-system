# widgets/bottom_panel.py

from PyQt6.QtWidgets import QWidget, QTabWidget, QVBoxLayout, QTableWidget, QTableWidgetItem
from PyQt6.QtCore import Qt


class BottomPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Positions
        self.positions_table = QTableWidget()
        self.positions_table.setColumnCount(8)
        self.positions_table.setHorizontalHeaderLabels(
            ["Symbol", "Side", "Entry", "Mark", "Qty", "PnL", "SL", "TP"]
        )
        self.positions_table.verticalHeader().setVisible(False)
        self.positions_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.positions_table.setAlternatingRowColors(True)

        self.tabs.addTab(self.positions_table, "Positions")

        # Trades
        self.trades_table = QTableWidget()
        self.trades_table.setColumnCount(7)
        self.trades_table.setHorizontalHeaderLabels(
            ["Time", "Symbol", "Side", "Price", "Qty", "PnL", "Status"]
        )
        self.trades_table.verticalHeader().setVisible(False)
        self.trades_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.trades_table.setAlternatingRowColors(True)

        self.tabs.addTab(self.trades_table, "Trade History")

    # ---- Load data ----
    def load_positions(self, data):
        """
        data: list of tuples (symbol, side, entry, mark, qty, pnl, sl, tp)
        """
        table = self.positions_table
        table.setRowCount(len(data))

        for row, row_data in enumerate(data):
            for col, value in enumerate(row_data):
                item = QTableWidgetItem(str(value))
                if col == 1:  # side
                    if value.upper() == "LONG":
                        item.setForeground(Qt.GlobalColor.darkGreen)
                    else:
                        item.setForeground(Qt.GlobalColor.red)
                elif col not in (0, 1):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                table.setItem(row, col, item)

        table.resizeColumnsToContents()

    def load_trades(self, data):
        """
        data: list of tuples (time, symbol, side, price, qty, pnl, status)
        """
        table = self.trades_table
        table.setRowCount(len(data))

        for row, row_data in enumerate(data):
            for col, value in enumerate(row_data):
                item = QTableWidgetItem(str(value))
                if col == 2:  # side
                    if value.upper() == "LONG":
                        item.setForeground(Qt.GlobalColor.darkGreen)
                    else:
                        item.setForeground(Qt.GlobalColor.red)
                elif col in (3, 4, 5):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                table.setItem(row, col, item)

        table.resizeColumnsToContents()
