"""
DNS 枚举工具 — 查询域名的各类 DNS 记录。

特性:
  - 支持 A / AAAA / MX / NS / CNAME / TXT / SOA / PTR 记录类型
  - 批量查询（每行一个域名）
  - 支持自定义 DNS 服务器
  - 结果表格化展示
  - dnspython 实现
"""

from __future__ import annotations

import concurrent.futures
from typing import Any, Optional

import dns.resolver
import dns.reversename
import dns.exception

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
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

# DNS 记录类型
RECORD_TYPES = ["A", "AAAA", "MX", "NS", "CNAME", "TXT", "SOA", "PTR", "SRV", "CAA"]

# 记录类型中文说明
RECORD_DESC = {
    "A": "IPv4 地址",
    "AAAA": "IPv6 地址",
    "MX": "邮件交换",
    "NS": "域名服务器",
    "CNAME": "别名",
    "TXT": "文本记录",
    "SOA": "授权起始",
    "PTR": "反向解析",
    "SRV": "服务记录",
    "CAA": "证书颁发机构授权",
}


class DnsToolWidget(QWidget):
    """DNS 枚举 UI"""

    execute_requested = pyqtSignal(dict)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ---- 输入区 ----
        input_group = QGroupBox("查询设置")
        input_group.setStyleSheet(_group_style())
        igrid = QGridLayout(input_group)
        igrid.setSpacing(8)

        # 域名输入
        domain_label = QLabel("域名:")
        domain_label.setStyleSheet("color: #cdd6f4; font-size: 13px;")
        self._domain_input = QLineEdit()
        self._domain_input.setPlaceholderText("例如: example.com（每行一个）")
        self._domain_input.setStyleSheet(_input_style())
        self._domain_input.returnPressed.connect(self._emit_execute)
        igrid.addWidget(domain_label, 0, 0)
        igrid.addWidget(self._domain_input, 0, 1)

        # DNS 服务器
        dns_label = QLabel("DNS 服务器:")
        dns_label.setStyleSheet("color: #cdd6f4; font-size: 13px;")
        self._dns_input = QLineEdit()
        self._dns_input.setPlaceholderText("留空使用系统默认（如 8.8.8.8）")
        self._dns_input.setStyleSheet(_input_style())
        igrid.addWidget(dns_label, 1, 0)
        igrid.addWidget(self._dns_input, 1, 1)

        layout.addWidget(input_group)

        # ---- 记录类型选择 ----
        type_group = QGroupBox("记录类型")
        type_group.setStyleSheet(_group_style())
        type_layout = QHBoxLayout(type_group)
        type_layout.setSpacing(4)

        self._type_checkboxes: dict[str, QCheckBox] = {}
        for rt in RECORD_TYPES:
            cb = QCheckBox(rt)
            cb.setToolTip(RECORD_DESC.get(rt, rt))
            cb.setChecked(rt in ("A", "AAAA", "MX", "NS", "TXT"))
            cb.setStyleSheet("""
                QCheckBox {
                    color: #cdd6f4;
                    spacing: 4px;
                    font-size: 12px;
                }
                QCheckBox::indicator {
                    width: 16px;
                    height: 16px;
                }
            """)
            self._type_checkboxes[rt] = cb
            type_layout.addWidget(cb)
        type_layout.addStretch()

        layout.addWidget(type_group)

        # ---- 执行按钮 ----
        btn_layout = QHBoxLayout()
        self._run_btn = QPushButton("🔍 查询 DNS 记录")
        self._run_btn.setStyleSheet(_btn_primary_style())
        self._run_btn.clicked.connect(self._emit_execute)
        btn_layout.addWidget(self._run_btn)

        self._clear_btn = QPushButton("清空结果")
        self._clear_btn.setStyleSheet(_btn_secondary_style())
        self._clear_btn.clicked.connect(self._clear_results)
        btn_layout.addWidget(self._clear_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # ---- 结果表格 ----
        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["域名", "记录类型", "TTL", "记录值"])
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self._table.setStyleSheet("""
            QTableWidget {
                background-color: #11111b;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 6px;
                gridline-color: #313244;
                font-size: 12px;
                alternate-background-color: #181825;
            }
            QTableWidget::item:selected {
                background-color: #45475a;
            }
            QHeaderView::section {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: 1px solid #313244;
                padding: 6px 8px;
                font-weight: bold;
                font-size: 12px;
            }
        """)
        layout.addWidget(self._table, stretch=1)

        # ---- 原始输出 ----
        raw_group = QGroupBox("详细输出")
        raw_group.setStyleSheet(_group_style())
        raw_layout = QVBoxLayout(raw_group)
        self._raw_text = QTextEdit()
        self._raw_text.setReadOnly(True)
        self._raw_text.setMaximumHeight(150)
        self._raw_text.setStyleSheet("""
            QTextEdit {
                background-color: #11111b;
                color: #a6adc8;
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 8px;
                font-family: "Consolas", monospace;
                font-size: 11px;
            }
        """)
        raw_layout.addWidget(self._raw_text)
        layout.addWidget(raw_group)

    def get_params(self) -> dict:
        domain = self._domain_input.text().strip()
        dns_server = self._dns_input.text().strip() or None
        record_types = [
            rt for rt, cb in self._type_checkboxes.items() if cb.isChecked()
        ]
        return {
            "domain": domain,
            "dns_server": dns_server,
            "record_types": record_types,
        }

    def add_result_row(
        self, domain: str, record_type: str, ttl: str, value: str
    ) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._table.setItem(row, 0, QTableWidgetItem(domain))
        self._table.setItem(row, 1, QTableWidgetItem(record_type))
        self._table.setItem(row, 2, QTableWidgetItem(ttl))
        self._table.setItem(row, 3, QTableWidgetItem(value))

    def clear_results(self) -> None:
        self._table.setRowCount(0)
        self._raw_text.clear()

    def append_raw(self, text: str) -> None:
        self._raw_text.append(text)

    # ----

    def _emit_execute(self) -> None:
        params = self.get_params()
        if params["domain"]:
            self.execute_requested.emit(params)

    def _clear_results(self) -> None:
        self.clear_results()


@register_tool
class DnsLookupTool(BaseTool):
    """DNS 枚举工具"""

    meta = ToolMeta(
        name="dns_lookup",
        display_name="DNS 枚举",
        category=ToolCategory.INFO_GATHERING,
        description="查询域名的 A/AAAA/MX/NS/CNAME/TXT/SOA 等 DNS 记录",
        icon="📡",
        version="1.0.0",
        keywords=["dns", "域名", "解析", "DNS记录", "enumeration"],
    )

    def __init__(self) -> None:
        super().__init__()
        self._widget: Optional[DnsToolWidget] = None

    def create_widget(self) -> QWidget:
        self._widget = DnsToolWidget()
        self._widget.execute_requested.connect(self._on_widget_execute)
        return self._widget

    def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        domain_str = params.get("domain", "").strip()
        dns_server = params.get("dns_server")
        record_types = params.get("record_types", ["A"])

        domains = [d.strip() for d in domain_str.splitlines() if d.strip()]

        results: dict[str, list[dict]] = {}

        for domain in domains:
            self.output_ready.emit(f"🔍 查询 {domain} ...")
            self.progress_updated.emit(10)
            domain_results: list[dict] = []

            # 配置 resolver
            resolver = dns.resolver.Resolver()
            if dns_server:
                resolver.nameservers = [dns_server]
            resolver.timeout = 5
            resolver.lifetime = 10

            for rt in record_types:
                try:
                    answers = resolver.resolve(domain, rt)
                    for answer in answers:
                        record_str = str(answer)
                        ttl_str = str(answers.rrset.ttl) if answers.rrset else "-"

                        domain_results.append({
                            "type": rt,
                            "value": record_str,
                            "ttl": ttl_str,
                        })

                        # 实时更新 UI
                        if self._widget:
                            self._widget.add_result_row(
                                domain, rt, ttl_str, record_str
                            )
                        self.output_ready.emit(f"  [{rt}] {record_str} (TTL: {ttl_str})")

                except dns.resolver.NoAnswer:
                    self.output_ready.emit(f"  [{rt}] 无记录")
                except dns.resolver.NXDOMAIN:
                    self.output_ready.emit(f"  [错误] 域名 {domain} 不存在")
                    break
                except dns.resolver.NoNameservers:
                    self.output_ready.emit(f"  [错误] {domain} 无可用的域名服务器")
                    break
                except dns.exception.Timeout:
                    self.output_ready.emit(f"  [{rt}] 查询超时")
                except Exception as e:
                    self.output_ready.emit(f"  [{rt}] 错误: {e}")

            results[domain] = domain_results

        self.progress_updated.emit(100)
        self.output_ready.emit(f"✓ 查询完成，共查询 {len(domains)} 个域名")

        return results

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        errors = []
        domain = params.get("domain", "").strip()
        if not domain:
            errors.append("请输入至少一个域名")
        return errors

    def _on_widget_execute(self, params: dict) -> None:
        if self._widget:
            self._widget.clear_results()
        self.execute(params)


# ---- 样式 ----

def _group_style() -> str:
    return """
        QGroupBox {
            color: #cdd6f4;
            font-size: 14px;
            font-weight: bold;
            border: 1px solid #313244;
            border-radius: 8px;
            margin-top: 8px;
            padding-top: 20px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 16px;
            padding: 0 8px;
        }
    """


def _input_style() -> str:
    return """
        QLineEdit {
            background-color: #313244;
            color: #cdd6f4;
            border: 1px solid #45475a;
            border-radius: 6px;
            padding: 10px 12px;
            font-size: 14px;
        }
        QLineEdit:focus {
            border-color: #89b4fa;
        }
    """


def _btn_primary_style() -> str:
    return """
        QPushButton {
            background-color: #89b4fa;
            color: #1e1e2e;
            border: none;
            border-radius: 6px;
            padding: 10px 24px;
            font-size: 13px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #74c7ec;
        }
        QPushButton:pressed {
            background-color: #89dceb;
        }
    """


def _btn_secondary_style() -> str:
    return """
        QPushButton {
            background-color: #313244;
            color: #cdd6f4;
            border: 1px solid #45475a;
            border-radius: 6px;
            padding: 10px 24px;
            font-size: 13px;
        }
        QPushButton:hover {
            background-color: #45475a;
        }
    """
