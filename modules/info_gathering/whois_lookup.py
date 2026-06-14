"""
WHOIS 查询工具 — 查询域名/IP 的注册信息。

特性:
  - 使用 python-whois 库查询
  - 备选方案：直接 socket 连接 WHOIS 服务器
  - 支持域名和 IP 地址
  - 结果格式化展示
  - 支持复制结果
"""

from __future__ import annotations

import re
import socket
from typing import Any, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.tool_base import BaseTool, ToolCategory, ToolMeta
from core.tool_registry import register_tool

# WHOIS 服务器映射
WHOIS_SERVERS: dict[str, str] = {
    "com": "whois.verisign-grs.com",
    "net": "whois.verisign-grs.com",
    "org": "whois.pir.org",
    "cn": "whois.cnnic.cn",
    "com.cn": "whois.cnnic.cn",
    "io": "whois.nic.io",
    "dev": "whois.nic.google",
    "app": "whois.nic.google",
}

DEFAULT_WHOIS = "whois.iana.org"


class WhoisToolWidget(QWidget):
    """WHOIS 查询工具 UI"""

    execute_requested = pyqtSignal(dict)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ---- 输入区 ----
        input_group = QGroupBox("查询目标")
        input_group.setStyleSheet(self._group_style())
        input_layout = QGridLayout(input_group)
        input_layout.setSpacing(8)

        # 目标输入
        target_label = QLabel("域名/IP:")
        target_label.setStyleSheet("color: #cdd6f4; font-size: 13px;")
        self._target_input = QLineEdit()
        self._target_input.setPlaceholderText("例如: example.com 或 1.1.1.1")
        self._target_input.setStyleSheet(self._input_style())
        self._target_input.returnPressed.connect(self._on_execute)
        input_layout.addWidget(target_label, 0, 0)
        input_layout.addWidget(self._target_input, 0, 1)

        # WHOIS 服务器选择
        server_label = QLabel("WHOIS 服务器:")
        server_label.setStyleSheet("color: #cdd6f4; font-size: 13px;")
        self._server_combo = QComboBox()
        self._server_combo.setEditable(True)
        self._server_combo.addItem("自动检测", "")
        for tld, server in WHOIS_SERVERS.items():
            self._server_combo.addItem(f"{tld} → {server}", server)
        self._server_combo.setStyleSheet(self._combo_style())
        input_layout.addWidget(server_label, 1, 0)
        input_layout.addWidget(self._server_combo, 1, 1)

        layout.addWidget(input_group)

        # ---- 结果区 ----
        result_group = QGroupBox("查询结果")
        result_group.setStyleSheet(self._group_style())
        result_layout = QVBoxLayout(result_group)

        self._result_text = QTextEdit()
        self._result_text.setReadOnly(True)
        self._result_text.setStyleSheet("""
            QTextEdit {
                background-color: #11111b;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 12px;
                font-family: "Cascadia Code", "Consolas", "Microsoft YaHei Mono", monospace;
                font-size: 12px;
                min-height: 300px;
            }
        """)
        result_layout.addWidget(self._result_text)

        # 复制按钮
        copy_btn = QPushButton("📋 复制结果")
        copy_btn.setStyleSheet(self._btn_secondary_style())
        copy_btn.clicked.connect(self._copy_result)
        result_layout.addWidget(copy_btn)

        layout.addWidget(result_group, stretch=1)

    def get_params(self) -> dict:
        target = self._target_input.text().strip()
        server = self._server_combo.currentData()
        return {"target": target, "server": server if server else None}

    def set_result(self, text: str) -> None:
        self._result_text.setPlainText(text)

    def append_result(self, text: str) -> None:
        self._result_text.append(text)

    # ---- 内部 ----

    def _on_execute(self) -> None:
        target = self._target_input.text().strip()
        if target:
            self.execute_requested.emit(self.get_params())

    def _copy_result(self) -> None:
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(self._result_text.toPlainText())

    # ---- 样式 ----

    @staticmethod
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

    @staticmethod
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

    @staticmethod
    def _combo_style() -> str:
        return """
            QComboBox {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 10px 12px;
                font-size: 13px;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #1e1e2e;
                color: #cdd6f4;
                selection-background-color: #45475a;
                border: 1px solid #313244;
            }
        """

    @staticmethod
    def _btn_secondary_style() -> str:
        return """
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #45475a;
            }
        """


@register_tool
class WhoisLookupTool(BaseTool):
    """WHOIS 查询工具"""

    meta = ToolMeta(
        name="whois_lookup",
        display_name="WHOIS 查询",
        category=ToolCategory.INFO_GATHERING,
        description="查询域名/IP 的 WHOIS 注册信息，包括注册商、注册日期、DNS 等",
        icon="🌐",
        version="1.0.0",
        keywords=["whois", "域名", "信息收集", "domain", "注册信息"],
    )

    def __init__(self) -> None:
        super().__init__()
        self._widget: Optional[WhoisToolWidget] = None

    def create_widget(self) -> QWidget:
        self._widget = WhoisToolWidget()
        self._widget.execute_requested.connect(self._on_widget_execute)
        return self._widget

    def execute(self, params: dict[str, Any]) -> str:
        target = params.get("target", "").strip()
        server = params.get("server")

        if not target:
            self.output_ready.emit("[错误] 请输入域名或 IP 地址")
            return ""

        self.output_ready.emit(f"🔍 正在查询: {target}")
        self.progress_updated.emit(10)

        result = ""
        try:
            # 方案1: 尝试 python-whois
            try:
                import whois
                self.output_ready.emit("使用 python-whois 库查询...")
                w = whois.whois(target)
                result = self._format_whois_result(w, target)
                self.output_ready.emit("✓ python-whois 查询成功")
            except ImportError:
                self.output_ready.emit("python-whois 未安装，使用 socket 直接查询...")
                result = self._whois_socket(target, server)
            except Exception as e:
                self.output_ready.emit(f"python-whois 查询失败: {e}")
                self.output_ready.emit("回退到 socket 直接查询...")
                result = self._whois_socket(target, server)

            if self._widget:
                self._widget.set_result(result)

            self.progress_updated.emit(100)
            self.output_ready.emit("✓ 查询完成")

        except Exception as e:
            self.output_ready.emit(f"[错误] 查询失败: {e}")
            result = f"查询失败: {e}"

        return result

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        errors = []
        target = params.get("target", "").strip()
        if not target:
            errors.append("请输入域名或 IP 地址")
        elif not self._is_valid_target(target):
            errors.append(f"无效的域名或 IP 格式: {target}")
        return errors

    # ---- 内部方法 ----

    def _on_widget_execute(self, params: dict) -> None:
        """Widget 发出执行请求"""
        self.execute(params)

    @staticmethod
    def _is_valid_target(target: str) -> bool:
        """简单验证域名或 IP 格式"""
        # IP 格式
        ip_pattern = r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
        if re.match(ip_pattern, target):
            return True
        # 域名格式
        domain_pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$"
        return bool(re.match(domain_pattern, target))

    def _format_whois_result(self, w, target: str) -> str:
        """格式化 python-whois 结果"""
        lines = []
        lines.append(f"{'=' * 60}")
        lines.append(f"WHOIS 查询结果: {target}")
        lines.append(f"{'=' * 60}")
        lines.append("")

        field_map = {
            "domain_name": "域名",
            "registrar": "注册商",
            "whois_server": "WHOIS 服务器",
            "creation_date": "创建日期",
            "expiration_date": "过期日期",
            "updated_date": "更新日期",
            "name_servers": "DNS 服务器",
            "status": "状态",
            "emails": "联系邮箱",
            "dnssec": "DNSSEC",
            "name": "注册人",
            "org": "组织",
            "address": "地址",
            "city": "城市",
            "state": "省份",
            "country": "国家",
            "registrant_postal_code": "邮编",
            "registrant_phone": "电话",
        }

        for attr, label in field_map.items():
            val = getattr(w, attr, None)
            if val is not None and val != "" and val != []:
                if isinstance(val, list):
                    if len(val) == 1:
                        val_str = str(val[0])
                    else:
                        val_str = ", ".join(str(v) for v in val)
                else:
                    val_str = str(val)
                lines.append(f"  {label:　<12s}: {val_str}")

        # 原始文本（截取前 2000 字符）
        if w.text:
            lines.append("")
            lines.append("-" * 60)
            lines.append("原始 WHOIS 响应（部分）:")
            lines.append("-" * 60)
            lines.append(w.text[:2000])

        return "\n".join(lines)

    def _whois_socket(self, target: str, server: Optional[str] = None) -> str:
        """使用 socket 直接查询 WHOIS（不依赖第三方库）"""
        # 确定 WHOIS 服务器
        if not server:
            # 根据 TLD 选择服务器
            parts = target.split(".")
            if len(parts) >= 2:
                tld = parts[-1].lower()
                # 检查二级 TLD (如 com.cn)
                if len(parts) >= 3 and f"{parts[-2]}.{tld}" in WHOIS_SERVERS:
                    server = WHOIS_SERVERS[f"{parts[-2]}.{tld}"]
                else:
                    server = WHOIS_SERVERS.get(tld, DEFAULT_WHOIS)
            else:
                server = DEFAULT_WHOIS

        self.output_ready.emit(f"连接到 WHOIS 服务器: {server}")

        result_lines = []
        result_lines.append(f"{'=' * 60}")
        result_lines.append(f"WHOIS 查询结果: {target}")
        result_lines.append(f"WHOIS 服务器: {server}")
        result_lines.append(f"{'=' * 60}")
        result_lines.append("")

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((server, 43))
            sock.send(f"{target}\r\n".encode())

            data = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                data += chunk
            sock.close()

            raw = data.decode("utf-8", errors="replace")
            result_lines.append(raw)

        except socket.timeout:
            result_lines.append("[错误] 连接 WHOIS 服务器超时")
        except socket.gaierror:
            result_lines.append(f"[错误] 无法解析服务器地址: {server}")
        except ConnectionRefusedError:
            result_lines.append(f"[错误] 连接被拒绝: {server}")
        except Exception as e:
            result_lines.append(f"[错误] {e}")

        return "\n".join(result_lines)
