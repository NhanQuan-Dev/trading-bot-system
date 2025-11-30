# widgets/bottom_panel.py

from PyQt6.QtWidgets import QWidget, QTabWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal


class BottomPanel(QWidget):
    # Signal để emit khi user click nút Close
    position_close_requested = pyqtSignal(str, str)  # (symbol, side)
    
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Positions
        self.positions_table = QTableWidget()
        self.positions_table.setColumnCount(9)
        self.positions_table.setHorizontalHeaderLabels(
            ["Symbol", "Side", "Entry", "Mark", "Qty", "PnL", "SL", "TP", "Action"]
        )
        self.positions_table.verticalHeader().setVisible(False)
        self.positions_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.positions_table.setAlternatingRowColors(True)
        self.positions_table.setShowGrid(False)
        self.positions_table.setStyleSheet("""
            QTableWidget {
                gridline-color: transparent;
                border: none;
            }
            QTableWidget::item {
                border: none;
            }
            QHeaderView::section {
                border: none;
                background-color: transparent;
                font-weight: normal;
            }
            QHeaderView::section:checked {
                font-weight: normal;
            }
        """)

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
        self.trades_table.setShowGrid(False)
        self.trades_table.setStyleSheet("""
            QTableWidget {
                gridline-color: transparent;
                border: none;
            }
            QTableWidget::item {
                border: none;
            }
            QHeaderView::section {
                border: none;
                background-color: transparent;
                font-weight: normal;
            }
            QHeaderView::section:checked {
                font-weight: normal;
            }
        """)

        self.tabs.addTab(self.trades_table, "Trade History")

    # ---- Load data ----
    def load_positions(self, data):
        """
        data: list of tuples (symbol, side, entry, mark, qty, pnl, sl, tp)
        """
        table = self.positions_table
        table.setRowCount(len(data))

        for row, row_data in enumerate(data):
            # Các cột dữ liệu thông thường
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
            
            # Thêm nút Close ở cột cuối (col 8)
            close_btn = QPushButton("Close")
            close_btn.setFixedSize(50, 20)
            close_btn.setStyleSheet("""
                QPushButton {
                    background-color: #d9534f;
                    color: white;
                    border: none;
                    padding: 2px 4px;
                    border-radius: 3px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #c9302c;
                }
            """)
            
            # Lưu thông tin symbol và side để emit signal
            symbol = row_data[0]
            side = row_data[1]
            close_btn.clicked.connect(
                lambda checked, s=symbol, sd=side: self._on_close_position_clicked(s, sd)
            )
            
            # Tạo container widget để center button
            from PyQt6.QtWidgets import QWidget as QW, QHBoxLayout
            container = QW()
            container_layout = QHBoxLayout(container)
            container_layout.addWidget(close_btn)
            container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            container_layout.setContentsMargins(0, 0, 0, 0)
            
            table.setCellWidget(row, 8, container)

        # Resize các cột khác trước
        table.resizeColumnsToContents()
        
        # Sau đó cố định chiều rộng cột Action và không cho resize
        from PyQt6.QtWidgets import QHeaderView
        table.setColumnWidth(8, 75)
        table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)

    def _on_close_position_clicked(self, symbol: str, side: str):
        """
        Handler khi user click nút Close.
        Emit signal để MainWindow hoặc module khác xử lý logic close position.
        """
        self.position_close_requested.emit(symbol, side)

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
