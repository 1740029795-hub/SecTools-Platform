"""
漏洞检查清单 — Web 安全测试检查清单，按分类组织。

特性:
  - 按 OWASP 分类组织
  - 可勾选/取消勾选
  - 进度追踪
  - 导出为 Markdown
  - 导入/重置
"""

from __future__ import annotations

from typing import Any, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.tool_base import BaseTool, ToolCategory, ToolMeta
from core.tool_registry import register_tool

CHECKLIST = {
    "信息收集": [
        "WHOIS 查询目标域名",
        "DNS 记录枚举 (A/MX/NS/TXT)",
        "子域名枚举",
        "端口扫描 (全端口/Top 1000)",
        "技术栈指纹识别",
        "爬取 robots.txt / sitemap.xml",
        "Google Hacking / GitHub 搜索",
        "证书透明度日志查询 (crt.sh)",
        "Shodan / Censys / Fofa 搜索",
        "历史 DNS 记录查询",
    ],
    "身份验证": [
        "弱密码测试 (admin/admin)",
        "用户名枚举",
        "暴力破解防护测试",
        "密码重置功能测试",
        "记住我功能测试",
        "多因素认证绕过测试",
        "会话固定测试",
        "JWT Token 安全性检查",
        "OAuth 配置检查",
        "验证码绕过测试",
    ],
    "访问控制": [
        "目录/文件越权访问",
        "水平越权 (IDOR)",
        "垂直越权 (普通→管理员)",
        "API 端点权限检查",
        "CORS 配置检查",
        "直接对象引用 (IDOR)",
        "路径遍历 (../../etc/passwd)",
        "强制浏览隐藏页面",
        "用户角色切换测试",
    ],
    "注入攻击": [
        "SQL 注入 (GET/POST/Cookie/Header)",
        "NoSQL 注入 (MongoDB)",
        "命令注入 (OS Command)",
        "LDAP 注入",
        "XPath 注入",
        "模板注入 (SSTI)",
        "表达式语言注入 (EL/OGNL)",
        "XXE (XML 外部实体注入)",
        "SSI (Server-Side Includes)",
    ],
    "跨站攻击": [
        "反射型 XSS",
        "存储型 XSS",
        "DOM 型 XSS",
        "CSRF (跨站请求伪造)",
        "点击劫持 (X-Frame-Options)",
        "CORS 跨域配置",
        "WebSocket 跨站",
        "PostMessage 跨域通信",
    ],
    "文件上传": [
        "文件扩展名绕过",
        "Content-Type 绕过",
        "图片马 (Image Shell)",
        ".htaccess 覆盖",
        "ZIP 炸弹 / 解压穿越",
        "SVG XSS 上传",
        "文件大小限制绕过",
        "并发上传竞争条件",
    ],
    "逻辑漏洞": [
        "支付流程篡改（金额/数量）",
        "优惠券/积分超额使用",
        "竞态条件 (Race Condition)",
        "业务流程跳过步骤",
        "投票/点赞刷量",
        "验证码绕过/重放",
        "手机/邮箱验证绕过",
        "邀请码/注册码逻辑",
    ],
    "配置安全": [
        "HTTP 安全头检查 (HSTS/CSP/X-Frame)",
        "Cookie 属性 (HttpOnly/Secure/SameSite)",
        "HTTPS 强制跳转",
        "敏感信息泄露 (错误页面)",
        "默认凭据/管理后台",
        "目录列表 (Directory Listing)",
        "调试模式/端点暴露",
        "TLS/SSL 配置检查",
    ],
}


class ChecklistWidget(QWidget):
    """检查清单 UI"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._checkboxes: dict[str, list[QCheckBox]] = {}
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # ---- 操作栏 ----
        top_row = QHBoxLayout()
        self._export_btn = QPushButton("📄 导出 Markdown")
        self._export_btn.setStyleSheet(_btn_accent_style())
        self._export_btn.clicked.connect(self._export)
        top_row.addWidget(self._export_btn)

        self._reset_btn = QPushButton("🔄 全部重置")
        self._reset_btn.setStyleSheet(_btn_secondary_style())
        self._reset_btn.clicked.connect(self._reset_all)
        top_row.addWidget(self._reset_btn)
        top_row.addStretch()

        self._progress = QProgressBar()
        self._progress.setMaximumWidth(300)
        self._progress.setStyleSheet("""
            QProgressBar { background-color: #313244; border: 1px solid #45475a;
                border-radius: 4px; text-align: center; color: #cdd6f4; height: 20px; }
            QProgressBar::chunk { background-color: #a6e3a1; border-radius: 3px; }
        """)
        top_row.addWidget(self._progress)
        layout.addLayout(top_row)

        # ---- 滚动区 ----
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setSpacing(16)

        for cat, items in CHECKLIST.items():
            group = QGroupBox(cat)
            group.setStyleSheet(_group_style())
            gl = QVBoxLayout(group)
            cbs = []
            for item in items:
                cb = QCheckBox(item)
                cb.setStyleSheet("color: #cdd6f4; font-size: 13px; padding: 2px 0;")
                cb.toggled.connect(self._update_progress)
                gl.addWidget(cb)
                cbs.append(cb)
            self._checkboxes[cat] = cbs
            cl.addWidget(group)

        cl.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def get_checked(self) -> dict[str, list[str]]:
        result = {}
        for cat, cbs in self._checkboxes.items():
            checked = [cb.text() for cb in cbs if cb.isChecked()]
            if checked:
                result[cat] = checked
        return result

    def _update_progress(self) -> None:
        total = sum(len(cbs) for cbs in self._checkboxes.values())
        checked = sum(
            sum(1 for cb in cbs if cb.isChecked())
            for cbs in self._checkboxes.values()
        )
        self._progress.setValue(int(checked / total * 100))
        self._progress.setFormat(f"{checked}/{total} ({int(checked/total*100)}%)")

    def _reset_all(self) -> None:
        for cbs in self._checkboxes.values():
            for cb in cbs:
                cb.setChecked(False)

    def _export(self) -> None:
        from PyQt6.QtWidgets import QApplication
        checked = self.get_checked()
        md = "# 漏洞测试检查清单\n\n"
        md += f"## 完成情况\n\n"
        total = sum(len(cbs) for cbs in self._checkboxes.values())
        done = sum(
            sum(1 for cb in cbs if cb.isChecked())
            for cbs in self._checkboxes.values()
        )
        md += f"- 总体: {done}/{total} ({int(done/total*100)}%)\n\n"

        for cat in CHECKLIST:
            items = checked.get(cat, [])
            md += f"## {cat} ({len(items)} 项)\n\n"
            for item in items:
                md += f"- [x] {item}\n"
            for item in CHECKLIST[cat]:
                if item not in items:
                    md += f"- [ ] {item}\n"
            md += "\n"

        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出检查清单", "checklist.md", "Markdown (*.md)"
        )
        if filepath:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(md)


@register_tool
class ChecklistTool(BaseTool):
    """漏洞检查清单"""

    meta = ToolMeta(
        name="checklist",
        display_name="漏洞检查清单",
        category=ToolCategory.LEARNING,
        description="Web 安全测试检查清单，按 OWASP 分类组织，支持进度追踪和导出",
        icon="✅",
        version="1.0.0",
        keywords=["检查清单", "checklist", "测试", "web安全", "规范"],
    )

    def __init__(self) -> None:
        super().__init__()
        self._widget: Optional[ChecklistWidget] = None

    def create_widget(self) -> QWidget:
        self._widget = ChecklistWidget()
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


def _btn_accent_style() -> str:
    return """
        QPushButton { background-color: #a6e3a1; color: #1e1e2e;
            border: none; border-radius: 6px;
            padding: 8px 16px; font-size: 12px; font-weight: bold; }
        QPushButton:hover { background-color: #94e2d5; }
    """


def _btn_secondary_style() -> str:
    return """
        QPushButton { background-color: #313244; color: #cdd6f4;
            border: 1px solid #45475a; border-radius: 6px;
            padding: 8px 16px; font-size: 12px; }
        QPushButton:hover { background-color: #45475a; }
    """
