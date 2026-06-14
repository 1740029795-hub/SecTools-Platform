"""
差异对比工具 — HTTP 响应 / 文本差异高亮对比。

特性:
  - 双栏并排对比
  - HTML 格式差异渲染（红色删除 / 绿色新增）
  - HTTP 响应快速对比（请求同一 URL 不同参数）
  - 行内差异高亮
  - 差异统计
"""

from __future__ import annotations

import difflib
from typing import Any, Optional

import requests

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.tool_base import BaseTool, ToolCategory, ToolMeta
from core.tool_registry import register_tool


class DiffToolWidget(QWidget):
    """差异对比 UI"""

    execute_requested = pyqtSignal(dict)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ---- HTTP 快速对比 ----
        http_group = QGroupBox("HTTP 快速对比")
        http_group.setStyleSheet(_group_style())
        hl = QHBoxLayout(http_group)
        hl.addWidget(QLabel("URL:"))
        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("https://example.com")
        self._url_input.setStyleSheet(_input_style())
        hl.addWidget(self._url_input, stretch=1)
        self._http_btn = QPushButton("发送 (GET/POST)")
        self._http_btn.setStyleSheet(_btn_accent_style())
        self._http_btn.clicked.connect(self._do_http_compare)
        hl.addWidget(self._http_btn)
        layout.addWidget(http_group)

        # ---- 双栏对比区 ----
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧 (A)
        left_widget = QWidget()
        ll = QVBoxLayout(left_widget)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.addWidget(QLabel("🔴 原始 (A):"))
        self._left_edit = QTextEdit()
        self._left_edit.setPlaceholderText("粘贴原始文本 / HTTP 响应...")
        self._left_edit.setStyleSheet(_textarea_style())
        ll.addWidget(self._left_edit)
        splitter.addWidget(left_widget)

        # 右侧 (B)
        right_widget = QWidget()
        rl = QVBoxLayout(right_widget)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.addWidget(QLabel("🟢 对比 (B):"))
        self._right_edit = QTextEdit()
        self._right_edit.setPlaceholderText("粘贴对比文本 / HTTP 响应...")
        self._right_edit.setStyleSheet(_textarea_style())
        rl.addWidget(self._right_edit)
        splitter.addWidget(right_widget)

        layout.addWidget(splitter, stretch=2)

        # ---- 按钮 ----
        btn_row = QHBoxLayout()
        self._diff_btn = QPushButton("🔍 对比差异")
        self._diff_btn.setStyleSheet(_btn_primary_style())
        self._diff_btn.clicked.connect(lambda: self.execute_requested.emit({
            "text_a": self._left_edit.toPlainText(),
            "text_b": self._right_edit.toPlainText(),
        }))
        btn_row.addWidget(self._diff_btn)

        self._clear_btn = QPushButton("清空")
        self._clear_btn.setStyleSheet(_btn_secondary_style())
        self._clear_btn.clicked.connect(self._clear)
        btn_row.addWidget(self._clear_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # ---- 差异结果（HTML 渲染） ----
        result_group = QGroupBox("差异结果")
        result_group.setStyleSheet(_group_style())
        rl2 = QVBoxLayout(result_group)
        self._diff_output = QTextEdit()
        self._diff_output.setReadOnly(True)
        self._diff_output.setStyleSheet(_textarea_style())
        rl2.addWidget(self._diff_output)

        # 统计
        self._stat_label = QLabel("")
        self._stat_label.setStyleSheet("color: #a6adc8; font-size: 12px; padding: 4px;")
        rl2.addWidget(self._stat_label)

        layout.addWidget(result_group, stretch=1)

    def set_diff_html(self, html: str) -> None:
        self._diff_output.setHtml(html)

    def set_diff_text(self, text: str) -> None:
        self._diff_output.setPlainText(text)

    def set_stat(self, text: str) -> None:
        self._stat_label.setText(text)

    def _clear(self) -> None:
        self._left_edit.clear()
        self._right_edit.clear()
        self._diff_output.clear()

    def _do_http_compare(self) -> None:
        self.execute_requested.emit({
            "text_a": self._left_edit.toPlainText(),
            "text_b": self._right_edit.toPlainText(),
            "http_url": self._url_input.text().strip(),
        })


@register_tool
class DiffTool(BaseTool):
    """差异对比工具"""

    meta = ToolMeta(
        name="diff_tool",
        display_name="差异对比",
        category=ToolCategory.UTILITIES,
        description="文本 / HTTP 响应差异高亮对比，支持行内差异高亮和统计",
        icon="📊",
        version="1.0.0",
        keywords=["diff", "对比", "差异", "比较", "http", "响应"],
    )

    def __init__(self) -> None:
        super().__init__()
        self._widget: Optional[DiffToolWidget] = None

    def create_widget(self) -> QWidget:
        self._widget = DiffToolWidget()
        self._widget.execute_requested.connect(lambda p: self.execute(p))
        return self._widget

    def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        text_a = params.get("text_a", "")
        text_b = params.get("text_b", "")
        http_url = params.get("http_url", "")

        # HTTP 对比模式
        if http_url and not text_a and not text_b:
            try:
                text_a, text_b = self._http_compare(http_url)
                if self._widget:
                    self._widget._left_edit.setPlainText(text_a)
                    self._widget._right_edit.setPlainText(text_b)
            except Exception as e:
                self.output_ready.emit(f"[错误] HTTP 请求失败: {e}")
                return {}

        if not text_a and not text_b:
            self.output_ready.emit("[提示] 请输入要对比的文本")
            return {}

        # 计算差异
        self.output_ready.emit(f"对比: A ({len(text_a)} 字符) vs B ({len(text_b)} 字符)")

        lines_a = text_a.splitlines(keepends=True)
        lines_b = text_b.splitlines(keepends=True)

        diff = list(difflib.unified_diff(
            lines_a, lines_b,
            fromfile="原始 (A)", tofile="对比 (B)",
            lineterm="",
        ))

        if not diff:
            self.output_ready.emit("✓ 两段文本完全相同")
            if self._widget:
                self._widget.set_diff_text("✅ 两段文本完全相同，无差异。")
                self._widget.set_stat("完全相同")
            return {"identical": True, "diff": []}

        # 生成 HTML 高亮
        html = self._generate_diff_html(lines_a, lines_b)
        if self._widget:
            self._widget.set_diff_html(html)

        # 统计
        added = sum(1 for d in diff if d.startswith("+") and not d.startswith("+++"))
        removed = sum(1 for d in diff if d.startswith("-") and not d.startswith("---"))
        stat = f"差异: +{added} 行新增, -{removed} 行删除, {len(diff)} 行变化"
        self.output_ready.emit(stat)
        if self._widget:
            self._widget.set_stat(stat)

        return {
            "identical": False,
            "added": added,
            "removed": removed,
            "diff": diff,
        }

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        return []

    # ---- 内部 ----

    def _http_compare(self, url: str) -> tuple[str, str]:
        """发送 GET 和 POST 请求对比"""
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        self.output_ready.emit(f"发送 GET 请求: {url}")
        resp_get = requests.get(url, timeout=15, headers={
            "User-Agent": "SecTools-Platform/1.0"
        })
        text_a = f"HTTP {resp_get.status_code}\n"
        for k, v in resp_get.headers.items():
            text_a += f"{k}: {v}\n"
        text_a += f"\n{resp_get.text[:5000]}"

        self.output_ready.emit(f"发送 POST 请求: {url}")
        resp_post = requests.post(url, timeout=15, headers={
            "User-Agent": "SecTools-Platform/1.0"
        })
        text_b = f"HTTP {resp_post.status_code}\n"
        for k, v in resp_post.headers.items():
            text_b += f"{k}: {v}\n"
        text_b += f"\n{resp_post.text[:5000]}"

        return text_a, text_b

    @staticmethod
    def _generate_diff_html(
        lines_a: list[str], lines_b: list[str]
    ) -> str:
        """生成 HTML 差异渲染"""
        diff = difflib.HtmlDiff(wrapcolumn=80)
        return diff.make_table(
            lines_a, lines_b,
            fromdesc="🔴 原始 (A)",
            todesc="🟢 对比 (B)",
            context=True,
            numlines=3,
        )


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


def _textarea_style() -> str:
    return """
        QTextEdit { background-color: #11111b; color: #cdd6f4;
            border: 1px solid #313244; border-radius: 6px;
            padding: 8px;
            font-family: Consolas, "Microsoft YaHei Mono", monospace;
            font-size: 12px; }
        QTextEdit:focus { border-color: #89b4fa; }
    """


def _btn_primary_style() -> str:
    return """
        QPushButton { background-color: #f9e2af; color: #1e1e2e;
            border: none; border-radius: 6px;
            padding: 10px 24px; font-size: 13px; font-weight: bold; }
        QPushButton:hover { background-color: #f5c2e7; }
    """


def _btn_accent_style() -> str:
    return """
        QPushButton { background-color: #89b4fa; color: #1e1e2e;
            border: none; border-radius: 6px;
            padding: 8px 16px; font-size: 12px; font-weight: bold; }
        QPushButton:hover { background-color: #74c7ec; }
    """


def _btn_secondary_style() -> str:
    return """
        QPushButton { background-color: #313244; color: #cdd6f4;
            border: 1px solid #45475a; border-radius: 6px;
            padding: 8px 16px; font-size: 12px; }
        QPushButton:hover { background-color: #45475a; }
    """
