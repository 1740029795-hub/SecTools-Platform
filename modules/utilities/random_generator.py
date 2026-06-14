"""
随机生成器 — 生成各类安全相关的随机值。

支持:
  - UUID (v1/v4)
  - 安全密码（自定义长度/复杂度）
  - API Key / Token
  - 随机字符串（字母/数字/符号）
  - 随机 IP / MAC 地址
  - 批量生成
"""

from __future__ import annotations

import hashlib
import os
import random
import secrets
import string
import uuid
from typing import Any, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.tool_base import BaseTool, ToolCategory, ToolMeta
from core.tool_registry import register_tool


class RandomGenWidget(QWidget):
    """随机生成器 UI"""

    execute_requested = pyqtSignal(dict)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ---- 生成类型 ----
        type_group = QGroupBox("生成类型")
        type_group.setStyleSheet(_group_style())
        type_layout = QGridLayout(type_group)
        type_layout.setSpacing(8)

        type_layout.addWidget(QLabel("类型:"), 0, 0)
        self._type_combo = QComboBox()
        self._type_combo.addItems([
            "UUID v4", "UUID v1",
            "安全密码", "API Key", "Token (Hex)",
            "随机字符串", "随机数字",
            "随机 IP 地址", "随机 MAC 地址",
            "Nano ID", "XKCD 风格密码",
        ])
        self._type_combo.setStyleSheet(_combo_style())
        self._type_combo.currentIndexChanged.connect(self._on_type_changed)
        type_layout.addWidget(self._type_combo, 0, 1)

        # 长度
        type_layout.addWidget(QLabel("长度:"), 1, 0)
        self._length_spin = QSpinBox()
        self._length_spin.setRange(4, 256)
        self._length_spin.setValue(32)
        self._length_spin.setStyleSheet(_spin_style())
        type_layout.addWidget(self._length_spin, 1, 1)

        # 数量
        type_layout.addWidget(QLabel("数量:"), 2, 0)
        self._count_spin = QSpinBox()
        self._count_spin.setRange(1, 100)
        self._count_spin.setValue(5)
        self._count_spin.setStyleSheet(_spin_style())
        type_layout.addWidget(self._count_spin, 2, 1)

        layout.addWidget(type_group)

        # ---- 密码选项 ----
        self._pwd_group = QGroupBox("密码选项")
        self._pwd_group.setStyleSheet(_group_style())
        pwd_layout = QGridLayout(self._pwd_group)
        pwd_layout.setSpacing(8)

        self._upper_cb = QCheckBox("大写字母 (A-Z)")
        self._upper_cb.setChecked(True)
        self._upper_cb.setStyleSheet(_cb_style())
        pwd_layout.addWidget(self._upper_cb, 0, 0)

        self._lower_cb = QCheckBox("小写字母 (a-z)")
        self._lower_cb.setChecked(True)
        self._lower_cb.setStyleSheet(_cb_style())
        pwd_layout.addWidget(self._lower_cb, 0, 1)

        self._digits_cb = QCheckBox("数字 (0-9)")
        self._digits_cb.setChecked(True)
        self._digits_cb.setStyleSheet(_cb_style())
        pwd_layout.addWidget(self._digits_cb, 1, 0)

        self._symbols_cb = QCheckBox("符号 (!@#$...)")
        self._symbols_cb.setChecked(True)
        self._symbols_cb.setStyleSheet(_cb_style())
        pwd_layout.addWidget(self._symbols_cb, 1, 1)

        self._no_ambig_cb = QCheckBox("排除易混淆字符 (0OIl1)")
        self._no_ambig_cb.setStyleSheet(_cb_style())
        pwd_layout.addWidget(self._no_ambig_cb, 2, 0)

        layout.addWidget(self._pwd_group)

        # ---- 按钮 ----
        btn_row = QHBoxLayout()
        self._gen_btn = QPushButton("🎲 生成")
        self._gen_btn.setStyleSheet(_btn_primary_style())
        self._gen_btn.clicked.connect(lambda: self.execute_requested.emit(self.get_params()))
        btn_row.addWidget(self._gen_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # ---- 输出 ----
        output_group = QGroupBox("生成结果")
        output_group.setStyleSheet(_group_style())
        ol = QVBoxLayout(output_group)
        self._output_edit = QTextEdit()
        self._output_edit.setReadOnly(True)
        self._output_edit.setStyleSheet(_output_style())
        ol.addWidget(self._output_edit)
        layout.addWidget(output_group, stretch=1)

    def get_params(self) -> dict:
        return {
            "type": self._type_combo.currentText(),
            "length": self._length_spin.value(),
            "count": self._count_spin.value(),
            "upper": self._upper_cb.isChecked(),
            "lower": self._lower_cb.isChecked(),
            "digits": self._digits_cb.isChecked(),
            "symbols": self._symbols_cb.isChecked(),
            "no_ambiguous": self._no_ambig_cb.isChecked(),
        }

    def set_output(self, text: str) -> None:
        self._output_edit.setPlainText(text)

    def append_output(self, text: str) -> None:
        self._output_edit.append(text)

    def _on_type_changed(self, idx: int) -> None:
        t = self._type_combo.currentText()
        show_pwd = t in ("安全密码", "随机字符串", "API Key", "Nano ID", "XKCD 风格密码")
        self._pwd_group.setVisible(show_pwd)
        if t in ("UUID v4", "UUID v1"):
            self._length_spin.setValue(36)
        elif t == "Nano ID":
            self._length_spin.setValue(21)
        elif t == "XKCD 风格密码":
            self._length_spin.setValue(4)


@register_tool
class RandomGeneratorTool(BaseTool):
    """随机生成器"""

    meta = ToolMeta(
        name="random_generator",
        display_name="随机生成器",
        category=ToolCategory.UTILITIES,
        description="生成 UUID/安全密码/API Key/Token/随机 IP 和 MAC",
        icon="🎲",
        version="1.0.0",
        keywords=["随机", "UUID", "密码", "token", "生成", "random", "password"],
    )

    # XKCD 风格单词列表
    XKCD_WORDS = [
        "correct", "horse", "battery", "staple", "apple", "bridge", "castle",
        "dragon", "eagle", "forest", "garden", "harbor", "island", "jungle",
        "knight", "lemon", "mountain", "north", "ocean", "panda", "queen",
        "river", "silver", "tiger", "umbrella", "village", "whale", "zenith",
        "anchor", "blaze", "cloud", "diamond", "ember", "flame", "glacier",
        "horizon", "ivory", "jade", "kiwi", "lotus", "mango", "nova",
    ]

    def __init__(self) -> None:
        super().__init__()
        self._widget: Optional[RandomGenWidget] = None

    def create_widget(self) -> QWidget:
        self._widget = RandomGenWidget()
        self._widget.execute_requested.connect(lambda p: self.execute(p))
        return self._widget

    def execute(self, params: dict[str, Any]) -> list[str]:
        gen_type = params["type"]
        length = params.get("length", 32)
        count = params.get("count", 5)

        results: list[str] = []

        self.output_ready.emit(f"生成 {count} 个 [{gen_type}] ...")

        for i in range(count):
            value = self._generate_one(gen_type, length, params)
            results.append(value)

        if self._widget:
            self._widget.set_output("\n".join(results))

        self.output_ready.emit(f"✓ 已生成 {count} 个值")
        return results

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        return []

    # ---- 生成逻辑 ----

    def _generate_one(self, gen_type: str, length: int, params: dict) -> str:
        if gen_type == "UUID v4":
            return str(uuid.uuid4())
        elif gen_type == "UUID v1":
            return str(uuid.uuid1())
        elif gen_type == "安全密码":
            return self._gen_password(length, params)
        elif gen_type == "API Key":
            return "sk-" + secrets.token_hex(length // 2)
        elif gen_type == "Token (Hex)":
            return secrets.token_hex(length // 2)
        elif gen_type == "随机字符串":
            return self._gen_random_string(length, params)
        elif gen_type == "随机数字":
            return "".join(secrets.choice(string.digits) for _ in range(length))
        elif gen_type == "随机 IP 地址":
            return ".".join(str(random.randint(0, 255)) for _ in range(4))
        elif gen_type == "随机 MAC 地址":
            return ":".join(
                f"{random.randint(0, 255):02x}" for _ in range(6)
            ).upper()
        elif gen_type == "Nano ID":
            return self._gen_nanoid(length)
        elif gen_type == "XKCD 风格密码":
            return self._gen_xkcd(length)
        return ""

    def _gen_password(self, length: int, params: dict) -> str:
        """生成安全密码"""
        charset = ""
        if params.get("upper", True):
            charset += string.ascii_uppercase
        if params.get("lower", True):
            charset += string.ascii_lowercase
        if params.get("digits", True):
            charset += string.digits
        if params.get("symbols", True):
            charset += "!@#$%^&*()-_=+[]{}|;:,.<>?/"

        if params.get("no_ambiguous", False):
            charset = charset.translate(
                str.maketrans("", "", "0OoIl1")
            )

        if not charset:
            charset = string.ascii_letters + string.digits

        # 确保每种类型至少一个字符
        password = []
        if params.get("upper"):
            password.append(secrets.choice(string.ascii_uppercase))
        if params.get("lower"):
            password.append(secrets.choice(string.ascii_lowercase))
        if params.get("digits"):
            password.append(secrets.choice(string.digits))
        if params.get("symbols"):
            password.append(secrets.choice("!@#$%^&*()-_=+"))

        remaining = length - len(password)
        password.extend(secrets.choice(charset) for _ in range(remaining))
        secrets.SystemRandom().shuffle(password)
        return "".join(password)

    def _gen_random_string(self, length: int, params: dict) -> str:
        charset = ""
        if params.get("upper", True):
            charset += string.ascii_uppercase
        if params.get("lower", True):
            charset += string.ascii_lowercase
        if params.get("digits", True):
            charset += string.digits
        if params.get("symbols", False):
            charset += "!@#$%^&*"
        if not charset:
            charset = string.ascii_letters + string.digits
        return "".join(secrets.choice(charset) for _ in range(length))

    def _gen_nanoid(self, size: int = 21) -> str:
        alphabet = string.ascii_letters + string.digits + "_-"
        return "".join(secrets.choice(alphabet) for _ in range(size))

    def _gen_xkcd(self, word_count: int = 4) -> str:
        words = [secrets.choice(self.XKCD_WORDS) for _ in range(word_count)]
        return "-".join(words)


# ---- 样式 ----

def _group_style() -> str:
    return """
        QGroupBox { color: #cdd6f4; font-size: 14px; font-weight: bold;
            border: 1px solid #313244; border-radius: 8px;
            margin-top: 8px; padding-top: 20px; }
        QGroupBox::title { subcontrol-origin: margin; left: 16px; padding: 0 8px; }
    """


def _combo_style() -> str:
    return """
        QComboBox { background-color: #313244; color: #cdd6f4;
            border: 1px solid #45475a; border-radius: 6px;
            padding: 8px 12px; font-size: 13px; }
        QComboBox QAbstractItemView { background-color: #1e1e2e; color: #cdd6f4;
            selection-background-color: #45475a; }
    """


def _spin_style() -> str:
    return """
        QSpinBox { background-color: #313244; color: #cdd6f4;
            border: 1px solid #45475a; border-radius: 6px;
            padding: 8px 12px; font-size: 13px; }
    """


def _cb_style() -> str:
    return "QCheckBox { color: #cdd6f4; font-size: 12px; spacing: 6px; }"


def _btn_primary_style() -> str:
    return """
        QPushButton { background-color: #a6e3a1; color: #1e1e2e;
            border: none; border-radius: 6px;
            padding: 10px 24px; font-size: 13px; font-weight: bold; }
        QPushButton:hover { background-color: #94e2d5; }
    """


def _output_style() -> str:
    return """
        QTextEdit { background-color: #11111b; color: #cdd6f4;
            border: 1px solid #313244; border-radius: 6px;
            padding: 10px;
            font-family: Consolas, monospace; font-size: 13px; }
    """
