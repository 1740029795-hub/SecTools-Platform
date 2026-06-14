"""
JWT 调试器 — 解码、分析和安全测试 JWT Token。

特性:
  - JWT Header/Payload/Signature 三部分解码
  - 自动 Base64 解码 + JSON 美化
  - none 算法检测（alg:none 攻击检测）
  - 弱密钥提示
  - 时间戳可读化（iat/exp/nbf）
  - Token 过期检查
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from typing import Any, Optional

import jwt

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
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


class JwtToolWidget(QWidget):
    """JWT 调试器 UI"""

    execute_requested = pyqtSignal(dict)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ---- Token 输入 ----
        input_group = QGroupBox("JWT Token")
        input_group.setStyleSheet(_group_style())
        il = QVBoxLayout(input_group)
        self._token_input = QTextEdit()
        self._token_input.setPlaceholderText("粘贴 JWT Token (eyJhbGciOi...)...")
        self._token_input.setMaximumHeight(80)
        self._token_input.setStyleSheet(_input_style())
        il.addWidget(self._token_input)
        layout.addWidget(input_group)

        # ---- 按钮 ----
        btn_row = QHBoxLayout()
        self._decode_btn = QPushButton("🔍 解码分析")
        self._decode_btn.setStyleSheet(_btn_primary_style())
        self._decode_btn.clicked.connect(lambda: self.execute_requested.emit({"token": self._token_input.toPlainText().strip()}))
        btn_row.addWidget(self._decode_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # ---- 结果区 ----
        result_group = QGroupBox("分析结果")
        result_group.setStyleSheet(_group_style())
        rl = QVBoxLayout(result_group)

        # Header
        rl.addWidget(QLabel("📋 Header:"))
        self._header_edit = QTextEdit()
        self._header_edit.setReadOnly(True)
        self._header_edit.setMaximumHeight(100)
        self._header_edit.setStyleSheet(_output_style())
        rl.addWidget(self._header_edit)

        # Payload
        rl.addWidget(QLabel("📦 Payload:"))
        self._payload_edit = QTextEdit()
        self._payload_edit.setReadOnly(True)
        self._payload_edit.setMaximumHeight(150)
        self._payload_edit.setStyleSheet(_output_style())
        rl.addWidget(self._payload_edit)

        # 时间信息
        self._time_label = QLabel("")
        self._time_label.setStyleSheet("color: #a6adc8; font-size: 12px; padding: 4px;")
        self._time_label.setWordWrap(True)
        rl.addWidget(self._time_label)

        # 安全提示
        self._security_label = QLabel("")
        self._security_label.setStyleSheet("color: #f9e2af; font-size: 12px; padding: 4px;")
        self._security_label.setWordWrap(True)
        rl.addWidget(self._security_label)

        # Signature
        rl.addWidget(QLabel("🔏 Signature:"))
        sig_row = QHBoxLayout()
        self._sig_edit = QLineEdit()
        self._sig_edit.setReadOnly(True)
        self._sig_edit.setStyleSheet(_line_style())
        sig_row.addWidget(self._sig_edit)
        rl.addLayout(sig_row)

        layout.addWidget(result_group, stretch=1)

        # ---- 验证 ----
        verify_group = QGroupBox("签名验证 / 算法攻击测试")
        verify_group.setStyleSheet(_group_style())
        vl = QGridLayout(verify_group)
        vl.setSpacing(8)

        vl.addWidget(QLabel("密钥:"), 0, 0)
        self._secret_input = QLineEdit()
        self._secret_input.setPlaceholderText("输入密钥验证签名...")
        self._secret_input.setStyleSheet(_line_style())
        vl.addWidget(self._secret_input, 0, 1)

        self._verify_btn = QPushButton("✓ 验证签名")
        self._verify_btn.setStyleSheet(_btn_secondary_style())
        self._verify_btn.clicked.connect(lambda: self.execute_requested.emit({
            "token": self._token_input.toPlainText().strip(),
            "verify": True,
            "secret": self._secret_input.text(),
        }))
        vl.addWidget(self._verify_btn, 1, 1)

        layout.addWidget(verify_group)

    def set_header(self, text: str) -> None:
        self._header_edit.setPlainText(text)

    def set_payload(self, text: str) -> None:
        self._payload_edit.setPlainText(text)

    def set_time_info(self, text: str) -> None:
        self._time_label.setText(text)

    def set_security_info(self, text: str) -> None:
        self._security_label.setText(text)

    def set_signature(self, text: str) -> None:
        self._sig_edit.setText(text)


@register_tool
class JwtDebuggerTool(BaseTool):
    """JWT 调试器"""

    meta = ToolMeta(
        name="jwt_debugger",
        display_name="JWT 调试器",
        category=ToolCategory.UTILITIES,
        description="JWT Token 解码分析 / none 算法攻击检测 / 弱密钥检测 / 签名验证",
        icon="🎫",
        version="1.0.0",
        keywords=["jwt", "token", "json", "认证", "none", "算法"],
    )

    def __init__(self) -> None:
        super().__init__()
        self._widget: Optional[JwtToolWidget] = None

    def create_widget(self) -> QWidget:
        self._widget = JwtToolWidget()
        self._widget.execute_requested.connect(lambda p: self.execute(p))
        return self._widget

    def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        token = params.get("token", "").strip()
        verify = params.get("verify", False)
        secret = params.get("secret", "")

        if not token:
            self.output_ready.emit("[错误] 请输入 JWT Token")
            return {}

        # 分割 Token
        parts = token.split(".")
        if len(parts) != 3:
            self.output_ready.emit("[错误] JWT 格式无效（应包含 3 部分，用 . 分隔）")
            return {}

        header_b64, payload_b64, signature = parts

        result = {"header": {}, "payload": {}, "signature": signature}

        header: dict = {}
        payload: dict = {}

        # 解码 Header
        try:
            header = self._b64decode(header_b64)
            if isinstance(header, dict):
                result["header"] = header
                if self._widget:
                    self._widget.set_header(json.dumps(header, indent=2, ensure_ascii=False))
                self.output_ready.emit(f"Header: {json.dumps(header)}")
        except Exception as e:
            self.output_ready.emit(f"Header 解码失败: {e}")

        # 解码 Payload
        try:
            payload = self._b64decode(payload_b64)
            if isinstance(payload, dict):
                result["payload"] = payload
                if self._widget:
                    self._widget.set_payload(json.dumps(payload, indent=2, ensure_ascii=False))
                self.output_ready.emit(f"Payload: {json.dumps(payload)}")
        except Exception as e:
            self.output_ready.emit(f"Payload 解码失败: {e}")

        if self._widget:
            self._widget.set_signature(signature[:40] + ("..." if len(signature) > 40 else ""))

        # 安全检测
        security_issues = self._check_security(header, payload, signature)
        if self._widget:
            self._widget.set_security_info("\n".join(security_issues))
        for issue in security_issues:
            self.output_ready.emit(f"⚠️ {issue}")

        # 时间分析
        time_info = self._analyze_time(payload)
        if self._widget:
            self._widget.set_time_info(time_info)
        if time_info:
            self.output_ready.emit(time_info)

        # 签名验证
        if verify and secret:
            try:
                decoded = jwt.decode(token, secret, algorithms=["HS256", "HS384", "HS512"])
                self.output_ready.emit("✓ 签名验证成功")
            except jwt.ExpiredSignatureError:
                self.output_ready.emit("✗ Token 已过期")
            except jwt.InvalidSignatureError:
                self.output_ready.emit("✗ 签名无效（密钥不匹配）")
            except Exception as e:
                self.output_ready.emit(f"✗ 验证失败: {e}")

        return result

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        token = params.get("token", "").strip()
        if not token:
            return ["请输入 JWT Token"]
        return []

    # ---- 内部 ----

    @staticmethod
    def _b64decode(data: str) -> Any:
        """Base64 URL-safe decode"""
        # 补齐 padding
        padding = 4 - len(data) % 4
        if padding != 4:
            data += "=" * padding
        decoded = base64.urlsafe_b64decode(data).decode("utf-8")
        return json.loads(decoded)

    def _check_security(
        self, header: dict, payload: dict, signature: str
    ) -> list[str]:
        """安全检查"""
        issues = []

        # none 算法
        alg = header.get("alg", "")
        if alg == "none":
            issues.append("🔴 严重: 使用了 'none' 算法 — 可被伪造！")
        elif alg.upper() == "NONE":
            issues.append("🔴 严重: 算法字段为 'NONE' — 可绕过签名验证")

        # 弱密钥算法
        if alg.startswith("HS"):
            if alg == "HS256":
                issues.append("🟡 提示: 使用 HS256，请确保密钥足够长（≥256 bit）")
            elif alg == "HS384" or alg == "HS512":
                issues.append("🟢 HS384/HS512: 推荐使用")

        # RSA 密钥长度提示
        if alg.startswith("RS"):
            issues.append("ℹ️ 使用 RSA 算法，需公钥/私钥对验证")

        # 无签名
        if not signature:
            issues.append("🔴 严重: 签名为空！")

        # 没有过期时间
        if "exp" not in payload:
            issues.append("🟡 提示: Token 无过期时间 (exp)")

        # jwt.io 提示
        if not issues:
            issues.append("✅ 未发现明显安全问题")

        return issues

    def _analyze_time(self, payload: dict) -> str:
        """分析时间字段"""
        lines = []
        now = int(time.time())

        for field, label in [("iat", "签发时间"), ("exp", "过期时间"), ("nbf", "生效时间")]:
            ts = payload.get(field)
            if ts:
                dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                dt_str = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
                if field == "exp":
                    remaining = ts - now
                    if remaining < 0:
                        lines.append(f"⏰ {label} (exp): {dt_str} — 🔴 已过期 ({abs(remaining)}s 前)")
                    elif remaining < 3600:
                        lines.append(f"⏰ {label} (exp): {dt_str} — 🟡 即将过期 ({remaining}s)")
                    else:
                        hours = remaining // 3600
                        lines.append(f"⏰ {label} (exp): {dt_str} — 🟢 剩余 {hours}h {remaining % 3600 // 60}m")
                elif field == "nbf":
                    if ts > now:
                        lines.append(f"⏰ {label} (nbf): {dt_str} — 尚未生效")
                    else:
                        lines.append(f"⏰ {label} (nbf): {dt_str} — 已生效")
                else:
                    lines.append(f"⏰ {label} (iat): {dt_str}")

        if not lines:
            lines.append("无时间字段")

        return "\n".join(lines)


# ---- 样式 ----

def _group_style() -> str:
    return """
        QGroupBox { color: #cdd6f4; font-size: 14px; font-weight: bold;
            border: 1px solid #313244; border-radius: 8px;
            margin-top: 8px; padding-top: 20px; }
        QGroupBox::title { subcontrol-origin: margin; left: 16px; padding: 0 8px; }
    """


def _input_style() -> str:
    return """
        QTextEdit { background-color: #313244; color: #cdd6f4;
            border: 1px solid #45475a; border-radius: 6px;
            padding: 10px; font-family: Consolas, monospace; font-size: 12px; }
    """


def _output_style() -> str:
    return """
        QTextEdit { background-color: #11111b; color: #a6e3a1;
            border: 1px solid #313244; border-radius: 6px;
            padding: 8px; font-family: Consolas, monospace; font-size: 12px; }
    """


def _line_style() -> str:
    return """
        QLineEdit { background-color: #313244; color: #cdd6f4;
            border: 1px solid #45475a; border-radius: 6px;
            padding: 8px 12px; font-family: Consolas, monospace; font-size: 12px; }
    """


def _btn_primary_style() -> str:
    return """
        QPushButton { background-color: #cba6f7; color: #1e1e2e;
            border: none; border-radius: 6px;
            padding: 10px 24px; font-size: 13px; font-weight: bold; }
        QPushButton:hover { background-color: #b4befe; }
    """


def _btn_secondary_style() -> str:
    return """
        QPushButton { background-color: #313244; color: #cdd6f4;
            border: 1px solid #45475a; border-radius: 6px;
            padding: 8px 16px; font-size: 12px; }
        QPushButton:hover { background-color: #45475a; }
    """
