"""
Web 技术指纹识别 — 识别目标网站使用的技术栈。

特性:
  - HTTP 响应头分析
  - HTML/JS 特征签名匹配
  - Cookie 特征检测
  - 常见框架/CMS/CDN/服务器识别
  - 可扩展签名库
"""

from __future__ import annotations

import re
from typing import Any, Optional

import requests

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
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

# 技术签名库: 类别 → [(名称, 匹配类型, 正则/关键字, 图标)]
TECH_SIGNATURES: dict[str, list[tuple[str, str, str, str]]] = {
    "Web 服务器": [
        ("Apache", "header:Server", r"Apache[/\s]?([\d.]+)?", "🪶"),
        ("Nginx", "header:Server", r"nginx[/\s]?([\d.]+)?", "🟢"),
        ("IIS", "header:Server", r"Microsoft-IIS[/\s]?([\d.]+)?", "🔵"),
        ("LiteSpeed", "header:Server", r"LiteSpeed", "⚡"),
        ("Caddy", "header:Server", r"Caddy", "🟡"),
        ("Tomcat", "header:Server", r"Apache-Coyote", "🐱"),
        ("Gunicorn", "header:Server", r"gunicorn", "🦄"),
    ],
    "编程语言/框架": [
        ("PHP", "header:X-Powered-By", r"PHP[/\s]?([\d.]+)?", "🐘"),
        ("ASP.NET", "header:X-Powered-By", r"ASP\.NET", "🔷"),
        ("Node.js", "header:X-Powered-By", r"Express|Node", "🟩"),
        ("Django", "cookie", r"csrftoken", "🎸"),
        ("Laravel", "cookie", r"laravel_session", "🔺"),
        ("Ruby on Rails", "cookie", r"_session.*rails", "💎"),
        ("Spring Boot", "header:X-Application-Context", r".+", "🍃"),
        ("Flask", "cookie", r"session=.*flask", "🧪"),
        ("Next.js", "meta", r"<meta[^>]*next-head", "▲"),
        ("Vue.js", "meta:html", r"<div[^>]*data-v-\w+", "💚"),
        ("React", "meta:html", r"react-root|_reactRoot", "⚛️"),
        ("jQuery", "script:html", r"jquery[/\s]?([\d.]+)?\.js", "📗"),
        ("Bootstrap", "meta:html", r"bootstrap[/\s]?([\d.]+)?\.(css|js)", "🅱️"),
        ("Tailwind CSS", "meta:html", r"tailwindcss[/\s]?([\d.]+)?", "🌊"),
    ],
    "CMS": [
        ("WordPress", "meta:html", r"wp-content|wordpress", "📝"),
        ("Drupal", "meta:html", r"Drupal|drupal\.js", "💧"),
        ("Joomla", "meta:html", r"joomla|com_content", "🎨"),
        ("Discuz", "meta:html", r"discuz|Discuz!", "💬"),
        ("DedeCMS", "meta:html", r"dedecms|DedeCMS", "🏗️"),
    ],
    "CDN/WAF": [
        ("Cloudflare", "header:cf-ray", r".+", "☁️"),
        ("Cloudflare", "header:server", r"cloudflare", "☁️"),
        ("阿里云 CDN", "header:X-Swift-CacheTime", r".+", "🇨🇳"),
        ("腾讯云 CDN", "header:X-NWS-LOG-UUID", r".+", "🇨🇳"),
        ("AWS CloudFront", "header:X-Cache", r"CloudFront", "🟠"),
        ("Fastly", "header:X-Served-By", r"Fastly", "⚡"),
        ("Varnish", "header:X-Varnish", r".+", "🔧"),
    ],
    "JavaScript 库": [
        ("Google Analytics", "script:html", r"google-analytics|gtag", "📊"),
        ("Font Awesome", "meta:html", r"font-?awesome", "🔤"),
        ("Swiper", "meta:html", r"swiper[/\s]?([\d.]+)?\.js", "🎠"),
        ("Axios", "script:html", r"axios[/\s]?([\d.]+)?", "📡"),
        ("Lodash", "script:html", r"lodash[/\s]?([\d.]+)?", "🔨"),
    ],
    "SSL/TLS": [
        ("Let's Encrypt", "ssl:issuer", r"Let's Encrypt", "🔒"),
        ("DigiCert", "ssl:issuer", r"DigiCert", "🛡️"),
        ("Sectigo", "ssl:issuer", r"Sectigo", "🛡️"),
    ],
}


class FingerprintToolWidget(QWidget):
    """指纹识别 UI"""

    execute_requested = pyqtSignal(dict)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ---- 输入 ----
        input_group = QGroupBox("目标网站")
        input_group.setStyleSheet(_group_style())
        igrid = QGridLayout(input_group)
        igrid.setSpacing(8)

        url_label = QLabel("URL:")
        url_label.setStyleSheet("color: #cdd6f4; font-size: 13px;")
        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("https://example.com")
        self._url_input.setStyleSheet(_input_style())
        self._url_input.returnPressed.connect(self._emit_execute)
        igrid.addWidget(url_label, 0, 0)
        igrid.addWidget(self._url_input, 0, 1)

        layout.addWidget(input_group)

        # ---- 按钮 ----
        btn_layout = QHBoxLayout()
        self._run_btn = QPushButton("🔬 识别技术栈")
        self._run_btn.setStyleSheet(_btn_primary_style())
        self._run_btn.clicked.connect(self._emit_execute)
        btn_layout.addWidget(self._run_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # ---- 结果表格 ----
        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["类别", "技术", "版本", "证据"])
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setStyleSheet(_table_style())
        layout.addWidget(self._table, stretch=1)

        # ---- HTTP 响应头 ----
        header_group = QGroupBox("HTTP 响应头")
        header_group.setStyleSheet(_group_style())
        header_layout = QVBoxLayout(header_group)
        self._header_text = QTextEdit()
        self._header_text.setReadOnly(True)
        self._header_text.setMaximumHeight(150)
        self._header_text.setStyleSheet("""
            QTextEdit {
                background-color: #11111b; color: #a6adc8;
                border: 1px solid #313244; border-radius: 6px;
                padding: 8px;
                font-family: "Consolas", monospace;
                font-size: 11px;
            }
        """)
        header_layout.addWidget(self._header_text)
        layout.addWidget(header_group)

    def get_params(self) -> dict:
        url = self._url_input.text().strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        return {"url": url}

    def add_result(self, category: str, name: str, version: str, evidence: str) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._table.setItem(row, 0, QTableWidgetItem(category))
        self._table.setItem(row, 1, QTableWidgetItem(name))
        self._table.setItem(row, 2, QTableWidgetItem(version))
        self._table.setItem(row, 3, QTableWidgetItem(evidence))

    def set_headers(self, headers: dict) -> None:
        lines = []
        for k, v in headers.items():
            lines.append(f"  {k}: {v}")
        self._header_text.setPlainText("\n".join(lines))

    def clear_results(self) -> None:
        self._table.setRowCount(0)
        self._header_text.clear()

    def _emit_execute(self) -> None:
        self.execute_requested.emit(self.get_params())


@register_tool
class FingerprintTool(BaseTool):
    """Web 技术栈指纹识别工具"""

    meta = ToolMeta(
        name="tech_fingerprint",
        display_name="技术指纹识别",
        category=ToolCategory.INFO_GATHERING,
        description="识别网站使用的技术栈：Web 服务器、CMS、框架、CDN、JS 库等",
        icon="🔬",
        version="1.0.0",
        keywords=["指纹", "fingerprint", "wappalyzer", "技术栈", "识别", "CMS"],
    )

    def __init__(self) -> None:
        super().__init__()
        self._widget: Optional[FingerprintToolWidget] = None

    def create_widget(self) -> QWidget:
        self._widget = FingerprintToolWidget()
        self._widget.execute_requested.connect(self._on_widget_execute)
        return self._widget

    def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        url = params["url"]
        self.output_ready.emit(f"🔬 正在分析: {url}")

        try:
            resp = requests.get(
                url,
                timeout=15,
                allow_redirects=True,
                verify=False,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/125.0.0.0 Safari/537.36"
                    )
                },
            )
        except requests.exceptions.SSLError:
            # 尝试忽略 SSL 错误
            import urllib3
            urllib3.disable_warnings()
            resp = requests.get(
                url,
                timeout=15,
                allow_redirects=True,
                verify=False,
                headers={"User-Agent": "Mozilla/5.0 ..."},
            )
        except Exception as e:
            self.output_ready.emit(f"[错误] 请求失败: {e}")
            return {"status": "error", "message": str(e)}

        headers = resp.headers
        html = resp.text.lower()
        status_code = resp.status_code

        # 显示响应头
        if self._widget:
            self._widget.set_headers(dict(headers))
            self._widget.clear_results()

        self.output_ready.emit(f"HTTP {status_code} - {len(html)} 字节")
        self.progress_updated.emit(20)

        # 收集所有匹配
        findings: dict[str, list[dict]] = {}

        for category, signatures in TECH_SIGNATURES.items():
            cat_findings: list[dict] = []
            for name, match_type, pattern, icon in signatures:
                version = ""
                evidence = ""

                if match_type == "header:Server":
                    val = headers.get("Server", "")
                    m = re.search(pattern, val, re.IGNORECASE)
                    if m:
                        version = m.group(1) if m.lastindex and m.lastindex >= 1 else ""
                        evidence = f"Server: {val}"
                elif match_type == "header:X-Powered-By":
                    val = headers.get("X-Powered-By", "")
                    m = re.search(pattern, val, re.IGNORECASE)
                    if m:
                        version = m.group(1) if m.lastindex and m.lastindex >= 1 else ""
                        evidence = f"X-Powered-By: {val}"
                elif match_type.startswith("header:"):
                    header_name = match_type.split(":", 1)[1]
                    val = headers.get(header_name, "")
                    m = re.search(pattern, val, re.IGNORECASE)
                    if m:
                        version = m.group(1) if m.lastindex and m.lastindex >= 1 else "" if m.groups() else ""
                        evidence = f"{header_name}: {val[:80]}"
                elif match_type == "cookie":
                    cookie_headers = headers.get("Set-Cookie", "")
                    m = re.search(pattern, cookie_headers, re.IGNORECASE)
                    if m:
                        evidence = f"Cookie: {cookie_headers[:80]}"
                elif match_type == "meta:html":
                    m = re.search(pattern, html, re.IGNORECASE)
                    if m:
                        version = m.group(1) if m.lastindex and m.lastindex >= 1 else "" if m.groups() else ""
                        evidence = f"HTML 匹配: {m.group(0)[:80]}"
                elif match_type == "script:html":
                    m = re.search(pattern, html, re.IGNORECASE)
                    if m:
                        version = m.group(1) if m.lastindex and m.lastindex >= 1 else "" if m.groups() else ""
                        evidence = f"Script 匹配: {m.group(0)[:80]}"
                elif match_type == "ssl:issuer":
                    pass  # SSL 信息需要额外请求，简化处理

                if evidence or m:
                    cat_findings.append({
                        "name": name,
                        "icon": icon,
                        "version": version,
                        "evidence": evidence,
                    })
                    self.output_ready.emit(
                        f"  ✓ [{category}] {icon} {name} {version}"
                    )

            if cat_findings:
                findings[category] = cat_findings

        # 填充表格
        if self._widget:
            for category, items in findings.items():
                for item in items:
                    self._widget.add_result(
                        category,
                        f"{item['icon']} {item['name']}",
                        item["version"],
                        item["evidence"],
                    )

        self.progress_updated.emit(100)

        total = sum(len(v) for v in findings.values())
        self.output_ready.emit(
            f"✓ 识别完成: 共发现 {total} 项技术，覆盖 {len(findings)} 个类别"
        )

        return {
            "url": url,
            "status_code": status_code,
            "findings": findings,
        }

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        errors = []
        url = params.get("url", "").strip()
        if not url:
            errors.append("请输入目标 URL")
        return errors

    def _on_widget_execute(self, params: dict) -> None:
        if self._widget:
            self._widget.clear_results()
        self.execute(params)


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


def _btn_primary_style() -> str:
    return """
        QPushButton {
            background-color: #cba6f7; color: #1e1e2e;
            border: none; border-radius: 6px;
            padding: 10px 24px; font-size: 13px; font-weight: bold;
        }
        QPushButton:hover { background-color: #b4befe; }
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
