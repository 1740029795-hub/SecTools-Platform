"""
统一日志系统 — 格式化日志输出，同时写入文件和 GUI 控制台。

用法:
    from core.logger import logger
    logger.info("启动应用")
    logger.warning("连接超时")
    logger.error("执行失败", exc_info=True)
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class LogManager:
    """日志管理器（单例）"""

    _instance: Optional["LogManager"] = None

    def __new__(cls) -> "LogManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._logger: Optional[logging.Logger] = None
            cls._instance._console_signals: list = []
        return cls._instance

    def init(
        self,
        level: str = "INFO",
        log_dir: Optional[str] = None,
        max_bytes: int = 2 * 1024 * 1024,  # 2MB
        backup_count: int = 3,
    ) -> logging.Logger:
        """初始化日志系统（仅首次调用有效）"""
        if self._logger is not None:
            return self._logger

        self._logger = logging.getLogger("SecTools")
        self._logger.setLevel(getattr(logging, level.upper(), logging.INFO))

        fmt = logging.Formatter(
            "[%(asctime)s] [%(levelname)-5s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # 控制台输出
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(fmt)
        console_handler.setLevel(logging.DEBUG)
        self._logger.addHandler(console_handler)

        # 文件输出（带轮转）
        if log_dir is None:
            log_dir = str(Path.home() / ".sectools" / "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(
            log_dir, f"sectools_{datetime.now().strftime('%Y%m%d')}.log"
        )

        try:
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
            )
        except ImportError:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")

        file_handler.setFormatter(fmt)
        file_handler.setLevel(logging.DEBUG)
        self._logger.addHandler(file_handler)

        self._logger.info("=" * 50)
        self._logger.info("SecTools Platform 启动")
        self._logger.info(f"日志文件: {log_file}")
        self._logger.info("=" * 50)

        return self._logger

    @property
    def logger(self) -> logging.Logger:
        if self._logger is None:
            self._logger = logging.getLogger("SecTools")
            self._logger.setLevel(logging.INFO)
            if not self._logger.handlers:
                self._logger.addHandler(logging.StreamHandler(sys.stdout))
        return self._logger

    def attach_console(self, callback) -> None:
        """附加 GUI 控制台回调"""
        self._console_signals.append(callback)

    def emit_to_console(self, level: str, message: str) -> None:
        """发送消息到 GUI 控制台"""
        for cb in self._console_signals:
            try:
                cb(level, message)
            except Exception:
                pass


# 全局日志管理器
log_manager = LogManager()

# 便捷函数
def get_logger() -> logging.Logger:
    return log_manager.logger


def safe_execute(func):
    """装饰器：捕获并记录异常"""
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            log_manager.logger.error(
                f"{func.__name__} 执行失败: {e}", exc_info=True
            )
            raise

    return wrapper
