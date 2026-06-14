"""
Writeup 助手 — 生成漏洞提交报告模板。

特性:
  - 支持漏洞盒子 / 补天等平台格式
  - 表单式填写
  - 一键生成 Markdown / HTML
  - 预填模板 + 常见字段
  - 导出到文件
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.tool_base import BaseTool, ToolCategory, ToolMeta
from core.tool_registry import register_tool

WRITEUP_TEMPLATES = {
    "漏洞盒子标准": """# 漏洞详情

## 基本信息
| 字段 | 内容 |
|------|------|
| 漏洞标题 | {title} |
| 漏洞类型 | {vuln_type} |
| 危害等级 | {severity} |
| 漏洞URL | {url} |
| 发现时间 | {date} |

## 漏洞描述
{description}

## 漏洞证明
{proof}

### 复现步骤
{steps}

## 漏洞危害
{impact}

## 修复建议
{fix}

## 参考资料
{references}
""",
    "补天平台": """## 基本信息
- **漏洞名称**: {title}
- **漏洞类型**: {vuln_type}
- **漏洞等级**: {severity}
- **影响域名**: {url}
- **发现日期**: {date}

## 漏洞描述
{description}

## 漏洞详情
{proof}

## 复现步骤
{steps}

## 修复方案
{fix}
""",
    "通用报告": """# {title}

**类型**: {vuln_type} | **等级**: {severity} | **日期**: {date}

## 摘要
{description}

## 影响范围
- **URL**: {url}

## 技术细节
{proof}

### 复现步骤
{steps}

## 业务影响
{impact}

## 修复建议
{fix}

---
*报告由 SecTools Platform 生成*
""",
}


class WriteupWidget(QWidget):
    """Writeup 助手 UI"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ---- 模板选择 ----
        tpl_row = QHBoxLayout()
        tpl_row.addWidget(QLabel("模板:"))
        self._tpl_combo = QComboBox()
        self._tpl_combo.addItems(list(WRITEUP_TEMPLATES.keys()))
        self._tpl_combo.setStyleSheet(_combo_style())
        tpl_row.addWidget(self._tpl_combo, stretch=1)
        layout.addLayout(tpl_row)

        # ---- 表单 ----
        form_group = QGroupBox("漏洞信息")
        form_group.setStyleSheet(_group_style())
        fl = QGridLayout(form_group)
        fl.setSpacing(8)

        fields = [
            ("漏洞标题:", "title", "示例: XX 系统 SQL 注入漏洞"),
            ("漏洞类型:", "vuln_type", "示例: SQL 注入 / XSS / SSRF / 文件上传..."),
            ("危害等级:", "severity", "示例: 严重 / 高危 / 中危 / 低危"),
            ("漏洞 URL:", "url", "示例: https://target.com/page?id=1"),
            ("漏洞描述:", "description", "描述漏洞的成因和影响"),
            ("漏洞证明:", "proof", "具体的 Payload / 截图 / 请求响应"),
            ("复现步骤:", "steps", "1. 访问 xxx\n2. 输入 xxx\n3. 提交查看结果"),
            ("漏洞危害:", "impact", "漏洞可能造成的业务影响"),
            ("修复建议:", "fix", "具体的修复方案"),
            ("参考资料:", "references", "OWASP / CWE 编号或参考链接"),
        ]

        self._fields: dict[str, object] = {}
        for i, (label, key, placeholder) in enumerate(fields):
            fl.addWidget(QLabel(label), i, 0)
            if key in ("description", "proof", "steps", "impact", "fix", "references"):
                widget = QTextEdit()
                widget.setMaximumHeight(80)
                widget.setStyleSheet(_textarea_style())
                widget.setPlaceholderText(placeholder)
            else:
                widget = QLineEdit()
                widget.setStyleSheet(_input_style())
                widget.setPlaceholderText(placeholder)
            self._fields[key] = widget
            fl.addWidget(widget, i, 1)

        layout.addWidget(form_group)

        # ---- 操作 ----
        btn_row = QHBoxLayout()
        self._gen_btn = QPushButton("📝 生成报告")
        self._gen_btn.setStyleSheet(_btn_primary_style())
        self._gen_btn.clicked.connect(self._generate)
        btn_row.addWidget(self._gen_btn)

        self._export_btn = QPushButton("💾 导出文件")
        self._export_btn.setStyleSheet(_btn_accent_style())
        self._export_btn.clicked.connect(self._export)
        btn_row.addWidget(self._export_btn)

        self._copy_btn = QPushButton("📋 复制")
        self._copy_btn.setStyleSheet(_btn_secondary_style())
        self._copy_btn.clicked.connect(self._copy)
        btn_row.addWidget(self._copy_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # ---- 输出 ----
        output_group = QGroupBox("生成的报告")
        output_group.setStyleSheet(_group_style())
        ol = QVBoxLayout(output_group)
        self._output_edit = QTextEdit()
        self._output_edit.setReadOnly(True)
        self._output_edit.setStyleSheet(_textarea_style())
        ol.addWidget(self._output_edit)
        layout.addWidget(output_group, stretch=1)

    def _get_values(self) -> dict:
        vals = {}
        for key, widget in self._fields.items():
            if isinstance(widget, QTextEdit):
                vals[key] = widget.toPlainText().strip()
            else:
                vals[key] = widget.text().strip()
        vals["date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        return vals

    def _generate(self) -> None:
        vals = self._get_values()
        tpl_name = self._tpl_combo.currentText()
        tpl = WRITEUP_TEMPLATES.get(tpl_name, "")
        report = tpl.format(**vals)
        self._output_edit.setPlainText(report)

    def _export(self) -> None:
        content = self._output_edit.toPlainText()
        if not content:
            self._generate()
            content = self._output_edit.toPlainText()
        filepath, _ = QFileDialog.getSaveFileName(
            self, "导出报告", "writeup.md", "Markdown (*.md);;HTML (*.html)"
        )
        if filepath:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

    def _copy(self) -> None:
        if not self._output_edit.toPlainText():
            self._generate()
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(self._output_edit.toPlainText())


@register_tool
class WriteupHelperTool(BaseTool):
    """Writeup 助手"""

    meta = ToolMeta(
        name="writeup_helper",
        display_name="Writeup 助手",
        category=ToolCategory.LEARNING,
        description="漏洞报告模板生成，支持漏洞盒子/补天平台格式，一键导出",
        icon="📝",
        version="1.0.0",
        keywords=["writeup", "报告", "漏洞盒子", "补天", "提交", "模板"],
    )

    def __init__(self) -> None:
        super().__init__()
        self._widget: Optional[WriteupWidget] = None

    def create_widget(self) -> QWidget:
        self._widget = WriteupWidget()
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


def _combo_style() -> str:
    return """
        QComboBox { background-color: #313244; color: #cdd6f4;
            border: 1px solid #45475a; border-radius: 6px;
            padding: 8px 12px; font-size: 13px; }
    """


def _input_style() -> str:
    return """
        QLineEdit { background-color: #313244; color: #cdd6f4;
            border: 1px solid #45475a; border-radius: 6px;
            padding: 8px 12px; font-size: 13px; }
    """


def _textarea_style() -> str:
    return """
        QTextEdit { background-color: #11111b; color: #cdd6f4;
            border: 1px solid #313244; border-radius: 6px;
            padding: 8px; font-family: Consolas, monospace; font-size: 12px; }
    """


def _btn_primary_style() -> str:
    return """
        QPushButton { background-color: #cba6f7; color: #1e1e2e;
            border: none; border-radius: 6px;
            padding: 10px 24px; font-size: 13px; font-weight: bold; }
        QPushButton:hover { background-color: #b4befe; }
    """


def _btn_accent_style() -> str:
    return """
        QPushButton { background-color: #94e2d5; color: #1e1e2e;
            border: none; border-radius: 6px;
            padding: 10px 24px; font-size: 13px; font-weight: bold; }
        QPushButton:hover { background-color: #89dceb; }
    """


def _btn_secondary_style() -> str:
    return """
        QPushButton { background-color: #313244; color: #cdd6f4;
            border: 1px solid #45475a; border-radius: 6px;
            padding: 10px 24px; font-size: 13px; }
        QPushButton:hover { background-color: #45475a; }
    """
