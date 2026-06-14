"""
子域名发现工具 — 通过多种来源发现目标域名的子域名。

数据源:
  - crt.sh 证书透明度日志（免费、快速）
  - 内置字典爆破（精选 Top 200 子域名）
  - DNS 解析验证

特性:
  - 多源聚合
  - 自动去重
  - DNS 解析验证子域名是否存活
  - 导出结果
"""

from __future__ import annotations

import concurrent.futures
from typing import Any, Optional

import dns.resolver
import requests

from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.tool_base import BaseTool, ToolCategory, ToolMeta
from core.tool_registry import register_tool

# 内置子域名字典（Top 200）
BUILTIN_SUBDOMAINS = [
    "www", "mail", "ftp", "localhost", "webmail", "smtp", "pop", "ns1", "webdisk",
    "ns2", "cpanel", "whm", "autodiscover", "autoconfig", "m", "imap", "test",
    "ns", "blog", "pop3", "dev", "www2", "admin", "forum", "news", "vpn", "ns3",
    "mail2", "new", "mysql", "old", "lists", "support", "mobile", "mx", "static",
    "docs", "beta", "shop", "sql", "secure", "demo", "cp", "calendar", "wiki",
    "web", "media", "email", "images", "img", "download", "dns", "staging",
    "server", "db", "portal", "video", "sip", "dns2", "api", "cdn", "stats",
    "survey", "host", "www3", "dns1", "ww2", "origin", "uat", "dev2", "git",
    "monitor", "help", "apps", "home", "relay", "stage", "svn", "gateway",
    "pay", "mssql", "jobs", "auth", "live", "chat", "ns4", "store", "manage",
    "cloud", "ws", "video2", "service", "kb", "spam", "update", "search",
    "imap4", "backup", "intranet", "training", "clubs", "links", "ch1",
    "upload", "ir", "voip", "photo", "mailer", "podcast", "lib", "board",
    "office", "vc", "owa", "ads", "report", "files", "members", "crm",
    "partners", "webinar", "stream", "data", "reports", "alerts", "bbs",
    "telemetry", "sandbox", "redirect", "cms", "gallery", "directory",
    "photos", "billing", "staff", "exchange", "notifications", "sites",
    "dashboard", "alumni", "webstats", "inbound", "streaming", "chat2",
    "cdn2", "gmail", "tools", "status", "analytics", "erp", "ci", "jenkins",
]

CRTSH_URL = "https://crt.sh/?q=%25.{}&output=json"


class SubdomainToolWidget(QWidget):
    """子域名发现 UI"""

    execute_requested = pyqtSignal(dict)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ---- 输入 ----
        input_group = QGroupBox("目标设置")
        input_group.setStyleSheet(_group_style())
        igrid = QGridLayout(input_group)
        igrid.setSpacing(8)

        domain_label = QLabel("目标域名:")
        domain_label.setStyleSheet("color: #cdd6f4; font-size: 13px;")
        self._domain_input = QLineEdit()
        self._domain_input.setPlaceholderText("例如: example.com")
        self._domain_input.setStyleSheet(_input_style())
        self._domain_input.returnPressed.connect(self._emit_execute)
        igrid.addWidget(domain_label, 0, 0)
        igrid.addWidget(self._domain_input, 0, 1)

        layout.addWidget(input_group)

        # ---- 数据源选择 ----
        source_group = QGroupBox("数据源")
        source_group.setStyleSheet(_group_style())
        src_layout = QHBoxLayout(source_group)

        self._crtsh_cb = QCheckBox("crt.sh 证书日志")
        self._crtsh_cb.setChecked(True)
        self._crtsh_cb.setStyleSheet(_checkbox_style())
        src_layout.addWidget(self._crtsh_cb)

        self._dict_cb = QCheckBox("字典爆破 (Top 200)")
        self._dict_cb.setChecked(True)
        self._dict_cb.setStyleSheet(_checkbox_style())
        src_layout.addWidget(self._dict_cb)

        self._resolve_cb = QCheckBox("DNS 解析验证")
        self._resolve_cb.setChecked(True)
        self._resolve_cb.setToolTip("验证发现的子域名是否真正解析到 IP")
        self._resolve_cb.setStyleSheet(_checkbox_style())
        src_layout.addWidget(self._resolve_cb)

        src_layout.addStretch()
        layout.addWidget(source_group)

        # ---- 按钮 ----
        btn_layout = QHBoxLayout()
        self._run_btn = QPushButton("🔎 发现子域名")
        self._run_btn.setStyleSheet(_btn_primary_style())
        self._run_btn.clicked.connect(self._emit_execute)
        btn_layout.addWidget(self._run_btn)

        self._export_btn = QPushButton("📋 复制结果")
        self._export_btn.setStyleSheet(_btn_secondary_style())
        self._export_btn.clicked.connect(self._copy_results)
        btn_layout.addWidget(self._export_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # ---- 进度条 ----
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setMaximumHeight(6)
        self._progress.setStyleSheet("""
            QProgressBar {
                background-color: #313244;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #a6e3a1;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self._progress)

        # ---- 结果表格 ----
        self._table = QTableWidget()
        self._table.setColumnCount(3)
        self._table.setHorizontalHeaderLabels(["子域名", "IP 地址", "来源"])
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setStyleSheet(_table_style())
        layout.addWidget(self._table, stretch=1)

        # 统计标签
        self._stat_label = QLabel("")
        self._stat_label.setStyleSheet("color: #6c7086; font-size: 12px; padding: 4px;")
        layout.addWidget(self._stat_label)

    def get_params(self) -> dict:
        return {
            "domain": self._domain_input.text().strip(),
            "use_crtsh": self._crtsh_cb.isChecked(),
            "use_dict": self._dict_cb.isChecked(),
            "resolve_dns": self._resolve_cb.isChecked(),
        }

    def add_result(self, subdomain: str, ip: str, source: str) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._table.setItem(row, 0, QTableWidgetItem(subdomain))
        item_ip = QTableWidgetItem(ip)
        if ip:
            item_ip.setForeground(Qt.GlobalColor.green)
        else:
            item_ip.setText("未解析")
            item_ip.setForeground(Qt.GlobalColor.gray)
        self._table.setItem(row, 1, item_ip)
        self._table.setItem(row, 2, QTableWidgetItem(source))

    def set_progress(self, value: int) -> None:
        self._progress.setVisible(True)
        self._progress.setValue(value)
        if value >= 100:
            self._progress.setVisible(False)

    def set_stat(self, text: str) -> None:
        self._stat_label.setText(text)

    def clear_results(self) -> None:
        self._table.setRowCount(0)
        self._stat_label.clear()

    def _emit_execute(self) -> None:
        params = self.get_params()
        if params["domain"]:
            self.execute_requested.emit(params)

    def _copy_results(self) -> None:
        lines = []
        for r in range(self._table.rowCount()):
            sd = self._table.item(r, 0).text()
            ip = self._table.item(r, 1).text()
            lines.append(f"{sd}\t{ip}")
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText("\n".join(lines))


@register_tool
class SubdomainDiscoveryTool(BaseTool):
    """子域名发现工具"""

    meta = ToolMeta(
        name="subdomain_discovery",
        display_name="子域名发现",
        category=ToolCategory.INFO_GATHERING,
        description="通过 crt.sh + 字典爆破 + DNS 验证发现目标域名下的所有子域名",
        icon="🔎",
        version="1.0.0",
        keywords=["子域名", "subdomain", "crt.sh", "爆破", "发现"],
    )

    def __init__(self) -> None:
        super().__init__()
        self._widget: Optional[SubdomainToolWidget] = None

    def create_widget(self) -> QWidget:
        self._widget = SubdomainToolWidget()
        self._widget.execute_requested.connect(self._on_widget_execute)
        return self._widget

    def execute(self, params: dict[str, Any]) -> set[str]:
        domain = params["domain"]
        use_crtsh = params["use_crtsh"]
        use_dict = params["use_dict"]
        resolve_dns = params["resolve_dns"]

        all_subdomains: set[str] = set()
        total_steps = (1 if use_crtsh else 0) + (1 if use_dict else 0)
        step = 0

        # 1) crt.sh
        if use_crtsh:
            step += 1
            self.output_ready.emit("[crt.sh] 正在查询证书透明度日志...")
            self.progress_updated.emit(int(step / total_steps * 50))
            crtsh_results = self._query_crtsh(domain)
            all_subdomains.update(crtsh_results)
            self.output_ready.emit(f"[crt.sh] 发现 {len(crtsh_results)} 个子域名")

        # 2) 字典爆破
        if use_dict:
            step += 1
            self.output_ready.emit(f"[字典] 开始爆破 {len(BUILTIN_SUBDOMAINS)} 个常见子域名...")
            self.progress_updated.emit(int(step / total_steps * 50))
            dict_results = self._dictionary_bruteforce(domain, BUILTIN_SUBDOMAINS)
            all_subdomains.update(dict_results)
            self.output_ready.emit(f"[字典] 发现 {len(dict_results)} 个子域名")

        all_subdomains.add(domain)  # 包含主域名

        self.progress_updated.emit(60)

        # 3) DNS 解析验证
        resolved: dict[str, str] = {}
        if resolve_dns:
            self.output_ready.emit(f"[DNS] 正在解析 {len(all_subdomains)} 个子域名...")
            subdomain_list = sorted(all_subdomains)
            for i, sd in enumerate(subdomain_list):
                progress = 60 + int((i + 1) / len(subdomain_list) * 40)
                self.progress_updated.emit(progress)

                ip = self._resolve_domain(sd)
                if ip:
                    resolved[sd] = ip
                    if self._widget:
                        self._widget.add_result(sd, ip, "已解析")
                    self.output_ready.emit(f"  ✓ {sd} → {ip}")
                else:
                    resolved[sd] = ""
                    if self._widget:
                        self._widget.add_result(sd, "", "未解析")
        else:
            for sd in sorted(all_subdomains):
                resolved[sd] = ""
                if self._widget:
                    self._widget.add_result(sd, "", "")

        # 统计
        resolved_count = sum(1 for ip in resolved.values() if ip)
        stat = (
            f"共发现 {len(all_subdomains)} 个子域名，"
            f"其中 {resolved_count} 个解析成功"
        )
        if self._widget:
            self._widget.set_stat(stat)
            self._widget.set_progress(100)

        self.output_ready.emit(f"✓ {stat}")
        self.progress_updated.emit(100)

        return all_subdomains

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        errors = []
        domain = params.get("domain", "").strip()
        if not domain:
            errors.append("请输入目标域名")
        return errors

    def _on_widget_execute(self, params: dict) -> None:
        if self._widget:
            self._widget.clear_results()
        self.execute(params)

    # ---- 内部方法 ----

    def _query_crtsh(self, domain: str) -> set[str]:
        """查询 crt.sh"""
        results: set[str] = set()
        try:
            resp = requests.get(
                CRTSH_URL.format(domain),
                timeout=15,
                headers={"User-Agent": "SecTools-Platform/1.0"},
            )
            if resp.status_code == 200:
                data = resp.json()
                for entry in data:
                    names = entry.get("name_value", "")
                    for name in names.split("\n"):
                        name = name.strip().lstrip("*.").lower()
                        if name.endswith(domain) and name != domain:
                            results.add(name)
        except Exception as e:
            self.output_ready.emit(f"  [crt.sh 错误] {e}")
        return results

    def _dictionary_bruteforce(
        self, domain: str, wordlist: list[str]
    ) -> set[str]:
        """字典爆破"""
        results: set[str] = set()
        resolver = dns.resolver.Resolver()
        resolver.timeout = 2
        resolver.lifetime = 4

        for prefix in wordlist:
            sd = f"{prefix}.{domain}"
            try:
                resolver.resolve(sd, "A")
                results.add(sd)
            except Exception:
                pass
        return results

    @staticmethod
    def _resolve_domain(domain: str) -> str:
        """解析域名 → IP"""
        try:
            answers = dns.resolver.resolve(domain, "A")
            return str(answers[0])
        except Exception:
            return ""


# ---- 样式 ----

def _group_style() -> str:
    return """
        QGroupBox {
            color: #cdd6f4; font-size: 14px; font-weight: bold;
            border: 1px solid #313244; border-radius: 8px;
            margin-top: 8px; padding-top: 20px;
        }
        QGroupBox::title { subcontrol-origin: margin; left: 16px; padding: 0 8px; }
    """


def _input_style() -> str:
    return """
        QLineEdit {
            background-color: #313244; color: #cdd6f4;
            border: 1px solid #45475a; border-radius: 6px;
            padding: 10px 12px; font-size: 14px;
        }
        QLineEdit:focus { border-color: #89b4fa; }
    """


def _checkbox_style() -> str:
    return """
        QCheckBox { color: #cdd6f4; spacing: 6px; font-size: 13px; }
        QCheckBox::indicator { width: 18px; height: 18px; }
    """


def _btn_primary_style() -> str:
    return """
        QPushButton {
            background-color: #a6e3a1; color: #1e1e2e;
            border: none; border-radius: 6px;
            padding: 10px 24px; font-size: 13px; font-weight: bold;
        }
        QPushButton:hover { background-color: #94e2d5; }
    """


def _btn_secondary_style() -> str:
    return """
        QPushButton {
            background-color: #313244; color: #cdd6f4;
            border: 1px solid #45475a; border-radius: 6px;
            padding: 10px 24px; font-size: 13px;
        }
        QPushButton:hover { background-color: #45475a; }
    """


def _table_style() -> str:
    return """
        QTableWidget {
            background-color: #11111b; color: #cdd6f4;
            border: 1px solid #313244; border-radius: 6px;
            gridline-color: #313244; font-size: 12px;
            alternate-background-color: #181825;
        }
        QTableWidget::item:selected { background-color: #45475a; }
        QHeaderView::section {
            background-color: #1e1e2e; color: #cdd6f4;
            border: 1px solid #313244;
            padding: 6px 8px; font-weight: bold; font-size: 12px;
        }
    """
