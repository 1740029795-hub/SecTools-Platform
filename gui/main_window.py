"""
主窗口 — 应用主框架，整合侧边栏、工具容器、状态栏。

布局:
  ┌─────────────┬──────────────────────────────────┐
  │             │                                   │
  │   Sidebar   │     ToolContainer                 │
  │  (导航/搜索) │  (工具页 + 输出控制台)               │
  │             │                                   │
  ├─────────────┴──────────────────────────────────┤
  │              StatusBar                          │
  └────────────────────────────────────────────────┘
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, QSettings, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from config.app_config import app_config
from core.logger import log_manager
from core.tool_base import BaseTool, ToolCategory
from core.tool_registry import ToolRegistry, tool_registry
from gui.styles import GLOBAL_STYLESHEET, COLORS
from gui.widgets.output_console import OutputConsole
from gui.widgets.sidebar import Sidebar
from gui.widgets.status_bar import AppStatusBar
from gui.widgets.tool_container import ToolContainer


class MainWindow(QMainWindow):
    """应用主窗口"""

    # 信号
    tool_switched = pyqtSignal(str)

    def __init__(self) -> None:
        super().__init__()
        self._registry: ToolRegistry = tool_registry
        self._tool_instances: dict[str, BaseTool] = {}
        self._init_settings()
        self._init_theme()
        self._init_ui()
        self._connect_signals()

    # ---- 初始化 ----

    def _init_settings(self) -> None:
        """初始化 QSettings — 默认窗口为屏幕的 70%"""
        self._settings = QSettings("SecTools", "SecurityPlatform")

        # 获取屏幕可用区域
        screen_geo = self.screen().availableGeometry()

        # 恢复上次尺寸和位置，或使用默认
        saved_w = self._settings.value("window/width", 0, type=int)
        saved_h = self._settings.value("window/height", 0, type=int)
        saved_x = self._settings.value("window/x", -1, type=int)
        saved_y = self._settings.value("window/y", -1, type=int)

        if saved_w and saved_h:
            self.resize(saved_w, saved_h)
            if saved_x >= 0 and saved_y >= 0:
                self.move(saved_x, saved_y)
            else:
                self._center_on_screen(screen_geo)
        else:
            w = int(screen_geo.width() * 0.7)
            h = int(screen_geo.height() * 0.75)
            self.resize(min(w, 1100), min(h, 750))
            self._center_on_screen(screen_geo)

        self.setMinimumSize(900, 550)

    def _init_theme(self) -> None:
        """应用深色主题"""
        # QDarkStyleSheet 提供专业深色主题作为基础
        # 后续通过自定义 QSS 微调
        pass

    def _init_ui(self) -> None:
        """构建 UI"""
        self.setWindowTitle("🔐 网络安全工具平台 - SecTools Platform")
        self.setMinimumSize(1024, 600)

        # ---- 中央部件 ----
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ---- 输出控制台（共享）----
        self._console = OutputConsole()

        # ---- 侧边栏 ----
        self._sidebar = Sidebar()
        main_layout.addWidget(self._sidebar)

        # ---- 工具容器 ----
        self._tool_container = ToolContainer(self._console)
        main_layout.addWidget(self._tool_container, stretch=1)

        # ---- 状态栏 ----
        self._status_bar = AppStatusBar()
        self.setStatusBar(self._status_bar)

        # ---- 菜单栏 ----
        self._init_menubar()

        # ---- 全局样式 ----
        self._apply_global_style()

    def _init_menubar(self) -> None:
        """初始化菜单栏"""
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: #181825;
                color: #cdd6f4;
                border-bottom: 1px solid #313244;
                padding: 2px;
            }
            QMenuBar::item:selected {
                background-color: #313244;
            }
            QMenu {
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: 1px solid #313244;
            }
            QMenu::item:selected {
                background-color: #45475a;
            }
        """)

        # ---- 文件菜单 ----
        file_menu = menubar.addMenu("文件(&F)")

        export_action = QAction("导出输出...", self)
        export_action.setShortcut("Ctrl+S")
        export_action.triggered.connect(self._export_output)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # ---- 工具菜单 ----
        tools_menu = menubar.addMenu("工具(&T)")

        clear_output_action = QAction("清空输出", self)
        clear_output_action.setShortcut("Ctrl+L")
        clear_output_action.triggered.connect(self._console.clear)
        tools_menu.addAction(clear_output_action)

        tools_menu.addSeparator()

        refresh_action = QAction("重新加载工具", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self._refresh_tools)
        tools_menu.addAction(refresh_action)

        # ---- 设置菜单 ----
        settings_menu = menubar.addMenu("设置(&S)")

        settings_action = QAction("⚙️ 系统设置...", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self._open_settings)
        settings_menu.addAction(settings_action)

        # ---- 帮助菜单 ----
        help_menu = menubar.addMenu("帮助(&H)")

        about_action = QAction("关于", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _apply_global_style(self) -> None:
        """应用全局样式"""
        self.setStyleSheet(GLOBAL_STYLESHEET)

    def _connect_signals(self) -> None:
        """连接信号/槽"""
        # 侧边栏选择工具
        self._sidebar.tool_selected.connect(self._on_tool_selected)
        # 工具切换
        self._tool_container.tool_switched.connect(self._on_tool_switched)
        # 控制台输出 → 状态栏
        self._console.output_appended.connect(
            lambda text: self._status_bar.set_status(text[:80])
        )

    # ---- 工具管理 ----

    def load_tools(self) -> None:
        """加载所有工具模块并填充侧边栏"""
        # 自动发现并导入模块
        self._registry.auto_discover()

        # 实例化工具
        for name, tool_cls in self._registry.get_all_tools().items():
            try:
                instance = tool_cls()
                self._tool_instances[name] = instance
                self._tool_container.add_tool(instance)
            except Exception as e:
                print(f"[MainWindow] 无法实例化工具 {name}: {e}")

        # 按分类填充侧边栏
        categories = self._registry.get_categories()
        for category, tools in sorted(
            categories.items(),
            key=lambda x: list(ToolCategory).index(x[0]) if x[0] in list(ToolCategory) else 99
        ):
            self._sidebar.add_category(category, tools)

        # 更新状态栏
        count = self._registry.tool_count
        self._status_bar.set_tool_count(count)
        self._status_bar.set_status(f"就绪 — {count} 个工具已加载")

    def load_tools_manual(self, tool_instances: dict[str, BaseTool]) -> None:
        """手动加载工具实例（备选方案）"""
        for name, instance in tool_instances.items():
            self._registry.register(type(instance))
            self._tool_instances[name] = instance
            self._tool_container.add_tool(instance)

        categories = self._registry.get_categories()
        for category, tools in sorted(categories.items(), key=lambda x: x[0].value):
            self._sidebar.add_category(category, tools)

        self._status_bar.set_tool_count(len(tool_instances))
        self._status_bar.set_status(f"就绪 — {len(tool_instances)} 个工具已加载")

    # ---- 槽 ----

    def _on_tool_selected(self, name: str) -> None:
        """侧边栏选择工具"""
        tool = self._tool_container.switch_to(name)
        if tool:
            self._sidebar.select_tool(name)
            self._status_bar.set_status(f"当前工具: {tool.meta.display_name}")

    def _on_tool_switched(self, name: str, tool: BaseTool) -> None:
        """工具切换"""
        self.tool_switched.emit(name)

    def _export_output(self) -> None:
        """导出控制台输出"""
        from PyQt6.QtWidgets import QFileDialog
        from pathlib import Path

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "导出输出",
            str(Path.home() / "output.txt"),
            "文本文件 (*.txt);;所有文件 (*.*)",
        )
        if filepath:
            try:
                Path(filepath).write_text(
                    self._console.get_text(), encoding="utf-8"
                )
                self._status_bar.show_message(f"已导出到: {filepath}")
            except Exception as e:
                QMessageBox.warning(self, "导出失败", str(e))

    def _refresh_tools(self) -> None:
        """刷新工具列表"""
        # 简化实现：清理并重新加载
        self._status_bar.show_message("正在刷新工具列表...")
        # 完整重新加载需要重建 UI，这里先做基本刷新
        self._status_bar.set_tool_count(self._registry.tool_count)
        self._status_bar.show_message("工具列表已刷新")

    def _show_about(self) -> None:
        """显示关于对话框"""
        QMessageBox.about(
            self,
            "关于 网络安全工具平台",
            "<h2>🔐 网络安全工具平台</h2>"
            "<p>SecTools Platform v1.0.0</p>"
            "<p>专为信息安全学习者设计的集成化安全工具平台。</p>"
            "<p>技术栈: Python + PyQt6</p>"
            "<hr>"
            "<p>免责声明: 本工具仅供学习和授权的安全测试使用，"
            "禁止用于任何非法活动。</p>",
        )

    # ---- 生命周期 ----

    def _open_settings(self) -> None:
        """打开设置对话框"""
        from gui.dialogs.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self)
        dialog.exec()

    def _center_on_screen(self, screen_geo) -> None:
        """将窗口居中到屏幕"""
        frame_geo = self.frameGeometry()
        x = screen_geo.x() + (screen_geo.width() - frame_geo.width()) // 2
        y = screen_geo.y() + (screen_geo.height() - frame_geo.height()) // 2
        self.move(max(0, x), max(0, y))

    def closeEvent(self, event) -> None:
        """窗口关闭时保存设置"""
        self._settings.setValue("window/width", self.width())
        self._settings.setValue("window/height", self.height())
        self._settings.setValue("window/x", self.x())
        self._settings.setValue("window/y", self.y())

        # 清理工具
        for instance in self._tool_instances.values():
            try:
                instance.cleanup()
            except Exception:
                pass

        super().closeEvent(event)
