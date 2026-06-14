"""
URL 参数分析工具 — 提取和分析 URL 中的参数，识别潜在注入点。

特性:
  - URL 参数自动提取 (Query String / Fragment)
  - 参数解码 (URL Decode / Base64)
  - 参数值类型识别 (数字/字符串/JSON/Base64/JWT)
  - 注入点标记 (数字→SQLi, 字符串→XSS, 回调→JSONP 等)
  - 批量 URL 分析
"""

from __future__ import annotations

import base64
import json
import re
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse, unquote

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
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


class UrlAnalyzerWidget(QWidget):
    """URL 分析器 UI"""

    execute_requested = pyqtSignal(dict)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ---- URL 输入 ----
        input_group = QGroupBox("URL 输入")
        input_group.setStyleSheet(_group_style())
        il = QVBoxLayout(input_group)

        url_row = QHBoxLayout()
        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("https://example.com/page?id=123&name=test&callback=jsonp")
        self._url_input.setStyleSheet(_input_style())
        self._url_input.returnPressed.connect(self._analyze)
        url_row.addWidget(self._url_input, stretch=1)

        self._analyze_btn = QPushButton("🔍 分析")
        self._analyze_btn.setStyleSheet(_btn_primary_style())
        self._analyze_btn.clicked.connect(self._analyze)
        url_row.addWidget(self._analyze_btn)
        il.addLayout(url_row)

        # 批量
        il.addWidget(QLabel("或批量粘贴（每行一个 URL）:"))
        self._batch_edit = QTextEdit()
        self._batch_edit.setPlaceholderText("https://example.com?a=1\nhttps://example.com?b=2")
        self._batch_edit.setMaximumHeight(80)
        self._batch_edit.setStyleSheet(_textarea_style())
        il.addWidget(self._batch_edit)

        layout.addWidget(input_group)

        # ---- 参数详情 ----
        param_group = QGroupBox("参数分析")
        param_group.setStyleSheet(_group_style())
        pl = QVBoxLayout(param_group)

        self._param_table = QTableWidget()
        self._param_table.setColumnCount(5)
        self._param_table.setHorizontalHeaderLabels([
            "参数名", "原始值", "解码值", "类型", "注入风险"
        ])
        self._param_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._param_table.setAlternatingRowColors(True)
        self._param_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._param_table.setStyleSheet(_table_style())
        pl.addWidget(self._param_table)

        layout.addWidget(param_group, stretch=1)

        # ---- URL 结构 ----
        struct_group = QGroupBox("URL 结构解析")
        struct_group.setStyleSheet(_group_style())
        sl = QVBoxLayout(struct_group)
        self._struct_edit = QTextEdit()
        self._struct_edit.setReadOnly(True)
        self._struct_edit.setMaximumHeight(200)
        self._struct_edit.setStyleSheet(_textarea_style())
        sl.addWidget(self._struct_edit)
        layout.addWidget(struct_group)

    def get_params(self) -> dict:
        urls = []
        single = self._url_input.text().strip()
        if single:
            urls.append(single)
        batch = self._batch_edit.toPlainText().strip()
        if batch:
            urls.extend(line.strip() for line in batch.split("\n") if line.strip())
        return {"urls": urls}

    def clear(self) -> None:
        self._param_table.setRowCount(0)

    def add_param(
        self, name: str, raw: str, decoded: str, ptype: str, risk: str
    ) -> None:
        row = self._param_table.rowCount()
        self._param_table.insertRow(row)
        self._param_table.setItem(row, 0, QTableWidgetItem(name))
        self._param_table.setItem(row, 1, QTableWidgetItem(raw))
        self._param_table.setItem(row, 2, QTableWidgetItem(decoded))
        self._param_table.setItem(row, 3, QTableWidgetItem(ptype))

        risk_item = QTableWidgetItem(risk)
        if "🔴" in risk:
            risk_item.setForeground(Qt.GlobalColor.red)
        elif "🟡" in risk:
            risk_item.setForeground(Qt.GlobalColor.yellow)
        elif "🟢" in risk:
            risk_item.setForeground(Qt.GlobalColor.green)
        self._param_table.setItem(row, 4, risk_item)

    def set_structure(self, text: str) -> None:
        self._struct_edit.setPlainText(text)

    def _analyze(self) -> None:
        self.execute_requested.emit(self.get_params())


@register_tool
class UrlAnalyzerTool(BaseTool):
    """URL 参数分析"""

    meta = ToolMeta(
        name="url_analyzer",
        display_name="URL 参数分析",
        category=ToolCategory.WEB_TESTING,
        description="提取 URL 参数，识别类型和潜在注入点（SQLi/XSS/SSRF 等）",
        icon="🔗",
        version="1.0.0",
        keywords=["url", "参数", "分析", "注入点", "parameter"],
    )

    def __init__(self) -> None:
        super().__init__()
        self._widget: Optional[UrlAnalyzerWidget] = None

    def create_widget(self) -> QWidget:
        self._widget = UrlAnalyzerWidget()
        self._widget.execute_requested.connect(lambda p: self.execute(p))
        return self._widget

    def execute(self, params: dict[str, Any]) -> list[dict]:
        urls = params.get("urls", [])
        if not urls:
            self.output_ready.emit("[提示] 请输入 URL")
            return []

        all_params: list[dict] = []

        if self._widget:
            self._widget.clear()
            self._widget.set_structure("")

        for url in urls:
            self.output_ready.emit(f"分析: {url[:80]}...")

            parsed = urlparse(url)
            params = parse_qs(parsed.query, keep_blank_values=True)

            # URL 结构
            structure = (
                f"Scheme:   {parsed.scheme}\n"
                f"Host:     {parsed.hostname}\n"
                f"Port:     {parsed.port or '默认'}\n"
                f"Path:     {parsed.path}\n"
                f"Query:    {parsed.query}\n"
                f"Fragment: {parsed.fragment or '(无)'}\n"
                f"参数数量: {len(params)}"
            )
            if self._widget:
                self._widget.set_structure(structure)

            for name, values in params.items():
                for val in values:
                    decoded = unquote(val)
                    ptype = self._detect_type(decoded)
                    risk = self._assess_risk(name, decoded, ptype)

                    all_params.append({
                        "name": name, "raw": val, "decoded": decoded,
                        "type": ptype, "risk": risk,
                    })

                    if self._widget:
                        self._widget.add_param(name, val, decoded, ptype, risk)

        self.output_ready.emit(
            f"✓ 分析完成: {len(urls)} 个 URL, {len(all_params)} 个参数"
        )
        return all_params

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        return []

    # ---- 内部 ----

    @staticmethod
    def _detect_type(value: str) -> str:
        if not value:
            return "空值"
        if re.match(r"^\d+$", value):
            return "整数"
        if re.match(r"^\d+\.\d+$", value):
            return "浮点数"
        if re.match(r"^[\w-]+\.[\w-]+\.[\w-]+$", value) and "." in value:
            # 检测 JWT
            parts = value.split(".")
            if len(parts) == 3:
                try:
                    for p in parts[:2]:
                        p2 = p + "=" * (4 - len(p) % 4)
                        base64.urlsafe_b64decode(p2)
                    return "JWT Token"
                except Exception:
                    pass
        try:
            base64.b64decode(value + "=" * (4 - len(value) % 4))
            # 检测是否为有效的 base64
            if re.match(r"^[A-Za-z0-9+/=]+$", value):
                return "Base64"
        except Exception:
            pass
        if value.startswith("{") and value.endswith("}"):
            try:
                json.loads(value)
                return "JSON"
            except Exception:
                pass
        if value in ("true", "false"):
            return "布尔值"
        return "字符串"

    @staticmethod
    def _assess_risk(name: str, value: str, ptype: str) -> str:
        name_lower = name.lower()

        # 高危参数名
        high_risk_names = [
            "url", "uri", "path", "file", "document", "folder", "root",
            "redirect", "return", "callback", "jsonp", "template", "page",
            "cmd", "exec", "command", "shell", "query", "q", "search",
            "id", "user", "uid", "username", "password", "token",
        ]
        for rn in high_risk_names:
            if rn in name_lower:
                return f"🔴 高危 (参数名={rn})"

        if ptype == "整数":
            return "🟡 中危 (数字型 → SQLi)"
        if ptype == "JWT Token":
            return "🟡 中危 (JWT → 算法攻击)"
        if ptype == "Base64":
            return "🟡 中危 (Base64 → 编码绕过)"
        if ptype == "JSON":
            return "🟡 中危 (JSON → 注入/SSRF)"

        # HTML/JS 字符
        if any(c in value for c in "<>\"'"):
            return "🟡 中危 (特殊字符反射 → XSS)"

        return "🟢 低风险"


# ---- 样式 ----
def _group_style() -> str:
    return """QGroupBox { color: #cdd6f4; font-size: 14px; font-weight: bold;
        border: 1px solid #313244; border-radius: 8px;
        margin-top: 8px; padding-top: 20px; }
        QGroupBox::title { subcontrol-origin: margin; left: 16px; padding: 0 8px; }"""


def _input_style() -> str:
    return """QLineEdit { background-color: #313244; color: #cdd6f4;
        border: 1px solid #45475a; border-radius: 6px;
        padding: 10px 12px; font-size: 14px; }
        QLineEdit:focus { border-color: #89b4fa; }"""


def _textarea_style() -> str:
    return """QTextEdit { background-color: #11111b; color: #cdd6f4;
        border: 1px solid #313244; border-radius: 6px;
        padding: 8px; font-family: Consolas, monospace; font-size: 12px; }"""


def _btn_primary_style() -> str:
    return """QPushButton { background-color: #89b4fa; color: #1e1e2e;
        border: none; border-radius: 6px;
        padding: 10px 24px; font-size: 13px; font-weight: bold; }
        QPushButton:hover { background-color: #74c7ec; }"""


def _table_style() -> str:
    return """QTableWidget { background-color: #11111b; color: #cdd6f4;
        border: 1px solid #313244; border-radius: 6px;
        gridline-color: #313244; font-size: 12px;
        alternate-background-color: #181825; }
        QHeaderView::section { background-color: #1e1e2e; color: #cdd6f4;
        border: 1px solid #313244; padding: 6px 8px; font-weight: bold; }"""
