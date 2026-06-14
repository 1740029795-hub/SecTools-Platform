"""
统一输出控制台 — 所有工具共享的实时输出面板。

特性:
  - QPlainTextEdit 高性能文本渲染
  - ANSI 颜色支持（简单处理）
  - 自动滚动
  - 时间戳前缀
  - 一键清空
  - 文本搜索
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import (
    QColor,
    QFont,
    QTextCharFormat,
    QTextCursor,
    QAction,
    QKeySequence,
)
from PyQt6.QtWidgets import (
    QPlainTextEdit,
    QVBoxLayout,
    QHBoxLayout,
    QToolBar,
    QToolButton,
    QWidget,
    QStyle,
)


class OutputConsole(QWidget):
    """统一输出控制台"""

    # 信号：通知外部有新输出
    output_appended = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._auto_scroll: bool = True
        self._show_timestamp: bool = True
        self._max_lines: int = 5000
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ---- 工具栏 ----
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setStyleSheet("""
            QToolBar {
                background-color: #1e1e2e;
                border-bottom: 1px solid #313244;
                padding: 2px;
                spacing: 4px;
            }
            QToolButton {
                color: #cdd6f4;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
            }
            QToolButton:hover {
                background-color: #313244;
                border-color: #45475a;
            }
            QToolButton:pressed {
                background-color: #45475a;
            }
        """)

        # 清空按钮
        self._clear_btn = QToolButton()
        self._clear_btn.setText("清空")
        self._clear_btn.setToolTip("清空输出 (Ctrl+L)")
        self._clear_btn.clicked.connect(self.clear)
        toolbar.addWidget(self._clear_btn)

        # 自动滚动按钮
        self._autoscroll_btn = QToolButton()
        self._autoscroll_btn.setText("自动滚动: ON")
        self._autoscroll_btn.setToolTip("切换自动滚动")
        self._autoscroll_btn.clicked.connect(self._toggle_autoscroll)
        toolbar.addWidget(self._autoscroll_btn)

        # 时间戳按钮
        self._timestamp_btn = QToolButton()
        self._timestamp_btn.setText("时间戳: ON")
        self._timestamp_btn.setToolTip("切换时间戳显示")
        self._timestamp_btn.clicked.connect(self._toggle_timestamp)
        toolbar.addWidget(self._timestamp_btn)

        toolbar.addSeparator()

        # 行数标签
        self._line_count_label = QToolButton()
        self._line_count_label.setText("0 行")
        self._line_count_label.setEnabled(False)
        toolbar.addWidget(self._line_count_label)

        layout.addWidget(toolbar)

        # ---- 文本编辑区 ----
        self._editor = QPlainTextEdit()
        self._editor.setReadOnly(True)
        self._editor.setMaximumBlockCount(self._max_lines)
        self._editor.setStyleSheet("""
            QPlainTextEdit {
                background-color: #11111b;
                color: #cdd6f4;
                border: none;
                font-family: "Cascadia Code", "Consolas", "Microsoft YaHei Mono", monospace;
                font-size: 13px;
                selection-background-color: #45475a;
            }
        """)

        # 设置 tab 宽度
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self._editor.setFont(font)
        self._editor.setTabStopDistance(40)

        layout.addWidget(self._editor)

        # 键盘快捷键
        clear_action = QAction("清空", self)
        clear_action.setShortcut(QKeySequence("Ctrl+L"))
        clear_action.triggered.connect(self.clear)
        self.addAction(clear_action)

    # ---- 公开方法 ----

    @pyqtSlot(str)
    def append(self, text: str) -> None:
        """追加普通文本"""
        self._append_with_format(text, QColor("#cdd6f4"))

    @pyqtSlot(str)
    def append_success(self, text: str) -> None:
        """追加成功文本（绿色）"""
        self._append_with_format(text, QColor("#a6e3a1"))

    @pyqtSlot(str)
    def append_error(self, text: str) -> None:
        """追加错误文本（红色）"""
        self._append_with_format(text, QColor("#f38ba8"))

    @pyqtSlot(str)
    def append_warning(self, text: str) -> None:
        """追加警告文本（黄色）"""
        self._append_with_format(text, QColor("#f9e2af"))

    @pyqtSlot(str)
    def append_info(self, text: str) -> None:
        """追加信息文本（蓝色）"""
        self._append_with_format(text, QColor("#89b4fa"))

    @pyqtSlot(str)
    def append_header(self, text: str) -> None:
        """追加标题文本（粗体青色）"""
        fmt = QTextCharFormat()
        fmt.setForeground(QColor("#94e2d5"))
        fmt.setFontWeight(QFont.Weight.Bold)
        self._append_formatted(text, fmt)

    def clear(self) -> None:
        """清空输出"""
        self._editor.clear()
        self._update_line_count()

    def get_text(self) -> str:
        """获取全部文本"""
        return self._editor.toPlainText()

    def copy_selection(self) -> None:
        """复制选中文本"""
        self._editor.copy()

    @property
    def auto_scroll(self) -> bool:
        return self._auto_scroll

    # ---- 内部方法 ----

    def _append_with_format(self, text: str, color: QColor) -> None:
        """以指定颜色追加文本"""
        fmt = QTextCharFormat()
        fmt.setForeground(color)
        self._append_formatted(text, fmt)
        self.output_appended.emit(text)

    def _append_formatted(self, text: str, fmt: QTextCharFormat) -> None:
        """以指定格式追加文本"""
        cursor = self._editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        if self._show_timestamp:
            ts = datetime.now().strftime("[%H:%M:%S] ")
            cursor.insertText(ts)  # 时间戳用默认格式

        cursor.insertText(text + "\n", fmt)
        self._update_line_count()

        if self._auto_scroll:
            self._editor.setTextCursor(cursor)
            self._editor.ensureCursorVisible()

    def _toggle_autoscroll(self) -> None:
        self._auto_scroll = not self._auto_scroll
        state = "ON" if self._auto_scroll else "OFF"
        self._autoscroll_btn.setText(f"自动滚动: {state}")

    def _toggle_timestamp(self) -> None:
        self._show_timestamp = not self._show_timestamp
        state = "ON" if self._show_timestamp else "OFF"
        self._timestamp_btn.setText(f"时间戳: {state}")

    def _update_line_count(self) -> None:
        count = self._editor.document().blockCount()
        self._line_count_label.setText(f"{count} 行")
