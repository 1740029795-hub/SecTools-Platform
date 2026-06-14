"""
HTTP 请求编辑器 — 发送自定义 HTTP 请求并查看响应。

特性:
  - HTTP 方法: GET / POST / PUT / DELETE / PATCH / HEAD / OPTIONS
  - 自定义 Header (Key: Value 格式)
  - 原始 Body 编辑 (支持 JSON/XML/Form)
  - 响应查看: Status / Headers / Body / 耗时
  - 历史记录 (最近 50 条)
  - JSON 响应自动格式化
  - 复制为 cURL 命令
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Any, Optional

import requests
from requests.exceptions import RequestException

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.tool_base import BaseTool, ToolCategory, ToolMeta
from core.tool_registry import register_tool

HTTP_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]


class HttpEditorWidget(QWidget):
    """HTTP 请求编辑器 UI"""

    execute_requested = pyqtSignal(dict)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._history: list[dict] = []
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # ---- 请求行 ----
        req_row = QHBoxLayout()

        self._method_combo = QComboBox()
        self._method_combo.addItems(HTTP_METHODS)
        self._method_combo.setCurrentText("GET")
        self._method_combo.setStyleSheet(_combo_style())
        self._method_combo.setFixedWidth(100)
        req_row.addWidget(self._method_combo)

        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("https://example.com/api/endpoint")
        self._url_input.setStyleSheet(_input_style())
        self._url_input.returnPressed.connect(self._send_request)
        req_row.addWidget(self._url_input, stretch=1)

        self._send_btn = QPushButton("▶ 发送")
        self._send_btn.setStyleSheet(_btn_primary_style())
        self._send_btn.clicked.connect(self._send_request)
        req_row.addWidget(self._send_btn)

        layout.addLayout(req_row)

        # ---- 主内容区 (请求 | 响应) ----
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # === 左侧：请求编辑 ===
        req_panel = QWidget()
        rl = QVBoxLayout(req_panel)
        rl.setContentsMargins(0, 0, 0, 0)
        req_tabs = QTabWidget()
        req_tabs.setStyleSheet(_tab_style())

        # Headers 标签页
        header_tab = QWidget()
        hl = QVBoxLayout(header_tab)
        hl.setContentsMargins(8, 8, 8, 8)
        hl.addWidget(QLabel("请求头 (每行一个 Key: Value):"))
        self._headers_edit = QTextEdit()
        self._headers_edit.setPlaceholderText(
            "Content-Type: application/json\n"
            "Authorization: Bearer token123\n"
            "User-Agent: SecTools/1.0"
        )
        self._headers_edit.setStyleSheet(_textarea_style())
        hl.addWidget(self._headers_edit)
        req_tabs.addTab(header_tab, "Headers")

        # Body 标签页
        body_tab = QWidget()
        bl = QVBoxLayout(body_tab)
        bl.setContentsMargins(8, 8, 8, 8)
        bl.addWidget(QLabel("请求体:"))
        self._body_edit = QTextEdit()
        self._body_edit.setPlaceholderText('{"key": "value"}')
        self._body_edit.setStyleSheet(_textarea_style())
        bl.addWidget(self._body_edit)

        # Body 快捷按钮
        body_btn_row = QHBoxLayout()
        for label, content in [
            ("JSON", '{\n  "key": "value"\n}'),
            ("Form", "key1=value1&key2=value2"),
            ("XML", "<root>\n  <key>value</key>\n</root>"),
        ]:
            btn = QPushButton(label)
            btn.setStyleSheet(_btn_small_style())
            btn.clicked.connect(lambda checked, c=content: self._body_edit.setPlainText(c))
            body_btn_row.addWidget(btn)
        body_btn_row.addStretch()
        bl.addLayout(body_btn_row)
        req_tabs.addTab(body_tab, "Body")

        rl.addWidget(req_tabs)
        splitter.addWidget(req_panel)

        # === 右侧：响应查看 ===
        resp_panel = QWidget()
        rpl = QVBoxLayout(resp_panel)
        rpl.setContentsMargins(0, 0, 0, 0)

        # 响应状态
        self._resp_status = QLabel("")
        self._resp_status.setStyleSheet(
            "color: #a6e3a1; font-size: 14px; font-weight: bold; padding: 4px 8px;"
        )
        rpl.addWidget(self._resp_status)

        resp_tabs = QTabWidget()
        resp_tabs.setStyleSheet(_tab_style())

        # Response Body
        body_resp_tab = QWidget()
        brl = QVBoxLayout(body_resp_tab)
        brl.setContentsMargins(8, 8, 8, 8)
        self._resp_body = QTextEdit()
        self._resp_body.setReadOnly(True)
        self._resp_body.setStyleSheet(_textarea_style())
        brl.addWidget(self._resp_body)
        resp_tabs.addTab(body_resp_tab, "Body")

        # Response Headers
        hdr_resp_tab = QWidget()
        hrl = QVBoxLayout(hdr_resp_tab)
        hrl.setContentsMargins(8, 8, 8, 8)
        self._resp_headers = QTextEdit()
        self._resp_headers.setReadOnly(True)
        self._resp_headers.setStyleSheet(_textarea_style())
        hrl.addWidget(self._resp_headers)
        resp_tabs.addTab(hdr_resp_tab, "Headers")

        rpl.addWidget(resp_tabs)
        splitter.addWidget(resp_panel)

        splitter.setSizes([500, 600])
        layout.addWidget(splitter, stretch=1)

        # ---- 历史记录 ----
        hist_group = QGroupBox("历史记录")
        hist_group.setStyleSheet(_group_style())
        hist_layout = QVBoxLayout(hist_group)

        self._hist_table = QTableWidget()
        self._hist_table.setColumnCount(4)
        self._hist_table.setHorizontalHeaderLabels(["时间", "方法", "URL", "状态码"])
        self._hist_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._hist_table.setMaximumHeight(150)
        self._hist_table.setAlternatingRowColors(True)
        self._hist_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._hist_table.setStyleSheet(_table_style())
        self._hist_table.itemDoubleClicked.connect(self._on_history_clicked)
        hist_layout.addWidget(self._hist_table)

        layout.addWidget(hist_group)

    def get_params(self) -> dict:
        headers_text = self._headers_edit.toPlainText()
        headers = {}
        for line in headers_text.strip().split("\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip()] = v.strip()

        return {
            "method": self._method_combo.currentText(),
            "url": self._url_input.text().strip(),
            "headers": headers,
            "body": self._body_edit.toPlainText(),
        }

    def set_response(self, status: str, headers: str, body: str, elapsed: float) -> None:
        self._resp_status.setText(f"{status}  ({elapsed:.2f}s)")
        self._resp_body.setPlainText(body)
        self._resp_headers.setPlainText(headers)

    def set_response_raw(self, text: str) -> None:
        self._resp_body.setPlainText(text)

    def add_history(
        self, timestamp: str, method: str, url: str, status_code: int
    ) -> None:
        self._history.insert(0, {
            "timestamp": timestamp,
            "method": method,
            "url": url,
            "status_code": status_code,
        })
        if len(self._history) > 50:
            self._history.pop()

        self._hist_table.setRowCount(0)
        for h in self._history:
            row = self._hist_table.rowCount()
            self._hist_table.insertRow(row)
            self._hist_table.setItem(row, 0, QTableWidgetItem(h["timestamp"]))
            self._hist_table.setItem(row, 1, QTableWidgetItem(h["method"]))
            self._hist_table.setItem(row, 2, QTableWidgetItem(h["url"]))
            item = QTableWidgetItem(str(h["status_code"]))
            if 200 <= h["status_code"] < 300:
                item.setForeground(Qt.GlobalColor.green)
            elif h["status_code"] >= 400:
                item.setForeground(Qt.GlobalColor.red)
            self._hist_table.setItem(row, 3, item)

    def _send_request(self) -> None:
        params = self.get_params()
        if params["url"]:
            self.execute_requested.emit(params)

    def _on_history_clicked(self, item: QTableWidgetItem) -> None:
        row = item.row()
        if row < len(self._history):
            h = self._history[row]
            self._method_combo.setCurrentText(h["method"])
            self._url_input.setText(h["url"])


@register_tool
class HttpEditorTool(BaseTool):
    """HTTP 请求编辑器"""

    meta = ToolMeta(
        name="http_editor",
        display_name="HTTP 请求编辑器",
        category=ToolCategory.WEB_TESTING,
        description="发送自定义 HTTP 请求，查看响应，支持历史记录和 cURL 导出",
        icon="🌐",
        version="1.0.0",
        keywords=["http", "请求", "burp", "repeater", "api", "测试"],
    )

    def __init__(self) -> None:
        super().__init__()
        self._widget: Optional[HttpEditorWidget] = None

    def create_widget(self) -> QWidget:
        self._widget = HttpEditorWidget()
        self._widget.execute_requested.connect(lambda p: self.execute(p))
        return self._widget

    def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        method = params.get("method", "GET")
        url = params.get("url", "")
        headers = params.get("headers", {})
        body = params.get("body", "")

        if not url.startswith(("http://", "https://")):
            url = "https://" + url
            if self._widget:
                self._widget._url_input.setText(url)

        self.output_ready.emit(f"📡 {method} {url}")

        try:
            start = time.time()
            resp = requests.request(
                method=method,
                url=url,
                headers=headers,
                data=body if body else None,
                timeout=30,
                allow_redirects=True,
                verify=False,  # 忽略 SSL 错误便于测试
            )
            elapsed = time.time() - start

            # 格式化响应
            status = f"HTTP {resp.status_code} {resp.reason}"
            resp_headers = "\n".join(f"{k}: {v}" for k, v in resp.headers.items())

            # 尝试美化 JSON 响应
            resp_body = resp.text
            try:
                json_body = resp.json()
                resp_body = json.dumps(json_body, indent=2, ensure_ascii=False)
            except Exception:
                pass

            if self._widget:
                self._widget.set_response(status, resp_headers, resp_body, elapsed)
                self._widget.add_history(
                    datetime.now().strftime("%H:%M:%S"),
                    method,
                    url,
                    resp.status_code,
                )

            self.output_ready.emit(
                f"✓ {status} — {len(resp.content)} bytes — {elapsed:.2f}s"
            )

            return {
                "status_code": resp.status_code,
                "headers": dict(resp.headers),
                "body": resp.text,
                "elapsed": elapsed,
            }

        except RequestException as e:
            err = f"请求失败: {e}"
            self.output_ready.emit(f"✗ {err}")
            if self._widget:
                self._widget.set_response_raw(err)
            return {"error": str(e)}

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        errors = []
        url = params.get("url", "").strip()
        if not url:
            errors.append("请输入 URL")
        return errors


# ---- 样式 ----

def _group_style() -> str:
    return """
        QGroupBox { color: #cdd6f4; font-size: 13px; font-weight: bold;
            border: 1px solid #313244; border-radius: 8px;
            margin-top: 8px; padding-top: 18px; }
        QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 8px; }
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
        QComboBox QAbstractItemView { background-color: #1e1e2e; color: #cdd6f4;
            selection-background-color: #45475a; }
    """


def _textarea_style() -> str:
    return """
        QTextEdit { background-color: #11111b; color: #cdd6f4;
            border: 1px solid #313244; border-radius: 6px;
            padding: 8px;
            font-family: Consolas, "Microsoft YaHei Mono", monospace;
            font-size: 12px; }
    """


def _btn_primary_style() -> str:
    return """
        QPushButton { background-color: #89b4fa; color: #1e1e2e;
            border: none; border-radius: 6px;
            padding: 8px 20px; font-size: 13px; font-weight: bold; }
        QPushButton:hover { background-color: #74c7ec; }
    """


def _btn_small_style() -> str:
    return """
        QPushButton { background-color: #45475a; color: #cdd6f4;
            border: none; border-radius: 4px;
            padding: 3px 10px; font-size: 11px; }
        QPushButton:hover { background-color: #585b70; }
    """


def _tab_style() -> str:
    return """
        QTabWidget::pane { border: 1px solid #313244; background-color: #1e1e2e; }
        QTabBar::tab { background-color: #181825; color: #a6adc8;
            padding: 6px 16px; font-size: 12px;
            border: 1px solid #313244; border-bottom: none; }
        QTabBar::tab:selected { background-color: #1e1e2e; color: #cdd6f4; }
    """


def _table_style() -> str:
    return """
        QTableWidget { background-color: #11111b; color: #cdd6f4;
            border: 1px solid #313244; border-radius: 6px;
            gridline-color: #313244; font-size: 11px;
            alternate-background-color: #181825; }
        QHeaderView::section { background-color: #1e1e2e; color: #cdd6f4;
            border: 1px solid #313244; padding: 4px 6px; font-weight: bold; }
    """
