"""
设置对话框 — 配置外部工具路径、代理、主题等。
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from config.app_config import app_config


class SettingsDialog(QDialog):
    """设置对话框"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("⚙️ 设置")
        self.resize(550, 500)
        self.setStyleSheet(_dialog_style())
        self._init_ui()
        self._load_values()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        tabs = QTabWidget()
        tabs.setStyleSheet(_tab_style())

        # ---- 外部工具 ----
        tools_tab = QWidget()
        tools_form = QFormLayout(tools_tab)
        tools_form.setSpacing(10)

        self._tool_paths: dict[str, QLineEdit] = {}
        for tool_id, label in [
            ("nmap", "Nmap 路径"),
            ("sqlmap", "SQLMap 路径"),
            ("dirb", "Dirb 路径"),
            ("nikto", "Nikto 路径"),
            ("python_path", "Python 路径"),
        ]:
            row = QHBoxLayout()
            edit = QLineEdit()
            edit.setStyleSheet(_input_style())
            edit.setPlaceholderText(f"输入 {label} 或使用环境变量默认值")
            row.addWidget(edit)

            browse_btn = QPushButton("📁")
            browse_btn.setFixedWidth(40)
            browse_btn.setStyleSheet(_btn_small_style())
            browse_btn.clicked.connect(
                lambda checked, e=edit: self._browse_file(e)
            )
            row.addWidget(browse_btn)

            tools_form.addRow(QLabel(f"{label}:"), row)
            self._tool_paths[tool_id] = edit

        tabs.addTab(tools_tab, "外部工具")

        # ---- 代理 ----
        proxy_tab = QWidget()
        proxy_form = QFormLayout(proxy_tab)
        proxy_form.setSpacing(10)

        self._proxy_enabled = QCheckBox("启用代理")
        self._proxy_enabled.setStyleSheet("color: #cdd6f4;")
        proxy_form.addRow("", self._proxy_enabled)

        self._proxy_http = QLineEdit()
        self._proxy_http.setPlaceholderText("http://127.0.0.1:8080")
        self._proxy_http.setStyleSheet(_input_style())
        proxy_form.addRow(QLabel("HTTP 代理:"), self._proxy_http)

        self._proxy_https = QLineEdit()
        self._proxy_https.setPlaceholderText("https://127.0.0.1:8080")
        self._proxy_https.setStyleSheet(_input_style())
        proxy_form.addRow(QLabel("HTTPS 代理:"), self._proxy_https)

        tabs.addTab(proxy_tab, "代理")

        # ---- 通用 ----
        general_tab = QWidget()
        general_form = QFormLayout(general_tab)
        general_form.setSpacing(10)

        self._theme_combo = QComboBox()
        self._theme_combo.addItems(["dark", "light"])
        self._theme_combo.setStyleSheet(_combo_style())
        general_form.addRow(QLabel("主题:"), self._theme_combo)

        self._thread_spin = QSpinBox()
        self._thread_spin.setRange(1, 200)
        self._thread_spin.setValue(10)
        self._thread_spin.setStyleSheet(_spin_style())
        general_form.addRow(QLabel("默认线程数:"), self._thread_spin)

        self._timeout_spin = QSpinBox()
        self._timeout_spin.setRange(1, 120)
        self._timeout_spin.setValue(30)
        self._timeout_spin.setStyleSheet(_spin_style())
        general_form.addRow(QLabel("默认超时(s):"), self._timeout_spin)

        self._ssl_verify = QCheckBox("验证 SSL 证书")
        self._ssl_verify.setChecked(False)
        self._ssl_verify.setStyleSheet("color: #cdd6f4;")
        general_form.addRow("", self._ssl_verify)

        tabs.addTab(general_tab, "通用")

        layout.addWidget(tabs)

        # ---- 按钮 ----
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Apply
        )
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(
            self._on_apply
        )
        buttons.setStyleSheet("""
            QPushButton { padding: 8px 20px; border-radius: 6px; font-size: 13px; }
        """)
        layout.addWidget(buttons)

    def _load_values(self) -> None:
        """加载当前配置到 UI"""
        for tool_id, edit in self._tool_paths.items():
            edit.setText(app_config.get(f"external_tools.{tool_id}", ""))

        self._proxy_enabled.setChecked(app_config.get("proxy.enabled", False))
        self._proxy_http.setText(app_config.get("proxy.http", ""))
        self._proxy_https.setText(app_config.get("proxy.https", ""))

        self._theme_combo.setCurrentText(app_config.get("theme", "dark"))
        self._thread_spin.setValue(app_config.get("max_threads", 10))
        self._timeout_spin.setValue(app_config.get("timeout", 30))
        self._ssl_verify.setChecked(app_config.get("verify_ssl", False))

    def _save_values(self) -> None:
        """保存 UI 值到配置"""
        for tool_id, edit in self._tool_paths.items():
            app_config.set(f"external_tools.{tool_id}", edit.text().strip())

        app_config.set("proxy.enabled", self._proxy_enabled.isChecked())
        app_config.set("proxy.http", self._proxy_http.text().strip())
        app_config.set("proxy.https", self._proxy_https.text().strip())

        app_config.set("theme", self._theme_combo.currentText())
        app_config.set("max_threads", self._thread_spin.value())
        app_config.set("timeout", self._timeout_spin.value())
        app_config.set("verify_ssl", self._ssl_verify.isChecked())

        app_config.save()

    def _on_ok(self) -> None:
        self._save_values()
        self.accept()

    def _on_apply(self) -> None:
        self._save_values()

    def _browse_file(self, edit: QLineEdit) -> None:
        filepath, _ = QFileDialog.getOpenFileName(
            self, "选择可执行文件", "", "可执行文件 (*.exe);;所有文件 (*)"
        )
        if filepath:
            edit.setText(filepath)


# ---- 样式 ----

def _dialog_style() -> str:
    return "QDialog { background-color: #1e1e2e; color: #cdd6f4; }"


def _tab_style() -> str:
    return """
        QTabWidget::pane { border: 1px solid #313244; background-color: #1e1e2e; }
        QTabBar::tab { background-color: #181825; color: #a6adc8;
            padding: 8px 20px; font-size: 13px; }
        QTabBar::tab:selected { background-color: #1e1e2e; color: #cdd6f4; }
    """


def _input_style() -> str:
    return """
        QLineEdit { background-color: #313244; color: #cdd6f4;
            border: 1px solid #45475a; border-radius: 6px;
            padding: 8px 12px; font-size: 13px; }
        QLineEdit:focus { border-color: #89b4fa; }
    """


def _combo_style() -> str:
    return """
        QComboBox { background-color: #313244; color: #cdd6f4;
            border: 1px solid #45475a; border-radius: 6px;
            padding: 8px 12px; font-size: 13px; }
    """


def _spin_style() -> str:
    return """
        QSpinBox { background-color: #313244; color: #cdd6f4;
            border: 1px solid #45475a; border-radius: 6px;
            padding: 8px 12px; font-size: 13px; }
    """


def _btn_small_style() -> str:
    return """
        QPushButton { background-color: #45475a; color: #cdd6f4;
            border: none; border-radius: 4px; padding: 4px 8px; }
        QPushButton:hover { background-color: #585b70; }
    """
