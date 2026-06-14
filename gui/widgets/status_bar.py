"""
状态栏 — 显示应用状态、工具运行状态、进度等信息。
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QStatusBar,
    QWidget,
)


class AppStatusBar(QStatusBar):
    """应用状态栏"""

    status_message = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        self.setStyleSheet("""
            QStatusBar {
                background-color: #1e1e2e;
                color: #a6adc8;
                border-top: 1px solid #313244;
                font-size: 12px;
                min-height: 24px;
                padding: 2px 8px;
            }
        """)

        # 永久部件
        self._status_label = QLabel("就绪")
        self.addWidget(self._status_label)

        # 进度条（默认隐藏）
        self._progress_bar = QProgressBar()
        self._progress_bar.setMaximumWidth(200)
        self._progress_bar.setMaximumHeight(16)
        self._progress_bar.setVisible(False)
        self._progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #313244;
                border: 1px solid #45475a;
                border-radius: 3px;
                text-align: center;
                color: #cdd6f4;
                font-size: 10px;
            }
            QProgressBar::chunk {
                background-color: #89b4fa;
                border-radius: 2px;
            }
        """)
        self.addPermanentWidget(self._progress_bar)

        # 工具数标签
        self._tool_count_label = QLabel("工具: 0")
        self._tool_count_label.setStyleSheet("color: #6c7086; padding-right: 8px;")
        self.addPermanentWidget(self._tool_count_label)

    # ---- 公开方法 ----

    def show_message(self, message: str, timeout: int = 5000) -> None:
        """显示临时消息"""
        self.showMessage(message, timeout)
        self.status_message.emit(message)

    def set_status(self, text: str) -> None:
        """设置持久状态文本"""
        self._status_label.setText(text)

    @pyqtSlot(int)
    def set_progress(self, value: int) -> None:
        """设置进度条值 (0-100)"""
        self._progress_bar.setVisible(True)
        self._progress_bar.setValue(value)
        if value >= 100:
            self.hide_progress()

    @pyqtSlot(int, int)
    def set_progress_range(self, current: int, total: int) -> None:
        """设置进度条 (current/total)"""
        self._progress_bar.setVisible(True)
        if total > 0:
            percent = int(current / total * 100)
        else:
            percent = 0
        self._progress_bar.setValue(percent)

    def hide_progress(self) -> None:
        """隐藏进度条"""
        self._progress_bar.setVisible(False)
        self._progress_bar.setValue(0)

    def set_tool_count(self, count: int) -> None:
        """更新工具计数"""
        self._tool_count_label.setText(f"工具: {count}")
