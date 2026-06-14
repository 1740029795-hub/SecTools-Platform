"""
应用配置管理 — 统一管理用户设置和默认值。

配置来源优先级: 用户配置 JSON > 默认值 > 内置硬编码 fallback
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional


class AppConfig:
    """应用配置管理器（单例）"""

    _instance: Optional["AppConfig"] = None

    DEFAULTS = {
        "external_tools": {
            "nmap": "nmap",
            "sqlmap": "",
            "dirb": "",
            "nikto": "",
            "python_path": "",
        },
        "proxy": {
            "enabled": False,
            "http": "",
            "https": "",
        },
        "theme": "dark",
        "language": "zh_CN",
        "max_threads": 10,
        "timeout": 30,
        "user_agent": "SecTools-Platform/1.0",
        "verify_ssl": False,
        "max_history": 50,
        "log_level": "INFO",
    }

    def __new__(cls) -> "AppConfig":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._data: dict[str, Any] = dict(cls.DEFAULTS)
            cls._instance._loaded = False
        return cls._instance

    # ---- 文件操作 ----

    def load(self, filepath: Optional[str] = None) -> None:
        """从 JSON 文件加载配置"""
        if filepath is None:
            filepath = self._default_path()
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                user_data = json.load(f)
            self._deep_update(self._data, user_data)
            self._loaded = True
        except FileNotFoundError:
            self._loaded = True  # 使用默认值即可
        except json.JSONDecodeError as e:
            print(f"[AppConfig] JSON 解析错误: {e}")
            self._loaded = True

    def save(self, filepath: Optional[str] = None) -> None:
        """保存配置到 JSON 文件"""
        if filepath is None:
            filepath = self._default_path()
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    # ---- 便捷访问 ----

    def get(self, key: str, default: Any = None) -> Any:
        """支持点号分隔的深路径取值, 如 'proxy.http'"""
        keys = key.split(".")
        val = self._data
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return default
        return val

    def set(self, key: str, value: Any) -> None:
        """支持点号分隔的深路径设值"""
        keys = key.split(".")
        target = self._data
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]
        target[keys[-1]] = value

    def get_all(self) -> dict[str, Any]:
        return dict(self._data)

    # ---- 内部 ----

    @staticmethod
    def _default_path() -> str:
        return str(
            Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
            / "SecTools"
            / "config.json"
        )

    @staticmethod
    def _deep_update(target: dict, source: dict) -> None:
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                AppConfig._deep_update(target[key], value)
            else:
                target[key] = value


# 全局单例
app_config = AppConfig()
