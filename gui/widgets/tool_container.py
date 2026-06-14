"""
工具容器 — QStackedWidget 封装，管理所有工具页面的切换。

每个工具对应一个页面：
  ┌──────────────────────────────┐
  │  工具标题栏（名称 + 操作按钮）       │
  ├──────────────────────────────┤
  │  工具自定义 UI（create_widget）     │
  ├──────────────────────────────┤
  │  输出控制台（统一）                │
  └──────────────────────────────┘
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.tool_base import BaseTool
from core.tool_worker import ThreadedToolRunner
from gui.widgets.output_console import OutputConsole


class ToolPage(QWidget):
    """单个工具的页面"""

    execute_requested = pyqtSignal(dict)  # 请求执行工具

    def __init__(
        self, tool: BaseTool, console: OutputConsole, parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self._tool = tool

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ---- 标题栏 ----
        title_bar = QWidget()
        title_bar.setStyleSheet("""
            background-color: #181825;
            border-bottom: 1px solid #313244;
        """)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(16, 8, 16, 8)

        title_label = QLabel(f"{tool.meta.icon} {tool.meta.display_name}")
        title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #cdd6f4;
            border: none;
            background: transparent;
        """)
        title_layout.addWidget(title_label)

        desc_label = QLabel(tool.meta.description)
        desc_label.setStyleSheet("""
            font-size: 12px;
            color: #a6adc8;
            border: none;
            background: transparent;
        """)
        desc_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        title_layout.addWidget(desc_label)
        title_layout.addStretch()

        # 执行按钮
        self._run_btn = QPushButton("▶ 执行")
        self._run_btn.setStyleSheet("""
            QPushButton {
                background-color: #a6e3a1;
                color: #1e1e2e;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #94e2d5;
            }
            QPushButton:pressed {
                background-color: #74c7ec;
            }
            QPushButton:disabled {
                background-color: #45475a;
                color: #6c7086;
            }
        """)
        self._run_btn.clicked.connect(self._on_execute_clicked)
        title_layout.addWidget(self._run_btn)

        layout.addWidget(title_bar)

        # ---- 内容区（工具 UI + 输出） ----
        splitter = QSplitter(Qt.Orientation.Vertical)

        # 工具自定义 UI
        self._tool_widget = tool.create_widget()
        self._tool_widget.setStyleSheet("""
            background-color: #1e1e2e;
        """)
        splitter.addWidget(self._tool_widget)

        # 输出控制台
        splitter.addWidget(console)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([400, 200])

        layout.addWidget(splitter, stretch=1)

    @property
    def tool(self) -> BaseTool:
        return self._tool

    @property
    def run_button(self) -> QPushButton:
        return self._run_btn

    def get_params(self) -> dict:
        """从工具 UI 收集参数 — 子类可覆盖"""
        return {}

    def _on_execute_clicked(self) -> None:
        params = self.get_params()
        self.execute_requested.emit(params)


class ToolContainer(QWidget):
    """管理所有工具页面的容器"""

    tool_switched = pyqtSignal(str, BaseTool)  # tool_name, tool_instance

    def __init__(
        self, console: OutputConsole, parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self._console = console
        self._pages: dict[str, ToolPage] = {}
        self._current_name: Optional[str] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 占位页面
        self._placeholder = QWidget()
        placeholder_layout = QVBoxLayout(self._placeholder)
        placeholder_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph_label = QLabel("选择一个工具开始使用")
        ph_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ph_label.setStyleSheet("""
            font-size: 24px;
            color: #6c7086;
        """)
        placeholder_layout.addWidget(ph_label)
        sub_label = QLabel("左侧导航栏选择安全工具，或使用搜索快速定位")
        sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub_label.setStyleSheet("font-size: 14px; color: #585b70;")
        placeholder_layout.addWidget(sub_label)

        # QStackedWidget
        self._stack = QStackedWidget()
        self._stack.addWidget(self._placeholder)  # index 0
        layout.addWidget(self._stack)

    def add_tool(self, tool: BaseTool) -> None:
        """添加一个工具页面"""
        page = ToolPage(tool, self._console)
        page.execute_requested.connect(
            lambda params, t=tool: self._on_execute(t, params)
        )
        self._pages[tool.meta.name] = page
        self._stack.addWidget(page)
        # 连接工具信号到控制台
        if hasattr(tool, 'output_ready'):
            tool.output_ready.connect(self._console.append)
        if hasattr(tool, 'finished'):
            tool.finished.connect(
                lambda result, p=page: self._on_tool_finished(p, result)
            )

    def switch_to(self, name: str) -> Optional[BaseTool]:
        """切换到指定工具页面"""
        if name == self._current_name:
            return None

        # 通知旧工具失活
        if self._current_name and self._current_name in self._pages:
            self._pages[self._current_name].tool.on_tab_deactivated()

        page = self._pages.get(name)
        if page:
            self._stack.setCurrentWidget(page)
            self._current_name = name
            page.tool.on_tab_activated()
            self.tool_switched.emit(name, page.tool)
            return page.tool

        self._stack.setCurrentWidget(self._placeholder)
        self._current_name = None
        return None

    def current_tool(self) -> Optional[BaseTool]:
        """获取当前工具实例"""
        if self._current_name and self._current_name in self._pages:
            return self._pages[self._current_name].tool
        return None

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """获取指定工具实例"""
        page = self._pages.get(name)
        return page.tool if page else None

    # ---- 内部 ----

    def _on_execute(self, tool: BaseTool, params: dict) -> None:
        """在后台线程执行工具逻辑（UI 不阻塞）"""
        page = self._pages.get(tool.meta.name)
        if page:
            page.run_button.setEnabled(False)
            page.run_button.setText("⏳ 运行中...")
            self._console.append_header(
                f"{'=' * 50}\n"
                f"开始执行: {tool.meta.display_name}\n"
                f"{'=' * 50}"
            )

        # 参数验证
        errors = tool.validate_params(params)
        if errors:
            for err in errors:
                self._console.append_error(f"[参数错误] {err}")
            if page:
                page.run_button.setEnabled(True)
                page.run_button.setText("▶ 执行")
            return

        # 使用 ThreadedToolRunner 在后台线程执行
        runner = ThreadedToolRunner(tool)
        runner.finished.connect(
            lambda result, p=page: self._on_tool_finished(p, result)
        )
        runner.error.connect(
            lambda err, p=page: self._on_tool_error(p, err)
        )
        runner.run(params)

    def _on_tool_finished(self, page: ToolPage, result) -> None:
        """工具执行完成"""
        page.run_button.setEnabled(True)
        page.run_button.setText("▶ 执行")
        self._console.append_success("✓ 执行完成")

    def _on_tool_error(self, page: ToolPage, error_msg: str) -> None:
        """工具执行出错"""
        page.run_button.setEnabled(True)
        page.run_button.setText("▶ 执行")
        self._console.append_error(f"[执行错误] {error_msg}")
