"""
侧边栏 — 左侧分类导航，按分类展示所有已注册工具。

特性:
  - 可折叠分类标题
  - 工具列表项带图标和标签
  - 搜索过滤
  - 点击切换工具
"""

from __future__ import annotations

from typing import Optional, Callable

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import (
    QFrame,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from core.tool_base import ToolCategory, ToolMeta


class CategoryHeader(QWidget):
    """可折叠的分类标题"""

    clicked = pyqtSignal(ToolCategory)

    def __init__(
        self,
        category: ToolCategory,
        tool_count: int = 0,
        collapsed: bool = False,
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.category = category
        self._collapsed = collapsed

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._btn = QToolButton()
        self._btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._btn.setArrowType(
            Qt.ArrowType.RightArrow if collapsed else Qt.ArrowType.DownArrow
        )
        text = f"{category.value} ({tool_count})"
        self._btn.setText(text)
        self._btn.setCheckable(False)
        self._btn.clicked.connect(lambda: self.clicked.emit(self.category))
        self._btn.setStyleSheet("""
            QToolButton {
                color: #cdd6f4;
                font-weight: bold;
                font-size: 13px;
                border: none;
                text-align: left;
                padding: 8px 12px;
                background-color: #181825;
            }
            QToolButton:hover {
                background-color: #313244;
            }
        """)

        layout.addWidget(self._btn)

    @property
    def collapsed(self) -> bool:
        return self._collapsed

    def toggle(self) -> None:
        self._collapsed = not self._collapsed
        self._btn.setArrowType(
            Qt.ArrowType.RightArrow if self._collapsed else Qt.ArrowType.DownArrow
        )


class Sidebar(QFrame):
    """侧边栏"""

    tool_selected = pyqtSignal(str)  # tool name

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._tool_items: dict[str, QListWidgetItem] = {}
        self._category_headers: dict[ToolCategory, CategoryHeader] = {}
        self._category_lists: dict[ToolCategory, QListWidget] = {}
        self._collapsed: set[ToolCategory] = set()
        self._on_tool_selected: Optional[Callable[[str], None]] = None
        self._init_ui()

    def _init_ui(self) -> None:
        self.setObjectName("sidebar")
        self.setMinimumWidth(200)
        self.setMaximumWidth(320)
        self.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
        )
        self.setStyleSheet("""
            #sidebar {
                background-color: #1e1e2e;
                border-right: 1px solid #313244;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ---- 标题 ----
        title = QLabel("🔐 安全工具箱")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                color: #cdd6f4;
                font-size: 16px;
                font-weight: bold;
                padding: 16px 8px 12px 8px;
                background-color: #181825;
                border-bottom: 2px solid #cba6f7;
            }
        """)
        layout.addWidget(title)

        # ---- 搜索框 ----
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("🔍 搜索工具...")
        self._search_input.setClearButtonEnabled(True)
        self._search_input.setStyleSheet("""
            QLineEdit {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 8px 12px;
                margin: 8px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #89b4fa;
            }
        """)
        self._search_input.textChanged.connect(self._on_search)
        layout.addWidget(self._search_input)

        # ---- 滚动区域容器 ----
        self._scroll_widget = QWidget()
        self._scroll_layout = QVBoxLayout(self._scroll_widget)
        self._scroll_layout.setContentsMargins(0, 0, 0, 0)
        self._scroll_layout.setSpacing(0)
        self._scroll_layout.addStretch()
        layout.addWidget(self._scroll_widget)

    # ---- 公开方法 ----

    def add_category(
        self, category: ToolCategory, tools: dict[str, ToolMeta]
    ) -> None:
        """添加一个分类及其工具列表"""
        if not tools:
            return

        # 分类标题
        collapsed = category in self._collapsed
        header = CategoryHeader(category, len(tools), collapsed)
        header.clicked.connect(self._on_category_clicked)
        self._category_headers[category] = header

        # 工具列表
        list_widget = QListWidget()
        list_widget.setVisible(not collapsed)
        list_widget.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
                padding: 0px;
            }
            QListWidget::item {
                color: #a6adc8;
                padding: 8px 12px 8px 24px;
                border: none;
                font-size: 13px;
            }
            QListWidget::item:hover {
                background-color: #313244;
                color: #cdd6f4;
            }
            QListWidget::item:selected {
                background-color: #45475a;
                color: #cdd6f4;
                border-left: 3px solid #cba6f7;
            }
        """)
        list_widget.itemClicked.connect(self._on_tool_clicked)

        for name, meta in tools.items():
            item = QListWidgetItem(f"{meta.icon} {meta.display_name}")
            item.setData(Qt.ItemDataRole.UserRole, name)
            item.setToolTip(meta.description)
            list_widget.addItem(item)
            self._tool_items[name] = item

        self._category_lists[category] = list_widget

        # 按顺序插入（在 stretch 之前）
        insert_index = self._scroll_layout.count() - 1
        self._scroll_layout.insertWidget(insert_index, header)
        self._scroll_layout.insertWidget(insert_index + 1, list_widget)

    def select_tool(self, name: str) -> None:
        """高亮选中的工具"""
        for item_name, item in self._tool_items.items():
            if item_name == name:
                item.setSelected(True)
                # 确保其所属分类展开
                for cat, lst in self._category_lists.items():
                    for i in range(lst.count()):
                        if lst.item(i) is item:
                            if cat in self._collapsed:
                                self._toggle_category(cat)
                            return

    def set_tool_count(self, count: int) -> None:
        """此方法已废弃，计数在外层主窗口更新状态栏"""
        pass

    def set_on_tool_selected(self, callback: Callable[[str], None]) -> None:
        """设置工具选择回调"""
        self._on_tool_selected = callback

    # ---- 内部方法 ----

    def _on_category_clicked(self, category: ToolCategory) -> None:
        self._toggle_category(category)

    def _toggle_category(self, category: ToolCategory) -> None:
        header = self._category_headers.get(category)
        lst = self._category_lists.get(category)
        if not header or not lst:
            return
        header.toggle()
        if category in self._collapsed:
            self._collapsed.discard(category)
            lst.setVisible(True)
        else:
            self._collapsed.add(category)
            lst.setVisible(False)

    def _on_tool_clicked(self, item: QListWidgetItem) -> None:
        name = item.data(Qt.ItemDataRole.UserRole)
        if name:
            self.tool_selected.emit(name)
            if self._on_tool_selected:
                self._on_tool_selected(name)

    def _on_search(self, text: str) -> None:
        """搜索过滤"""
        query = text.strip().lower()
        for cat, lst in self._category_lists.items():
            visible_count = 0
            for i in range(lst.count()):
                item = lst.item(i)
                name = item.data(Qt.ItemDataRole.UserRole)
                display = item.text().lower()
                matches = (not query) or (query in name.lower() or query in display)
                item.setHidden(not matches)
                if matches:
                    visible_count += 1
            # 自动展开/折叠匹配的分类
            header = self._category_headers.get(cat)
            if header and query:
                if visible_count > 0 and cat in self._collapsed:
                    self._toggle_category(cat)
                elif visible_count == 0 and cat not in self._collapsed:
                    self._toggle_category(cat)
