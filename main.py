"""
网络安全工具集成平台 — 主入口

为信息安全专业学生构建的桌面应用，集成各类网络安全工具，
用于学习 Web 安全测试并在漏洞盒子、补天等平台提交漏洞。

启动方式:
    python main.py

技术栈:
    - Python 3.x + PyQt6
    - 插件式模块化架构
    - 深色黑客风格主题
"""

from __future__ import annotations

import sys
import os
import traceback
from pathlib import Path


def setup_path() -> None:
    """确保项目根目录在 sys.path 中"""
    project_root = Path(__file__).resolve().parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


def setup_exception_hook(app, logger) -> None:
    """安装全局异常捕获钩子 — 未处理异常弹出对话框并记录日志"""

    def _exception_hook(exc_type, exc_value, exc_tb):
        # 记录到日志
        tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        logger.critical(f"未处理的异常:\n{tb_str}")

        # 弹出错误对话框
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(
            None,
            "严重错误",
            f"发生了未处理的异常:\n\n{exc_value}\n\n"
            f"详细信息已写入日志文件。\n"
            f"应用可能处于不稳定状态，建议重启。",
        )
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = _exception_hook

    # 同时捕获线程中的异常
    import threading
    _original_thread_init = threading.Thread.__init__

    def _patched_init(self, *args, **kwargs):
        _original_thread_init(self, *args, **kwargs)
        _original_run = self.run

        def _patched_run():
            try:
                _original_run()
            except Exception:
                sys.excepthook(*sys.exc_info())

        self.run = _patched_run

    threading.Thread.__init__ = _patched_init


def main() -> None:
    """应用入口"""
    setup_path()

    # --- 初始化配置 ---
    from config.app_config import app_config
    app_config.load()

    # --- 初始化日志 ---
    from core.logger import log_manager
    log_manager.init(level=app_config.get("log_level", "INFO"))
    logger = log_manager.logger

    # 抑制第三方库日志噪音
    import logging
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    # --- 创建 Qt Application ---
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("SecTools Platform")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("SecTools")
    app.setStyle("Fusion")

    # --- 全局异常钩子 ---
    setup_exception_hook(app, logger)

    # --- 创建主窗口 ---
    logger.info("正在初始化主窗口...")
    from gui.main_window import MainWindow
    window = MainWindow()

    # 日志→GUI 控制台桥接：将 log_manager 的输出同步到 GUI 输出控制台
    log_manager.attach_console(
        lambda level, msg: _log_to_console(window, level, msg)
    )

    window.show()

    # --- 加载工具 ---
    window.load_tools()
    logger.info(
        "应用启动完成 — %d 个工具已加载",
        window._registry.tool_count if hasattr(window, '_registry') else 0,
    )

    # --- 进入事件循环 ---
    exit_code = app.exec()

    # --- 退出清理 ---
    logger.info("应用退出 (exit_code=%d)", exit_code)
    app_config.save()
    sys.exit(exit_code)


def _log_to_console(window, level: str, message: str) -> None:
    """将日志消息转发到 GUI 输出控制台"""
    try:
        console = getattr(window, '_console', None)
        if console is None:
            return
        if level == "ERROR":
            console.append_error(message)
        elif level == "WARNING":
            console.append_warning(message)
        elif level == "DEBUG":
            console.append_info(message)
        else:
            console.append(message)
    except Exception:
        pass  # GUI 可能尚未就绪，静默忽略


if __name__ == "__main__":
    main()
