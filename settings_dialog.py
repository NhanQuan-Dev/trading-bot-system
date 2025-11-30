# settings_dialog.py

from dataclasses import dataclass

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QTabWidget,
    QWidget,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QPushButton,
    QHBoxLayout,
    QDialogButtonBox,
    QMessageBox,
    QLabel,
    QSpinBox,
)


@dataclass
class ApiSettings:
    environment: str = "Testnet"  # "Testnet" hoặc "Production"
    api_key: str = ""
    api_secret: str = ""


@dataclass
class DbSettings:
    host: str = "localhost"
    port: int = 5432
    database: str = ""
    user: str = ""
    password: str = ""


class SettingsDialog(QDialog):
    """
    Dialog cấu hình API & Database.

    - Tab 1: API (Binance, v.v.)
    - Tab 2: Database (Postgres)

    Có 2 signal:
    - api_connection_tested(bool success, str environment)
    - db_connection_tested(bool success)
    """

    api_connection_tested = pyqtSignal(bool, str)
    db_connection_tested = pyqtSignal(bool)

    def __init__(
        self,
        parent=None,
        api_settings: ApiSettings | None = None,
        db_settings: DbSettings | None = None,
    ):
        super().__init__(parent)

        self.setWindowTitle("Settings - API & Database")
        self.resize(500, 350)

        self._api_settings = api_settings or ApiSettings()
        self._db_settings = db_settings or DbSettings()

        self._init_ui()

    # ------------------------------------------------------------------ UI
    def _init_ui(self):
        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # --- Tab API ---
        self.api_tab = QWidget()
        self._init_api_tab()
        self.tabs.addTab(self.api_tab, "API")

        # --- Tab DB ---
        self.db_tab = QWidget()
        self._init_db_tab()
        self.tabs.addTab(self.db_tab, "Database")

        # --- Buttons Save / Cancel ---
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_save_clicked)
        button_box.rejected.connect(self.reject)

        layout.addWidget(button_box)

    def _init_api_tab(self):
        layout = QVBoxLayout(self.api_tab)
        form = QFormLayout()

        # Environment
        self.env_combo = QComboBox()
        self.env_combo.addItems(["Testnet", "Production"])
        self.env_combo.setCurrentText(self._api_settings.environment)
        form.addRow("Environment:", self.env_combo)

        # API Key
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setText(self._api_settings.api_key)
        form.addRow("API Key:", self.api_key_edit)

        # API Secret
        self.api_secret_edit = QLineEdit()
        self.api_secret_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_secret_edit.setText(self._api_settings.api_secret)
        form.addRow("API Secret:", self.api_secret_edit)

        layout.addLayout(form)

        # Test button + status label
        btn_layout = QHBoxLayout()
        self.api_test_button = QPushButton("Test Connection")
        self.api_test_button.clicked.connect(self._on_test_api_clicked)

        self.api_status_label = QLabel("Status: Not tested")
        self.api_status_label.setStyleSheet("color: gray;")

        btn_layout.addWidget(self.api_test_button)
        btn_layout.addWidget(self.api_status_label)

        layout.addLayout(btn_layout)

    def _init_db_tab(self):
        layout = QVBoxLayout(self.db_tab)
        form = QFormLayout()

        # Host
        self.db_host_edit = QLineEdit()
        self.db_host_edit.setText(self._db_settings.host)
        form.addRow("Host:", self.db_host_edit)

        # Port
        self.db_port_spin = QSpinBox()
        self.db_port_spin.setRange(1, 65535)
        self.db_port_spin.setValue(self._db_settings.port)
        form.addRow("Port:", self.db_port_spin)

        # Database
        self.db_name_edit = QLineEdit()
        self.db_name_edit.setText(self._db_settings.database)
        form.addRow("Database:", self.db_name_edit)

        # User
        self.db_user_edit = QLineEdit()
        self.db_user_edit.setText(self._db_settings.user)
        form.addRow("User:", self.db_user_edit)

        # Password
        self.db_password_edit = QLineEdit()
        self.db_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.db_password_edit.setText(self._db_settings.password)
        form.addRow("Password:", self.db_password_edit)

        layout.addLayout(form)

        # Test button + status label
        btn_layout = QHBoxLayout()
        self.db_test_button = QPushButton("Test Connection")
        self.db_test_button.clicked.connect(self._on_test_db_clicked)

        self.db_status_label = QLabel("Status: Not tested")
        self.db_status_label.setStyleSheet("color: gray;")

        btn_layout.addWidget(self.db_test_button)
        btn_layout.addWidget(self.db_status_label)

        layout.addLayout(btn_layout)

    # ------------------------------------------------------------------ Actions

    def _on_test_api_clicked(self):
        """
        Tạm thời: chỉ check field không rỗng.
        Sau này bạn thay bằng logic thật: gọi Binance API / ping server.
        """
        api_key = self.api_key_edit.text().strip()
        api_secret = self.api_secret_edit.text().strip()
        env = self.env_combo.currentText()

        if not api_key or not api_secret:
            QMessageBox.warning(
                self,
                "API Test",
                "API Key hoặc Secret đang trống.\nĐiền đủ thông tin rồi thử lại.",
            )
            self.api_status_label.setText("Status: Missing credentials")
            self.api_status_label.setStyleSheet("color: orange;")
            self.api_connection_tested.emit(False, env)
            return

        # Giả lập success
        QMessageBox.information(
            self,
            "API Test",
            f"Test kết nối API ({env}) giả lập thành công.\nSau này thay bằng real ping.",
        )
        self.api_status_label.setText(f"Status: Connected ({env})")
        self.api_status_label.setStyleSheet("color: green;")
        self.api_connection_tested.emit(True, env)

    def _on_test_db_clicked(self):
        """
        Tạm thời: chỉ check host + database không rỗng.
        Sau này bạn thay bằng logic thật: psycopg2 / asyncpg connect thử.
        """
        host = self.db_host_edit.text().strip()
        db_name = self.db_name_edit.text().strip()

        if not host or not db_name:
            QMessageBox.warning(
                self,
                "DB Test",
                "Host hoặc Database đang trống.\nĐiền đủ thông tin rồi thử lại.",
            )
            self.db_status_label.setText("Status: Missing config")
            self.db_status_label.setStyleSheet("color: orange;")
            self.db_connection_tested.emit(False)
            return

        # Giả lập success
        QMessageBox.information(
            self,
            "DB Test",
            "Test kết nối Database giả lập thành công.\nSau này thay bằng real connect.",
        )
        self.db_status_label.setText("Status: Connected")
        self.db_status_label.setStyleSheet("color: green;")
        self.db_connection_tested.emit(True)

    def _on_save_clicked(self):
        """
        Lưu vào dataclass trong dialog.
        (Sau này MainWindow có thể đọc ra và ghi file/QSettings.)
        """
        self._api_settings = ApiSettings(
            environment=self.env_combo.currentText(),
            api_key=self.api_key_edit.text().strip(),
            api_secret=self.api_secret_edit.text().strip(),
        )

        self._db_settings = DbSettings(
            host=self.db_host_edit.text().strip(),
            port=int(self.db_port_spin.value()),
            database=self.db_name_edit.text().strip(),
            user=self.db_user_edit.text().strip(),
            password=self.db_password_edit.text().strip(),
        )

        self.accept()

    # ------------------------------------------------------------------ Public getters

    def get_api_settings(self) -> ApiSettings:
        return self._api_settings

    def get_db_settings(self) -> DbSettings:
        return self._db_settings
