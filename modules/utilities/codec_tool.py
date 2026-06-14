"""
编解码工具 — 链式编码/解码，支持多步组合操作。

支持:
  - Base64 / Base64URL / Base32 / Base16 (Hex)
  - URL 编码 / 解码
  - Unicode 转义 (\\uXXXX) / ASCII 编码
  - ROT13 / ROT47
  - HTML 实体编码
  - 链式操作：支持多步组合，如 Base64→URL→Hex
"""

from __future__ import annotations

import base64
import binascii
import codecs
import html
import re
import urllib.parse
from typing import Any, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.tool_base import BaseTool, ToolCategory, ToolMeta
from core.tool_registry import register_tool

# 编解码操作定义
OPERATIONS = {
    # 编码器
    "Base64 编码": {
        "encode": lambda s: base64.b64encode(s.encode()).decode(),
        "decode": lambda s: base64.b64decode(s.encode()).decode(errors="replace"),
        "category": "Base64",
    },
    "Base64URL 编码": {
        "encode": lambda s: base64.urlsafe_b64encode(s.encode()).decode().rstrip("="),
        "decode": lambda s: base64.urlsafe_b64decode(
            s.encode() + b"=" * (4 - len(s) % 4)
        ).decode(errors="replace"),
        "category": "Base64",
    },
    "Base32 编码": {
        "encode": lambda s: base64.b32encode(s.encode()).decode(),
        "decode": lambda s: base64.b32decode(s.encode()).decode(errors="replace"),
        "category": "Base",
    },
    "Base16 (Hex) 编码": {
        "encode": lambda s: binascii.hexlify(s.encode()).decode(),
        "decode": lambda s: binascii.unhexlify(s.encode()).decode(errors="replace"),
        "category": "Base",
    },
    "URL 编码": {
        "encode": lambda s: urllib.parse.quote(s, safe=""),
        "decode": lambda s: urllib.parse.unquote(s),
        "category": "Web",
    },
    "URL 编码 (全部)": {
        "encode": lambda s: urllib.parse.quote(s, safe=""),
        "decode": lambda s: urllib.parse.unquote(s),
        "category": "Web",
    },
    "Unicode 转义": {
        "encode": lambda s: s.encode("unicode-escape").decode(),
        "decode": lambda s: s.encode().decode("unicode-escape"),
        "category": "文本",
    },
    "ASCII 编码": {
        "encode": lambda s: " ".join(str(ord(c)) for c in s),
        "decode": lambda s: "".join(chr(int(n)) for n in s.split()),
        "category": "文本",
    },
    "ROT13": {
        "encode": lambda s: codecs.encode(s, "rot_13"),
        "decode": lambda s: codecs.encode(s, "rot_13"),
        "category": "古典",
    },
    "ROT47": {
        "encode": lambda s: "".join(
            chr(33 + ((ord(c) - 33 + 47) % 94)) if 33 <= ord(c) <= 126 else c
            for c in s
        ),
        "decode": lambda s: "".join(
            chr(33 + ((ord(c) - 33 + 47) % 94)) if 33 <= ord(c) <= 126 else c
            for c in s
        ),
        "category": "古典",
    },
    "HTML 实体编码": {
        "encode": lambda s: html.escape(s, quote=True),
        "decode": lambda s: html.unescape(s),
        "category": "Web",
    },
    "二进制 (0/1)": {
        "encode": lambda s: " ".join(format(ord(c), "08b") for c in s),
        "decode": lambda s: "".join(chr(int(b, 2)) for b in s.split()),
        "category": "其他",
    },
    "MD5 哈希": {
        "encode": lambda s: __import__("hashlib").md5(s.encode()).hexdigest(),
        "decode": None,
        "category": "哈希",
    },
    "SHA256 哈希": {
        "encode": lambda s: __import__("hashlib").sha256(s.encode()).hexdigest(),
        "decode": None,
        "category": "哈希",
    },
}


class CodecToolWidget(QWidget):
    """编解码工具 UI"""

    execute_requested = pyqtSignal(dict)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._chain: list[tuple[str, str, str]] = []  # [(name, mode, category)]
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ---- 操作选择区 ----
        op_row = QHBoxLayout()

        self._op_combo = QComboBox()
        self._op_combo.setEditable(False)
        for name in OPERATIONS:
            self._op_combo.addItem(name)
        self._op_combo.setStyleSheet(_combo_style())
        op_row.addWidget(QLabel("操作:"))
        op_row.addWidget(self._op_combo, stretch=1)

        self._encode_btn = QPushButton("编码 →")
        self._encode_btn.setStyleSheet(_btn_primary_style())
        self._encode_btn.clicked.connect(lambda: self._add_to_chain("encode"))
        op_row.addWidget(self._encode_btn)

        self._decode_btn = QPushButton("← 解码")
        self._decode_btn.setStyleSheet(_btn_accent_style())
        self._decode_btn.clicked.connect(lambda: self._add_to_chain("decode"))
        op_row.addWidget(self._decode_btn)

        layout.addLayout(op_row)

        # ---- 操作链显示 ----
        chain_row = QHBoxLayout()
        chain_row.addWidget(QLabel("操作链:"))
        self._chain_list = QListWidget()
        self._chain_list.setMaximumHeight(80)
        self._chain_list.setStyleSheet("""
            QListWidget {
                background-color: #313244; color: #cdd6f4;
                border: 1px solid #45475a; border-radius: 6px;
                font-size: 11px;
            }
        """)
        chain_row.addWidget(self._chain_list, stretch=1)

        clear_chain_btn = QPushButton("清空链")
        clear_chain_btn.setStyleSheet(_btn_small_style())
        clear_chain_btn.clicked.connect(self._clear_chain)
        chain_row.addWidget(clear_chain_btn)

        layout.addLayout(chain_row)

        # ---- 输入/输出 ----
        splitter = QSplitter(Qt.Orientation.Vertical)

        # 输入
        input_widget = QWidget()
        il = QVBoxLayout(input_widget)
        il.setContentsMargins(0, 0, 0, 0)
        il.addWidget(QLabel("输入:"))
        self._input_edit = QTextEdit()
        self._input_edit.setPlaceholderText("在此粘贴要编码/解码的文本...")
        self._input_edit.setStyleSheet(_textarea_style())
        il.addWidget(self._input_edit)
        splitter.addWidget(input_widget)

        # 输出
        output_widget = QWidget()
        ol = QVBoxLayout(output_widget)
        ol.setContentsMargins(0, 0, 0, 0)
        ol_hdr = QHBoxLayout()
        ol_hdr.addWidget(QLabel("输出:"))
        ol_hdr.addStretch()
        self._copy_btn = QPushButton("📋 复制")
        self._copy_btn.setStyleSheet(_btn_small_style())
        self._copy_btn.clicked.connect(self._copy_output)
        ol_hdr.addWidget(self._copy_btn)
        ol.addLayout(ol_hdr)

        self._output_edit = QTextEdit()
        self._output_edit.setReadOnly(True)
        self._output_edit.setStyleSheet(_textarea_style())
        ol.addWidget(self._output_edit)
        splitter.addWidget(output_widget)

        splitter.setSizes([250, 250])
        layout.addWidget(splitter, stretch=1)

        # ---- 执行按钮 ----
        exec_row = QHBoxLayout()
        self._run_btn = QPushButton("▶ 执行链式操作")
        self._run_btn.setStyleSheet(_btn_primary_style())
        self._run_btn.clicked.connect(self._execute_chain)
        exec_row.addWidget(self._run_btn)

        self._swap_btn = QPushButton("⇅ 交换输入/输出")
        self._swap_btn.setStyleSheet(_btn_secondary_style())
        self._swap_btn.clicked.connect(self._swap)
        exec_row.addWidget(self._swap_btn)
        exec_row.addStretch()
        layout.addLayout(exec_row)

    def _add_to_chain(self, mode: str) -> None:
        name = self._op_combo.currentText()
        cat = OPERATIONS[name]["category"]
        self._chain.append((name, mode, cat))
        prefix = "→" if mode == "encode" else "←"
        item = QListWidgetItem(f"{prefix} [{cat}] {name}")
        self._chain_list.addItem(item)

    def _clear_chain(self) -> None:
        self._chain.clear()
        self._chain_list.clear()

    def _execute_chain(self) -> None:
        self.execute_requested.emit({
            "text": self._input_edit.toPlainText(),
            "chain": list(self._chain),
        })

    def set_output(self, text: str) -> None:
        self._output_edit.setPlainText(text)

    def _swap(self) -> None:
        tmp = self._input_edit.toPlainText()
        self._input_edit.setPlainText(self._output_edit.toPlainText())
        self._output_edit.setPlainText(tmp)

    def _copy_output(self) -> None:
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(self._output_edit.toPlainText())


@register_tool
class CodecTool(BaseTool):
    """编解码工具"""

    meta = ToolMeta(
        name="codec_tool",
        display_name="编解码工具",
        category=ToolCategory.UTILITIES,
        description="Base64/URL/Hex/Unicode/ROT13/HTML 链式编解码，支持多步组合操作",
        icon="🔐",
        version="1.0.0",
        keywords=["编码", "解码", "base64", "url", "hex", "unicode", "rot13", "html"],
    )

    def __init__(self) -> None:
        super().__init__()
        self._widget: Optional[CodecToolWidget] = None

    def create_widget(self) -> QWidget:
        self._widget = CodecToolWidget()
        self._widget.execute_requested.connect(
            lambda params: self.execute(params)
        )
        return self._widget

    def execute(self, params: dict[str, Any]) -> str:
        text = params.get("text", "")
        chain = params.get("chain", [])

        if not text:
            self.output_ready.emit("[提示] 请输入文本")
            return ""

        if not chain:
            self.output_ready.emit("[提示] 请选择至少一个操作添加到操作链")
            return ""

        result = text
        self.output_ready.emit(f"输入: {text[:50]}... (长度 {len(text)})")

        for name, mode, cat in chain:
            op = OPERATIONS.get(name)
            if not op:
                self.output_ready.emit(f"  [错误] 未知操作: {name}")
                continue

            try:
                if mode == "encode":
                    result = op["encode"](result)
                else:
                    if op["decode"] is None:
                        self.output_ready.emit(f"  [跳过] {name} 不支持解码")
                        continue
                    result = op["decode"](result)

                arrow = "→" if mode == "encode" else "←"
                self.output_ready.emit(
                    f"  {arrow} [{cat}] {name}: {result[:60]}..."
                )
            except Exception as e:
                self.output_ready.emit(f"  [错误] {name}: {e}")

        if self._widget:
            self._widget.set_output(result)

        self.output_ready.emit(f"✓ 完成，输出长度: {len(result)}")
        return result

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        return []


# ---- 样式 ----

def _combo_style() -> str:
    return """
        QComboBox {
            background-color: #313244; color: #cdd6f4;
            border: 1px solid #45475a; border-radius: 6px;
            padding: 8px 12px; font-size: 13px;
        }
        QComboBox QAbstractItemView {
            background-color: #1e1e2e; color: #cdd6f4;
            selection-background-color: #45475a;
        }
    """


def _btn_primary_style() -> str:
    return """
        QPushButton {
            background-color: #89b4fa; color: #1e1e2e;
            border: none; border-radius: 6px;
            padding: 8px 16px; font-size: 12px; font-weight: bold;
        }
        QPushButton:hover { background-color: #74c7ec; }
    """


def _btn_accent_style() -> str:
    return """
        QPushButton {
            background-color: #f9e2af; color: #1e1e2e;
            border: none; border-radius: 6px;
            padding: 8px 16px; font-size: 12px; font-weight: bold;
        }
        QPushButton:hover { background-color: #f5c2e7; }
    """


def _btn_secondary_style() -> str:
    return """
        QPushButton {
            background-color: #313244; color: #cdd6f4;
            border: 1px solid #45475a; border-radius: 6px;
            padding: 8px 16px; font-size: 12px;
        }
        QPushButton:hover { background-color: #45475a; }
    """


def _btn_small_style() -> str:
    return """
        QPushButton {
            background-color: #45475a; color: #cdd6f4;
            border: none; border-radius: 4px;
            padding: 4px 10px; font-size: 11px;
        }
        QPushButton:hover { background-color: #585b70; }
    """


def _textarea_style() -> str:
    return """
        QTextEdit {
            background-color: #11111b; color: #cdd6f4;
            border: 1px solid #313244; border-radius: 6px;
            padding: 10px;
            font-family: "Consolas", "Microsoft YaHei Mono", monospace;
            font-size: 13px;
        }
        QTextEdit:focus { border-color: #89b4fa; }
    """
