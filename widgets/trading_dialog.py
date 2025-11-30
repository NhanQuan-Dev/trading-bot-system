# widgets/trading_dialog.py

from dataclasses import dataclass
from enum import Enum

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton,
    QCheckBox,
    QDoubleSpinBox,
    QSpinBox,
    QButtonGroup,
    QRadioButton,
)


class OrderType(Enum):
    MARKET = "Market"
    LIMIT = "Limit"
    STOP_LIMIT = "Stop Limit"
    STOP_MARKET = "Stop Market"
    TRAILING_STOP = "Trailing Stop"


class PositionMode(Enum):
    ONE_WAY = "One-Way"
    HEDGE = "Hedge"


class MarginMode(Enum):
    CROSS = "Cross"
    ISOLATED = "Isolated"


class TimeInForce(Enum):
    GTC = "GTC"  # Good Till Cancel
    IOC = "IOC"  # Immediate or Cancel
    FOK = "FOK"  # Fill or Kill


@dataclass
class OrderData:
    """Data class để lưu thông tin order"""
    symbol: str
    side: str  # "LONG" or "SHORT"
    order_type: OrderType
    quantity: float
    price: float | None = None  # For limit orders
    stop_price: float | None = None  # For stop orders
    callback_rate: float | None = None  # For trailing stop
    activation_price: float | None = None  # For trailing stop
    stop_loss: float | None = None
    take_profit: float | None = None
    leverage: int = 1
    margin_mode: MarginMode = MarginMode.CROSS
    position_mode: PositionMode = PositionMode.ONE_WAY
    time_in_force: TimeInForce = TimeInForce.GTC


class TradingDialog(QDialog):
    """
    Dialog đặt lệnh trading với đầy đủ chức năng:
    - Multiple order types với dynamic fields
    - Position/Margin mode configuration
    - Real-time calculation
    - Risk management (SL/TP)
    """

    order_submitted = pyqtSignal(OrderData)

    def __init__(self, symbol: str = "BTCUSDT", current_price: float = 0.0, parent=None, symbols: list[str] = None, symbol_prices: dict = None):
        super().__init__(parent)

        self.symbol = symbol
        self.current_price = current_price if current_price > 0 else 62000.5
        self.available_symbols = symbols or ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]
        self.symbol_prices = symbol_prices or {}

        self.setWindowTitle(f"Trading - {symbol}")
        self.resize(550, 750)

        self._init_ui()
        self._connect_signals()
        self._update_order_fields()
        self._calculate_summary()

    def _init_ui(self):
        """Khởi tạo UI"""
        layout = QVBoxLayout(self)

        # Symbol Selection
        layout.addWidget(self._create_symbol_selection_group())

        # Position Settings Group
        layout.addWidget(self._create_position_settings_group())

        # Order Type Selection
        layout.addWidget(self._create_order_type_group())

        # Order Details (Dynamic)
        layout.addWidget(self._create_order_details_group())

        # Risk Management
        layout.addWidget(self._create_risk_management_group())

        # Summary
        layout.addWidget(self._create_summary_group())

        # Action Buttons
        layout.addLayout(self._create_action_buttons())

    def _create_symbol_selection_group(self) -> QGroupBox:
        """Tạo group Symbol Selection"""
        group = QGroupBox("Symbol")
        layout = QHBoxLayout()

        # Symbol combo
        self.symbol_combo = QComboBox()
        self.symbol_combo.addItems(self.available_symbols)
        self.symbol_combo.setCurrentText(self.symbol)
        self.symbol_combo.setMinimumWidth(150)

        # Current price label
        self.current_price_label = QLabel(f"${self.current_price:,.2f}")
        self.current_price_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #007acc;")

        layout.addWidget(QLabel("Select Symbol:"))
        layout.addWidget(self.symbol_combo)
        layout.addStretch()
        layout.addWidget(QLabel("Current Price:"))
        layout.addWidget(self.current_price_label)

        group.setLayout(layout)
        return group

    def _create_position_settings_group(self) -> QGroupBox:
        """Tạo group Position Settings"""
        group = QGroupBox("Position Settings")
        form = QFormLayout()

        # Position Mode
        self.position_mode_combo = QComboBox()
        self.position_mode_combo.addItems([mode.value for mode in PositionMode])
        form.addRow("Position Mode:", self.position_mode_combo)

        # Margin Mode
        self.margin_mode_combo = QComboBox()
        self.margin_mode_combo.addItems([mode.value for mode in MarginMode])
        form.addRow("Margin Mode:", self.margin_mode_combo)

        # Leverage
        self.leverage_spin = QSpinBox()
        self.leverage_spin.setRange(1, 125)
        self.leverage_spin.setValue(5)
        self.leverage_spin.setSuffix("x")
        form.addRow("Leverage:", self.leverage_spin)

        group.setLayout(form)
        return group

    def _create_order_type_group(self) -> QGroupBox:
        """Tạo group Order Type với radio buttons"""
        group = QGroupBox("Order Type")
        layout = QHBoxLayout()

        self.order_type_group = QButtonGroup()

        for order_type in OrderType:
            radio = QRadioButton(order_type.value)
            radio.setProperty("order_type", order_type)
            self.order_type_group.addButton(radio)
            layout.addWidget(radio)

            if order_type == OrderType.MARKET:
                radio.setChecked(True)

        group.setLayout(layout)
        return group

    def _create_order_details_group(self) -> QGroupBox:
        """Tạo group Order Details với dynamic fields"""
        group = QGroupBox("Order Details")
        self.order_form = QFormLayout()

        # Price (for Limit orders)
        self.price_label = QLabel("Price:")
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0.01, 999999.99)
        self.price_spin.setDecimals(2)
        self.price_spin.setValue(self.current_price)
        self.price_spin.setSuffix(" USDT")
        self.order_form.addRow(self.price_label, self.price_spin)

        # Stop Price (for Stop orders)
        self.stop_price_label = QLabel("Stop Price:")
        self.stop_price_spin = QDoubleSpinBox()
        self.stop_price_spin.setRange(0.01, 999999.99)
        self.stop_price_spin.setDecimals(2)
        self.stop_price_spin.setValue(self.current_price * 0.98)
        self.stop_price_spin.setSuffix(" USDT")
        self.order_form.addRow(self.stop_price_label, self.stop_price_spin)

        # Limit Price (for Stop Limit)
        self.limit_price_label = QLabel("Limit Price:")
        self.limit_price_spin = QDoubleSpinBox()
        self.limit_price_spin.setRange(0.01, 999999.99)
        self.limit_price_spin.setDecimals(2)
        self.limit_price_spin.setValue(self.current_price * 0.97)
        self.limit_price_spin.setSuffix(" USDT")
        self.order_form.addRow(self.limit_price_label, self.limit_price_spin)

        # Callback Rate (for Trailing Stop)
        self.callback_label = QLabel("Callback Rate:")
        self.callback_spin = QDoubleSpinBox()
        self.callback_spin.setRange(0.1, 10.0)
        self.callback_spin.setDecimals(2)
        self.callback_spin.setValue(1.0)
        self.callback_spin.setSuffix(" %")
        self.order_form.addRow(self.callback_label, self.callback_spin)

        # Activation Price (for Trailing Stop)
        self.activation_label = QLabel("Activation Price:")
        self.activation_spin = QDoubleSpinBox()
        self.activation_spin.setRange(0.01, 999999.99)
        self.activation_spin.setDecimals(2)
        self.activation_spin.setValue(0.0)
        self.activation_spin.setSuffix(" USDT (Optional)")
        self.order_form.addRow(self.activation_label, self.activation_spin)

        # Time in Force (for Limit orders)
        self.tif_label = QLabel("Time in Force:")
        self.tif_combo = QComboBox()
        self.tif_combo.addItems([tif.value for tif in TimeInForce])
        self.order_form.addRow(self.tif_label, self.tif_combo)

        # Quantity
        self.quantity_spin = QDoubleSpinBox()
        self.quantity_spin.setRange(0.001, 10000.0)
        self.quantity_spin.setDecimals(3)
        self.quantity_spin.setValue(0.5)
        self.quantity_spin.setSuffix(" BTC")
        self.order_form.addRow("Quantity:", self.quantity_spin)

        # Total (calculated)
        self.total_label = QLabel("$31,000.25")
        self.total_label.setStyleSheet("font-weight: bold; color: #007acc;")
        self.order_form.addRow("Total:", self.total_label)

        group.setLayout(self.order_form)
        return group

    def _create_risk_management_group(self) -> QGroupBox:
        """Tạo group Risk Management"""
        group = QGroupBox("Risk Management (Optional)")
        form = QFormLayout()

        # Stop Loss
        sl_layout = QHBoxLayout()
        self.sl_checkbox = QCheckBox()
        self.sl_checkbox.setChecked(False)
        self.sl_spin = QDoubleSpinBox()
        self.sl_spin.setRange(0.01, 999999.99)
        self.sl_spin.setDecimals(2)
        self.sl_spin.setValue(self.current_price * 0.97)
        self.sl_spin.setEnabled(False)
        self.sl_info = QLabel("-3.00% ($-1,000)")
        self.sl_info.setStyleSheet("color: #ef5350;")

        sl_layout.addWidget(self.sl_checkbox)
        sl_layout.addWidget(self.sl_spin)
        sl_layout.addWidget(self.sl_info)
        form.addRow("Stop Loss:", sl_layout)

        # Take Profit
        tp_layout = QHBoxLayout()
        self.tp_checkbox = QCheckBox()
        self.tp_checkbox.setChecked(False)
        self.tp_spin = QDoubleSpinBox()
        self.tp_spin.setRange(0.01, 999999.99)
        self.tp_spin.setDecimals(2)
        self.tp_spin.setValue(self.current_price * 1.05)
        self.tp_spin.setEnabled(False)
        self.tp_info = QLabel("+5.00% ($+1,500)")
        self.tp_info.setStyleSheet("color: #26a69a;")

        tp_layout.addWidget(self.tp_checkbox)
        tp_layout.addWidget(self.tp_spin)
        tp_layout.addWidget(self.tp_info)
        form.addRow("Take Profit:", tp_layout)

        group.setLayout(form)
        return group

    def _create_summary_group(self) -> QGroupBox:
        """Tạo group Summary"""
        group = QGroupBox("Summary")
        form = QFormLayout()

        self.margin_label = QLabel("$6,200")
        self.margin_label.setStyleSheet("font-weight: bold;")
        form.addRow("Margin Required:", self.margin_label)

        self.max_loss_label = QLabel("$1,000 (-3.23%)")
        self.max_loss_label.setStyleSheet("color: #ef5350;")
        form.addRow("Max Loss:", self.max_loss_label)

        self.max_profit_label = QLabel("$1,500 (+4.84%)")
        self.max_profit_label.setStyleSheet("color: #26a69a;")
        form.addRow("Max Profit:", self.max_profit_label)

        self.rr_label = QLabel("1:1.5")
        self.rr_label.setStyleSheet("font-weight: bold; color: #007acc;")
        form.addRow("Risk/Reward:", self.rr_label)

        group.setLayout(form)
        return group

    def _create_action_buttons(self) -> QHBoxLayout:
        """Tạo nút BUY/LONG và SELL/SHORT"""
        layout = QHBoxLayout()

        # BUY/LONG button
        self.buy_button = QPushButton("BUY / LONG")
        self.buy_button.setMinimumHeight(50)
        self.buy_button.setStyleSheet("""
            QPushButton {
                background-color: #26a69a;
                color: white;
                font-size: 16px;
                font-weight: bold;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2bbbad;
            }
            QPushButton:pressed {
                background-color: #00897b;
            }
        """)

        # SELL/SHORT button
        self.sell_button = QPushButton("SELL / SHORT")
        self.sell_button.setMinimumHeight(50)
        self.sell_button.setStyleSheet("""
            QPushButton {
                background-color: #ef5350;
                color: white;
                font-size: 16px;
                font-weight: bold;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #f44336;
            }
            QPushButton:pressed {
                background-color: #e53935;
            }
        """)

        layout.addWidget(self.buy_button)
        layout.addWidget(self.sell_button)

        return layout

    def _connect_signals(self):
        """Kết nối signals"""
        # Symbol changed
        self.symbol_combo.currentTextChanged.connect(self._on_symbol_changed)

        # Order type changed
        self.order_type_group.buttonClicked.connect(self._on_order_type_changed)

        # Value changed → recalculate
        self.quantity_spin.valueChanged.connect(self._calculate_summary)
        self.price_spin.valueChanged.connect(self._calculate_summary)
        self.leverage_spin.valueChanged.connect(self._calculate_summary)

        # SL/TP checkbox
        self.sl_checkbox.toggled.connect(self._on_sl_toggled)
        self.tp_checkbox.toggled.connect(self._on_tp_toggled)

        # SL/TP value changed
        self.sl_spin.valueChanged.connect(self._calculate_sl_info)
        self.tp_spin.valueChanged.connect(self._calculate_tp_info)

        # Action buttons
        self.buy_button.clicked.connect(lambda: self._on_submit_order("LONG"))
        self.sell_button.clicked.connect(lambda: self._on_submit_order("SHORT"))

    def _on_symbol_changed(self, symbol: str):
        """Handler khi symbol thay đổi"""
        self.symbol = symbol
        self.setWindowTitle(f"Trading - {symbol}")
        
        # Cập nhật giá hiện tại nếu có
        if self.symbol_prices and symbol in self.symbol_prices:
            self.current_price = self.symbol_prices[symbol]
            self.current_price_label.setText(f"${self.current_price:,.2f}")
            
            # Cập nhật các giá trị mặc định
            self.price_spin.setValue(self.current_price)
            self.stop_price_spin.setValue(self.current_price * 0.98)
            self.limit_price_spin.setValue(self.current_price * 0.97)
            self.sl_spin.setValue(self.current_price * 0.97)
            self.tp_spin.setValue(self.current_price * 1.05)
            
            # Tính lại summary
            self._calculate_summary()

    def _on_order_type_changed(self):
        """Handler khi order type thay đổi"""
        self._update_order_fields()
        self._calculate_summary()

    def _update_order_fields(self):
        """Cập nhật hiển thị fields dựa trên order type"""
        selected_button = self.order_type_group.checkedButton()
        if not selected_button:
            return

        order_type = selected_button.property("order_type")

        # Hide all optional fields first
        self._hide_field(self.price_label, self.price_spin)
        self._hide_field(self.stop_price_label, self.stop_price_spin)
        self._hide_field(self.limit_price_label, self.limit_price_spin)
        self._hide_field(self.callback_label, self.callback_spin)
        self._hide_field(self.activation_label, self.activation_spin)
        self._hide_field(self.tif_label, self.tif_combo)

        # Show fields based on order type
        if order_type == OrderType.MARKET:
            pass  # No extra fields

        elif order_type == OrderType.LIMIT:
            self._show_field(self.price_label, self.price_spin)
            self._show_field(self.tif_label, self.tif_combo)

        elif order_type == OrderType.STOP_LIMIT:
            self._show_field(self.stop_price_label, self.stop_price_spin)
            self._show_field(self.limit_price_label, self.limit_price_spin)

        elif order_type == OrderType.STOP_MARKET:
            self._show_field(self.stop_price_label, self.stop_price_spin)

        elif order_type == OrderType.TRAILING_STOP:
            self._show_field(self.callback_label, self.callback_spin)
            self._show_field(self.activation_label, self.activation_spin)

    def _hide_field(self, label: QLabel, widget):
        """Ẩn field"""
        label.hide()
        widget.hide()

    def _show_field(self, label: QLabel, widget):
        """Hiện field"""
        label.show()
        widget.show()

    def _on_sl_toggled(self, checked: bool):
        """Handler khi SL checkbox toggle"""
        self.sl_spin.setEnabled(checked)
        self._calculate_summary()

    def _on_tp_toggled(self, checked: bool):
        """Handler khi TP checkbox toggle"""
        self.tp_spin.setEnabled(checked)
        self._calculate_summary()

    def _calculate_summary(self):
        """Tính toán và cập nhật summary"""
        quantity = self.quantity_spin.value()
        leverage = self.leverage_spin.value()

        # Get effective price based on order type
        selected_button = self.order_type_group.checkedButton()
        order_type = selected_button.property("order_type") if selected_button else OrderType.MARKET

        if order_type == OrderType.LIMIT:
            price = self.price_spin.value()
        else:
            price = self.current_price

        # Calculate total
        total = price * quantity
        self.total_label.setText(f"${total:,.2f}")

        # Calculate margin required
        margin = total / leverage
        self.margin_label.setText(f"${margin:,.2f}")

        # Update SL/TP info
        self._calculate_sl_info()
        self._calculate_tp_info()

        # Calculate risk/reward
        self._calculate_risk_reward()

    def _calculate_sl_info(self):
        """Tính toán thông tin SL"""
        if not self.sl_checkbox.isChecked():
            self.sl_info.setText("--")
            return

        entry_price = self.current_price
        sl_price = self.sl_spin.value()
        quantity = self.quantity_spin.value()

        pct = ((sl_price - entry_price) / entry_price) * 100
        amount = (sl_price - entry_price) * quantity

        self.sl_info.setText(f"{pct:+.2f}% (${amount:+,.0f})")
        self.max_loss_label.setText(f"${abs(amount):,.0f} ({abs(pct):.2f}%)")

    def _calculate_tp_info(self):
        """Tính toán thông tin TP"""
        if not self.tp_checkbox.isChecked():
            self.tp_info.setText("--")
            return

        entry_price = self.current_price
        tp_price = self.tp_spin.value()
        quantity = self.quantity_spin.value()

        pct = ((tp_price - entry_price) / entry_price) * 100
        amount = (tp_price - entry_price) * quantity

        self.tp_info.setText(f"{pct:+.2f}% (${amount:+,.0f})")
        self.max_profit_label.setText(f"${abs(amount):,.0f} ({abs(pct):.2f}%)")

    def _calculate_risk_reward(self):
        """Tính toán Risk/Reward ratio"""
        if not self.sl_checkbox.isChecked() or not self.tp_checkbox.isChecked():
            self.rr_label.setText("--")
            return

        entry_price = self.current_price
        sl_price = self.sl_spin.value()
        tp_price = self.tp_spin.value()
        quantity = self.quantity_spin.value()

        risk = abs((sl_price - entry_price) * quantity)
        reward = abs((tp_price - entry_price) * quantity)

        if risk > 0:
            ratio = reward / risk
            self.rr_label.setText(f"1:{ratio:.2f}")
        else:
            self.rr_label.setText("--")

    def _on_submit_order(self, side: str):
        """Handler khi submit order"""
        # Get order type
        selected_button = self.order_type_group.checkedButton()
        order_type = selected_button.property("order_type") if selected_button else OrderType.MARKET

        # Collect data
        order_data = OrderData(
            symbol=self.symbol,
            side=side,
            order_type=order_type,
            quantity=self.quantity_spin.value(),
            price=self.price_spin.value() if order_type == OrderType.LIMIT else None,
            stop_price=self.stop_price_spin.value() if order_type in [OrderType.STOP_LIMIT, OrderType.STOP_MARKET] else None,
            callback_rate=self.callback_spin.value() if order_type == OrderType.TRAILING_STOP else None,
            activation_price=self.activation_spin.value() if order_type == OrderType.TRAILING_STOP and self.activation_spin.value() > 0 else None,
            stop_loss=self.sl_spin.value() if self.sl_checkbox.isChecked() else None,
            take_profit=self.tp_spin.value() if self.tp_checkbox.isChecked() else None,
            leverage=self.leverage_spin.value(),
            margin_mode=MarginMode[self.margin_mode_combo.currentText().upper().replace("-", "_")],
            position_mode=PositionMode[self.position_mode_combo.currentText().upper().replace("-", "_")],
            time_in_force=TimeInForce[self.tif_combo.currentText()] if order_type == OrderType.LIMIT else TimeInForce.GTC,
        )

        # Emit signal
        self.order_submitted.emit(order_data)

        # Close dialog (Non-modal nên dùng close() thay vì accept())
        self.close()

    def set_current_price(self, price: float):
        """Update current price"""
        self.current_price = price
        self.price_spin.setValue(price)
        self._calculate_summary()
