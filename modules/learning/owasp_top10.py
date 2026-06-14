"""
OWASP Top 10 参考手册 — 中文版 Web 应用安全风险参考。

数据来源: OWASP Top 10:2021
"""

from __future__ import annotations

from typing import Any, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.tool_base import BaseTool, ToolCategory, ToolMeta
from core.tool_registry import register_tool

OWASP_DATA = [
    {
        "id": "A01:2021",
        "name": "访问控制失效",
        "en": "Broken Access Control",
        "risk": "🔴 严重",
        "summary": "访问控制强制实施用户只能在给定权限范围内操作的策略。当这些控制失效时，攻击者可以绕过身份验证、访问他人的账户、查看敏感文件、修改数据、更改权限等。",
        "examples": [
            "绕过 URL 路径限制 (/admin)",
            "越权访问 (IDOR)",
            "CORS 配置错误",
            "JWT Token 未验证",
        ],
        "prevention": [
            "默认拒绝所有请求",
            "实施基于角色的访问控制 (RBAC)",
            "强制记录访问日志",
            "定期审计权限模型",
        ],
    },
    {
        "id": "A02:2021",
        "name": "加密机制失效",
        "en": "Cryptographic Failures",
        "risk": "🔴 严重",
        "summary": "与加密相关的失效（或缺乏加密）通常导致敏感数据泄露。包括使用弱加密算法、明文传输、不安全的密钥管理等。",
        "examples": [
            "明文传输密码",
            "使用 MD5/SHA1 存储密码",
            "未使用 HTTPS",
            "硬编码密钥/Token",
        ],
        "prevention": [
            "使用 TLS 1.3 加密传输",
            "密码使用 bcrypt/scrypt/Argon2 哈希",
            "密钥使用密钥管理服务 (KMS)",
            "禁用过时的加密算法",
        ],
    },
    {
        "id": "A03:2021",
        "name": "注入攻击",
        "en": "Injection",
        "risk": "🔴 严重",
        "summary": "当用户提供的数据被解释为代码或命令时发生注入。SQL、NoSQL、OS 命令、LDAP、XPath 等均可被注入利用。攻击者可获取数据、篡改记录甚至获取服务器控制权。",
        "examples": [
            "SQL 注入: ' OR 1=1 --",
            "命令注入: ; cat /etc/passwd",
            "XPath 注入",
            "模板注入 (SSTI)",
        ],
        "prevention": [
            "使用参数化查询 (PreparedStatement)",
            "使用 ORM 框架",
            "输入验证 + 白名单过滤",
            "最小权限原则运行数据库账户",
        ],
    },
    {
        "id": "A04:2021",
        "name": "不安全的设计",
        "en": "Insecure Design",
        "risk": "🟡 高危",
        "summary": "不安全的设计是一个广泛的类别，代表与设计和架构缺陷相关的风险。需要在软件开发生命周期早期引入安全设计模式、威胁建模和安全编码实践。",
        "examples": [
            "缺少速率限制（暴力破解）",
            "无验证码的登录表单",
            "用户可猜测的密码重置令牌",
            "过度暴露的错误信息",
        ],
        "prevention": [
            "建立安全开发生命周期 (SDL)",
            "使用威胁建模 (STRIDE)",
            "限制资源消耗 (速率限制)",
            "安全需求与用户故事集成",
        ],
    },
    {
        "id": "A05:2021",
        "name": "安全配置错误",
        "en": "Security Misconfiguration",
        "risk": "🟡 高危",
        "summary": "安全配置错误是最常见的漏洞之一。包括默认账户/密码、不必要的功能开启、过于详细的错误信息、未打补丁的组件、未加固的云服务等。",
        "examples": [
            "默认管理员密码未修改",
            "目录列表开启",
            "详细错误堆栈暴露",
            "不必要的 HTTP 方法 (PUT/DELETE)",
        ],
        "prevention": [
            "自动化加固流程",
            "最小化平台（移除不必要的功能）",
            "定期审查和修补",
            "使用安全基线配置模板",
        ],
    },
    {
        "id": "A06:2021",
        "name": "易受攻击和过时的组件",
        "en": "Vulnerable and Outdated Components",
        "risk": "🟡 高危",
        "summary": "使用存在已知漏洞的组件（库、框架、依赖）。此类漏洞利用门槛极低，攻击者可通过自动化工具发现并利用。",
        "examples": [
            "Log4Shell (CVE-2021-44228)",
            "Struts2 远程代码执行",
            "过时的 jQuery 版本有 XSS 漏洞",
            "未更新的 WordPress 插件",
        ],
        "prevention": [
            "定期扫描依赖项漏洞 (SCA)",
            "使用 npm audit / pip audit / OWASP Dependency-Check",
            "订阅安全公告",
            "及时更新和打补丁",
        ],
    },
    {
        "id": "A07:2021",
        "name": "身份识别和身份验证失效",
        "en": "Identification and Authentication Failures",
        "risk": "🔴 严重",
        "summary": "应用程序在身份验证和会话管理方面的实现缺陷。攻击者可以借助这些漏洞冒充其他用户。",
        "examples": [
            "弱密码策略",
            "会话固定攻击",
            "Token 泄露在 URL 中",
            "缺少多因素认证 (MFA)",
        ],
        "prevention": [
            "实施多因素认证 (MFA)",
            "使用安全的会话管理",
            "限制登录尝试次数",
            "密码强度检测",
        ],
    },
    {
        "id": "A08:2021",
        "name": "软件和数据完整性失效",
        "en": "Software and Data Integrity Failures",
        "risk": "🟡 高危",
        "summary": "软件更新、关键数据和 CI/CD 流水线未验证完整性。不安全的反序列化也归入此类别。攻击者可利用反序列化漏洞实现远程代码执行。",
        "examples": [
            "不安全的反序列化 (Python pickle)",
            "未签名的固件更新",
            "npm 包供应链攻击",
            "CI/CD 管道中的恶意代码注入",
        ],
        "prevention": [
            "使用数字签名验证软件和数据",
            "避免接收不可信来源的序列化对象",
            "使用软件供应链安全工具",
            "确保 CI/CD 流水线安全",
        ],
    },
    {
        "id": "A09:2021",
        "name": "安全日志记录和监控失效",
        "en": "Security Logging and Monitoring Failures",
        "risk": "🟡 高危",
        "summary": "没有日志记录和监控无法检测到安全事件。攻击者依赖监控不足来实现其目标而不被发现。平均检测时间超过 200 天。",
        "examples": [
            "未记录登录失败",
            "审计日志存储在可写位置",
            "无实时告警",
            "日志不含足够的上下文信息",
        ],
        "prevention": [
            "记录所有登录、访问控制、输入验证失败",
            "确保日志格式统一便于分析",
            "建立实时告警机制",
            "日志存储完整性保护",
        ],
    },
    {
        "id": "A10:2021",
        "name": "服务器端请求伪造 (SSRF)",
        "en": "Server-Side Request Forgery (SSRF)",
        "risk": "🟡 高危",
        "summary": "SSRF 漏洞允许攻击者诱导服务器端应用向非预期的地址发出请求。常用于攻击内部系统、云元数据服务等。",
        "examples": [
            "访问 AWS 169.254.169.254 元数据",
            "代理内部服务端口扫描",
            "file:///etc/passwd 文件读取",
            "Redis/MySQL 未授权访问",
        ],
        "prevention": [
            "白名单验证远程资源地址",
            "禁用不必要的 URL schema (file://, gopher://)",
            "内网地址黑名单",
            "使用独立的网络出口",
        ],
    },
]


class OwaspWidget(QWidget):
    """OWASP Top 10 参考 UI"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧列表
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.addWidget(QLabel("OWASP Top 10:2021"))
        self._list = QListWidget()
        self._list.setStyleSheet(_list_style())
        for item in OWASP_DATA:
            list_item = QListWidgetItem(f"{item['id']}  {item['name']}")
            list_item.setData(Qt.ItemDataRole.UserRole, item["id"])
            self._list.addItem(list_item)
        self._list.currentRowChanged.connect(self._on_select)
        ll.addWidget(self._list)
        splitter.addWidget(left)

        # 右侧详情
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(8, 0, 0, 0)

        self._title_label = QLabel("")
        self._title_label.setStyleSheet("color: #cdd6f4; font-size: 20px; font-weight: bold; padding: 8px 0;")
        rl.addWidget(self._title_label)

        self._risk_label = QLabel("")
        self._risk_label.setStyleSheet("font-size: 14px; padding: 4px 0;")
        rl.addWidget(self._risk_label)

        rl.addWidget(QLabel("📖 概述:"))
        self._summary_edit = QTextEdit()
        self._summary_edit.setReadOnly(True)
        self._summary_edit.setMaximumHeight(100)
        self._summary_edit.setStyleSheet(_text_style())
        rl.addWidget(self._summary_edit)

        rl.addWidget(QLabel("🔍 示例:"))
        self._example_edit = QTextEdit()
        self._example_edit.setReadOnly(True)
        self._example_edit.setStyleSheet(_text_style())
        rl.addWidget(self._example_edit)

        rl.addWidget(QLabel("🛡️ 防护建议:"))
        self._prevention_edit = QTextEdit()
        self._prevention_edit.setReadOnly(True)
        self._prevention_edit.setStyleSheet(_text_style())
        rl.addWidget(self._prevention_edit)

        splitter.addWidget(right)
        splitter.setSizes([300, 700])
        layout.addWidget(splitter)

        self._list.setCurrentRow(0)

    def _on_select(self, idx: int) -> None:
        if idx < 0 or idx >= len(OWASP_DATA):
            return
        d = OWASP_DATA[idx]
        self._title_label.setText(f"{d['id']}: {d['name']} ({d['en']})")
        self._risk_label.setText(f"风险等级: {d['risk']}")
        self._summary_edit.setPlainText(d["summary"])
        self._example_edit.setPlainText("\n".join(f"• {e}" for e in d["examples"]))
        self._prevention_edit.setPlainText("\n".join(f"• {p}" for p in d["prevention"]))


@register_tool
class OwaspTop10Tool(BaseTool):
    """OWASP Top 10 参考"""

    meta = ToolMeta(
        name="owasp_top10",
        display_name="OWASP Top 10",
        category=ToolCategory.LEARNING,
        description="OWASP Top 10:2021 中文参考手册，含漏洞描述、示例和防护建议",
        icon="📘",
        version="1.0.0",
        keywords=["owasp", "top10", "参考", "学习", "web安全"],
    )

    def __init__(self) -> None:
        super().__init__()
        self._widget: Optional[OwaspWidget] = None

    def create_widget(self) -> QWidget:
        self._widget = OwaspWidget()
        return self._widget

    def execute(self, params: dict[str, Any]) -> Any:
        return None

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        return []


def _list_style() -> str:
    return """
        QListWidget { background-color: #11111b; color: #cdd6f4;
            border: 1px solid #313244; border-radius: 6px;
            font-size: 13px; }
        QListWidget::item { padding: 10px 12px; border-bottom: 1px solid #313244; }
        QListWidget::item:hover { background-color: #313244; }
        QListWidget::item:selected { background-color: #45475a; border-left: 3px solid #cba6f7; }
    """


def _text_style() -> str:
    return """
        QTextEdit { background-color: #11111b; color: #a6adc8;
            border: 1px solid #313244; border-radius: 6px;
            padding: 10px; font-size: 13px; line-height: 1.6; }
    """
