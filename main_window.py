# main_window.py

import sys
from PyQt6.QtWidgets import (
    QMainWindow,
    QDockWidget,
    QToolBar,
    QMessageBox,
    QLabel,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence

from widgets.chart_area import ChartArea
from widgets.watchlist import WatchlistWidget
from widgets.orderbook import OrderBookTable
from widgets.bottom_panel import BottomPanel
from widgets.trading_dialog import TradingDialog, OrderData
from data.mock_data import (
    get_watchlist_symbols,
    get_mock_prices,
    get_mock_orderbook,
    get_mock_positions,
    get_mock_trades,
)
from settings_dialog import SettingsDialog

class TradingTerminalWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Trading Terminal - Modular PyQt6 Demo")
        self.resize(1200, 700)

        self.current_symbol = "BTCUSDT"  # Track current symbol
        self.symbol_prices = get_mock_prices()

        self._create_menu_bar()
        self._create_tool_bar()
        self._create_central_chart()
        self._create_left_watchlist_dock()
        self._create_right_orderbook_dock()
        self._create_bottom_panel_dock()
        self._create_status_bar()

    # ----- Menu -----
    def _create_menu_bar(self):
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("File")
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = menu_bar.addMenu("View")
        view_menu.addAction("Reset Layout", self.reset_layout)

        # --- Trade Menu ---
        trade_menu = menu_bar.addMenu("Trade")
        new_order_action = QAction("New Order...", self)
        new_order_action.setShortcut(QKeySequence("F2"))
        new_order_action.triggered.connect(self.open_trading_dialog)
        trade_menu.addAction(new_order_action)

        # --- Settings ---
        settings_menu = menu_bar.addMenu("Settings")
        settings_action = QAction("API & Database...", self)
        settings_action.triggered.connect(self.open_settings_dialog)
        settings_menu.addAction(settings_action)
        help_menu = menu_bar.addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    # ----- Toolbar -----
    def _create_tool_bar(self):
        tool_bar = QToolBar("Main Toolbar", self)
        tool_bar.setMovable(False)
        self.addToolBar(tool_bar)

        start_action = QAction("Start", self)
        start_action.triggered.connect(self.on_start_clicked)
        tool_bar.addAction(start_action)

        stop_action = QAction("Stop", self)
        stop_action.triggered.connect(self.on_stop_clicked)
        tool_bar.addAction(stop_action)

    # ----- Central: Chart -----
    def _create_central_chart(self):
        self.chart_area = ChartArea(self)
        self.setCentralWidget(self.chart_area)

    # ----- Left Dock: Watchlist -----
    def _create_left_watchlist_dock(self):
        dock = QDockWidget("Watchlist", self)
        dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)

        self.watchlist = WatchlistWidget()
        self.watchlist.set_symbols(get_watchlist_symbols())
        self.watchlist.symbolSelected.connect(self.on_symbol_selected)

        dock.setWidget(self.watchlist)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)

    # ----- Right Dock: Orderbook -----
    def _create_right_orderbook_dock(self):
        dock = QDockWidget("Order Book", self)
        dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea)

        self.orderbook_table = OrderBookTable()
        self.orderbook_table.load_data(get_mock_orderbook())

        dock.setWidget(self.orderbook_table)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

    # ----- Bottom Dock: Positions/Trades -----
    def _create_bottom_panel_dock(self):
        dock = QDockWidget("Positions / Trades", self)
        dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea | Qt.DockWidgetArea.TopDockWidgetArea)

        self.bottom_panel = BottomPanel()
        self.bottom_panel.load_positions(get_mock_positions())
        self.bottom_panel.load_trades(get_mock_trades())
        
        # Kết nối signal để xử lý close position
        self.bottom_panel.position_close_requested.connect(self.on_close_position_requested)

        dock.setWidget(self.bottom_panel)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)

    # ----- Handlers -----
    def on_symbol_selected(self, symbol: str):
        self.current_symbol = symbol
        self.statusBar().showMessage(f"Selected symbol: {symbol}", 3000)
        self.chart_area.set_symbol(symbol)
        self._update_price_label(symbol)
        # Sau này: refesh orderbook / positions cho symbol này

    def _update_price_label(self, symbol: str):
        price = self.symbol_prices.get(symbol)
        if price is None:
            self.price_label.setText(f"Price: N/A for {symbol}")
        else:
            self.price_label.setText(f"Price: {symbol} = {price:,.2f}")

    def on_start_clicked(self):
        QMessageBox.information(self, "Start", "Start streaming / bot (placeholder).")

    def on_stop_clicked(self):
        QMessageBox.information(self, "Stop", "Stop streaming / bot (placeholder).")

    def reset_layout(self):
        QMessageBox.information(self, "Layout", "Reset layout (tự implement thêm nếu muốn).")

    def show_about_dialog(self):
        QMessageBox.information(
            self,
            "About",
            "Trading Terminal Layout Demo (Modular)\n\nPyQt6 + Dock Widgets + Tables.",
        )

    def _create_status_bar(self):
        status_bar = self.statusBar()

        self.price_label = QLabel("Price: --")
        self.api_status_label = QLabel("API: Not configured")
        self.db_status_label = QLabel("DB: Not configured")

        self.price_label.setStyleSheet("color: #007acc;")
        self.api_status_label.setStyleSheet("color: gray;")
        self.db_status_label.setStyleSheet("color: gray;")

        status_bar.addPermanentWidget(self.price_label)
        status_bar.addPermanentWidget(self.api_status_label)
        status_bar.addPermanentWidget(self.db_status_label)

    def open_settings_dialog(self):
        dialog = SettingsDialog(self)

        dialog.api_connection_tested.connect(self.on_api_connection_tested)
        dialog.db_connection_tested.connect(self.on_db_connection_tested)

        if dialog.exec():
            api = dialog.get_api_settings()
            db = dialog.get_db_settings()
            self.statusBar().showMessage("Settings saved.", 3000)

    def on_api_connection_tested(self, success: bool, environment: str):
        if success:
            self.api_status_label.setText(f"API: Connected ({environment})")
            self.api_status_label.setStyleSheet("color: green;")
        else:
            self.api_status_label.setText("API: Error")
            self.api_status_label.setStyleSheet("color: red;")

    def on_db_connection_tested(self, success: bool):
        if success:
            self.db_status_label.setText("DB: Connected")
            self.db_status_label.setStyleSheet("color: green;")
        else:
            self.db_status_label.setText("DB: Error")
            self.db_status_label.setStyleSheet("color: red;")

    def open_trading_dialog(self):
        """
        Mở dialog đặt lệnh trading (Non-Modal).
        Sử dụng symbol hiện tại và giá hiện tại.
        Dialog không block main window - có thể thao tác song song.
        """
        current_price = self.symbol_prices.get(self.current_symbol, 0.0)
        dialog = TradingDialog(self.current_symbol, current_price, self)
        dialog.order_submitted.connect(self.on_order_submitted)
        dialog.show()  # Non-modal - không block main window

    def on_order_submitted(self, order_data: OrderData):
        """
        Handler khi order được submit từ dialog.
        TODO: Implement logic thật - gọi API, lưu DB, cập nhật UI.
        """
        QMessageBox.information(
            self,
            "Order Submitted",
            f"Order placed successfully!\n\n"
            f"Symbol: {order_data.symbol}\n"
            f"Side: {order_data.side}\n"
            f"Type: {order_data.order_type.value}\n"
            f"Quantity: {order_data.quantity}\n"
            f"Leverage: {order_data.leverage}x\n\n"
            f"TODO: Implement real order execution."
        )
        self.statusBar().showMessage(f"Order submitted: {order_data.side} {order_data.quantity} {order_data.symbol}", 5000)

    def on_close_position_requested(self, symbol: str, side: str):
        """
        Handler khi user click nút Close position.
        Sau này implement logic thật: gọi API close position, cập nhật DB, v.v.
        """
        reply = QMessageBox.question(
            self,
            "Close Position",
            f"Bạn có chắc muốn đóng position {side} {symbol}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # TODO: Implement logic close position thật
            # - Gọi API exchange
            # - Cập nhật database
            # - Refresh bảng positions
            self.statusBar().showMessage(f"Closing position: {side} {symbol}...", 3000)
            QMessageBox.information(
                self,
                "Close Position",
                f"Position {side} {symbol} đã được đóng (placeholder).\nSau này sẽ implement logic thật."
            )

    
    
