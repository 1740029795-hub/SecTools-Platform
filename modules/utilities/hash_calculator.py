"""
哈希计算器 — 文本和文件的哈希值计算。

支持:
  - 算法: MD5, SHA1, SHA224, SHA256, SHA384, SHA512, SHA3-256, SHA3-512
  - BLAKE2b, BLAKE2s
  - HMAC (自定义密钥)
  - 文件哈希（大文件分块读取）
  - 拖放文件支持
  - 与给定哈希值对比验证
"""

from __future__ import annotations

import hashlib
import hmac
import os
from typing import Any, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.tool_base import BaseTool, ToolCategory, ToolMeta
from core.tool_registry import register_tool

ALGORITHMS = [
    "MD5", "SHA1", "SHA224", "SHA256", "SHA384", "SHA512",
    "SHA3-256", "SHA3-512", "BLAKE2b", "BLAKE2s",
]


class HashToolWidget(QWidget):
    """哈希计算器 UI"""

    execute_requested = pyqtSignal(dict)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ---- 输入模式 ----
        mode_group = QGroupBox("输入")
        mode_group.setStyleSheet(_group_style())
        mode_layout = QVBoxLayout(mode_group)

        # 文本输入
        self._text_input = QTextEdit()
        self._text_input.setPlaceholderText("输入要计算哈希的文本...")
        self._text_input.setMaximumHeight(100)
        self._text_input.setStyleSheet(_input_area_style())
        mode_layout.addWidget(self._text_input)

        # 文件输入
        file_row = QHBoxLayout()
        self._file_input = QLineEdit()
        self._file_input.setPlaceholderText("或选择文件...")
        self._file_input.setReadOnly(True)
        self._file_input.setStyleSheet(_input_style())
        file_row.addWidget(self._file_input)

        browse_btn = QPushButton("📁 浏览")
        browse_btn.setStyleSheet(_btn_secondary_style())
        browse_btn.clicked.connect(self._browse_file)
        file_row.addWidget(browse_btn)
        mode_layout.addLayout(file_row)

        layout.addWidget(mode_group)

        # ---- 算法选择 + HMAC ----
        algo_group = QGroupBox("算法设置")
        algo_group.setStyleSheet(_group_style())
        algo_layout = QGridLayout(algo_group)
        algo_layout.setSpacing(8)

        # 算法多选
        algo_layout.addWidget(QLabel("算法:"), 0, 0)
        self._algo_checks: dict[str, QCheckBox] = {}
        check_layout = QHBoxLayout()
        for algo in ALGORITHMS:
            cb = QCheckBox(algo)
            cb.setChecked(algo in ("MD5", "SHA256"))
            cb.setStyleSheet("color: #cdd6f4; font-size: 11px;")
            self._algo_checks[algo] = cb
            check_layout.addWidget(cb)
        check_layout.addStretch()
        algo_layout.addLayout(check_layout, 0, 1)

        # HMAC 密钥
        algo_layout.addWidget(QLabel("HMAC 密钥:"), 1, 0)
        self._hmac_key = QLineEdit()
        self._hmac_key.setPlaceholderText("留空使用普通哈希，填入密钥则计算 HMAC")
        self._hmac_key.setStyleSheet(_input_style())
        algo_layout.addWidget(self._hmac_key, 1, 1)

        layout.addWidget(algo_group)

        # ---- 验证 ----
        verify_group = QGroupBox("哈希验证")
        verify_group.setStyleSheet(_group_style())
        verify_layout = QHBoxLayout(verify_group)
        verify_layout.addWidget(QLabel("期望值:"))
        self._verify_input = QLineEdit()
        self._verify_input.setPlaceholderText("粘贴期望的哈希值进行对比...")
        self._verify_input.setStyleSheet(_input_style())
        verify_layout.addWidget(self._verify_input, stretch=1)
        layout.addWidget(verify_group)

        # ---- 按钮 ----
        btn_row = QHBoxLayout()
        self._run_btn = QPushButton("🔢 计算哈希")
        self._run_btn.setStyleSheet(_btn_primary_style())
        self._run_btn.clicked.connect(lambda: self.execute_requested.emit(self.get_params()))
        btn_row.addWidget(self._run_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # ---- 结果表格 ----
        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["算法", "哈希值", "验证", "长度"])
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self._table.setStyleSheet(_table_style())
        layout.addWidget(self._table, stretch=1)

    def get_params(self) -> dict:
        selected_algos = [
            a for a, cb in self._algo_checks.items() if cb.isChecked()
        ]
        return {
            "text": self._text_input.toPlainText(),
            "file_path": self._file_input.text().strip(),
            "algorithms": selected_algos,
            "hmac_key": self._hmac_key.text().strip(),
            "expected": self._verify_input.text().strip(),
        }

    def add_result(self, algo: str, hash_val: str, verified: str, length: int) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._table.setItem(row, 0, QTableWidgetItem(algo))
        self._table.setItem(row, 1, QTableWidgetItem(hash_val))

        v_item = QTableWidgetItem(verified)
        if verified == "✓ 匹配":
            v_item.setForeground(Qt.GlobalColor.green)
        elif verified == "✗ 不匹配":
            v_item.setForeground(Qt.GlobalColor.red)
        self._table.setItem(row, 2, v_item)
        self._table.setItem(row, 3, QTableWidgetItem(str(length)))

    def clear_results(self) -> None:
        self._table.setRowCount(0)

    def _browse_file(self) -> None:
        filepath, _ = QFileDialog.getOpenFileName(
            self, "选择文件", "", "所有文件 (*.*)"
        )
        if filepath:
            self._file_input.setText(filepath)


@register_tool
class HashCalculatorTool(BaseTool):
    """哈希计算器"""

    meta = ToolMeta(
        name="hash_calculator",
        display_name="哈希计算器",
        category=ToolCategory.UTILITIES,
        description="MD5/SHA 家族哈希计算，支持文本/文件/HMAC，含哈希验证对比",
        icon="🔢",
        version="1.0.0",
        keywords=["hash", "md5", "sha256", "哈希", "校验", "hmac"],
    )

    def __init__(self) -> None:
        super().__init__()
        self._widget: Optional[HashToolWidget] = None

    def create_widget(self) -> QWidget:
        self._widget = HashToolWidget()
        self._widget.execute_requested.connect(lambda p: self.execute(p))
        return self._widget

    def execute(self, params: dict[str, Any]) -> dict[str, str]:
        text = params.get("text", "")
        file_path = params.get("file_path", "")
        algorithms = params.get("algorithms", ["MD5", "SHA256"])
        hmac_key = params.get("hmac_key", "")
        expected = params.get("expected", "")

        if self._widget:
            self._widget.clear_results()

        # 获取数据（文件优先，否则用文本，包括空字符串）
        if file_path and os.path.isfile(file_path):
            data = self._hash_file(file_path, algorithms, hmac_key)
            source = f"文件: {os.path.basename(file_path)}"
        else:
            data = self._hash_text(text, algorithms, hmac_key)
            source = f"文本 ({len(text)} 字符)"

        self.output_ready.emit(f"计算: {source}")
        results = {}

        for algo, hash_val in data.items():
            length = len(hash_val) * 4  # hex 每字符 4 bit
            verified = ""
            if expected:
                if hash_val.lower() == expected.lower():
                    verified = "✓ 匹配"
                else:
                    verified = "✗ 不匹配"
            else:
                verified = "-"

            if self._widget:
                self._widget.add_result(algo, hash_val, verified, length)
            self.output_ready.emit(f"  {algo}: {hash_val}")
            results[algo] = hash_val

        self.output_ready.emit(f"✓ 完成")
        return results

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        return []

    # ---- 内部 ----

    def _hash_text(
        self, text: str, algorithms: list[str], hmac_key: str
    ) -> dict[str, str]:
        data_bytes = text.encode("utf-8")
        return self._compute_hashes(data_bytes, algorithms, hmac_key)

    def _hash_file(
        self, file_path: str, algorithms: list[str], hmac_key: str
    ) -> dict[str, str]:
        """分块读取大文件"""
        hashers = {}
        for algo in algorithms:
            if hmac_key:
                hashers[algo] = hmac.new(
                    hmac_key.encode(), digestmod=self._get_hashlib(algo)
                )
            else:
                hashers[algo] = self._get_hashlib(algo)()

        file_size = os.path.getsize(file_path)
        bytes_read = 0
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                bytes_read += len(chunk)
                for h in hashers.values():
                    h.update(chunk)

                if file_size > 0 and bytes_read % (file_size // 10 + 1) == 0:
                    pct = int(bytes_read / file_size * 100)
                    self.progress_updated.emit(pct)

        self.progress_updated.emit(100)
        return {algo: h.hexdigest() for algo, h in hashers.items()}

    def _compute_hashes(
        self, data: bytes, algorithms: list[str], hmac_key: str
    ) -> dict[str, str]:
        results = {}
        for algo in algorithms:
            if hmac_key:
                h = hmac.new(hmac_key.encode(), data, self._get_hashlib(algo))
            else:
                h = self._get_hashlib(algo)(data)
            results[algo] = h.hexdigest()
        return results

    @staticmethod
    def _get_hashlib(algo: str):
        algo_lower = algo.lower().replace("-", "")
        if algo_lower.startswith("sha3"):
            return getattr(hashlib, algo_lower)
        elif algo_lower.startswith("blake2"):
            return getattr(hashlib, algo_lower)
        else:
            return getattr(hashlib, algo_lower)


# ---- 样式 ----

def _group_style() -> str:
    return """
        QGroupBox { color: #cdd6f4; font-size: 14px; font-weight: bold;
            border: 1px solid #313244; border-radius: 8px;
            margin-top: 8px; padding-top: 20px; }
        QGroupBox::title { subcontrol-origin: margin; left: 16px; padding: 0 8px; }
    """


def _input_style() -> str:
    return """
        QLineEdit { background-color: #313244; color: #cdd6f4;
            border: 1px solid #45475a; border-radius: 6px;
            padding: 8px 12px; font-size: 13px; }
        QLineEdit:focus { border-color: #89b4fa; }
    """


def _input_area_style() -> str:
    return """
        QTextEdit { background-color: #313244; color: #cdd6f4;
            border: 1px solid #45475a; border-radius: 6px;
            padding: 8px; font-size: 13px; }
        QTextEdit:focus { border-color: #89b4fa; }
    """


def _btn_primary_style() -> str:
    return """
        QPushButton { background-color: #f9e2af; color: #1e1e2e;
            border: none; border-radius: 6px;
            padding: 10px 24px; font-size: 13px; font-weight: bold; }
        QPushButton:hover { background-color: #f5c2e7; }
    """


def _btn_secondary_style() -> str:
    return """
        QPushButton { background-color: #313244; color: #cdd6f4;
            border: 1px solid #45475a; border-radius: 6px;
            padding: 8px 16px; font-size: 12px; }
        QPushButton:hover { background-color: #45475a; }
    """


def _table_style() -> str:
    return """
        QTableWidget { background-color: #11111b; color: #cdd6f4;
            border: 1px solid #313244; border-radius: 6px;
            gridline-color: #313244; font-size: 12px;
            alternate-background-color: #181825; }
        QTableWidget::item:selected { background-color: #45475a; }
        QHeaderView::section { background-color: #1e1e2e; color: #cdd6f4;
            border: 1px solid #313244;
            padding: 6px 8px; font-weight: bold; font-size: 12px; }
    """
