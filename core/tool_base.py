"""
工具模块基类 — 所有安全工具的抽象基类。

每个工具模块继承 BaseTool，通过 ToolMeta 声明元数据，
使用 @register_tool 装饰器自动注册到 ToolRegistry。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QWidget


# 解决 QObject 和 ABC 的元类冲突
class _QObjectABC(type(QObject), type(ABC)):
    """QObject + ABC 的组合元类"""
    pass


class ToolCategory(Enum):
    """工具分类枚举"""
    INFO_GATHERING = "信息收集"
    WEB_TESTING = "Web 测试"
    UTILITIES = "实用工具"
    LEARNING = "学习资源"


@dataclass
class ToolMeta:
    """工具元数据 — 描述一个安全工具的基本信息"""
    name: str                           # 工具唯一标识，如 "whois_lookup"
    display_name: str                   # 显示名称，如 "WHOIS 查询"
    category: ToolCategory              # 所属分类
    description: str = ""               # 工具描述
    icon: str = "🛠️"                    # 图标（emoji 或路径）
    version: str = "1.0.0"             # 版本号
    author: str = ""                    # 作者
    keywords: list[str] = field(default_factory=list)  # 搜索关键词
    requires_external: list[str] = field(default_factory=list)  # 依赖的外部工具


class BaseTool(QObject, ABC, metaclass=_QObjectABC):
    """安全工具抽象基类

    所有工具模块必须继承此类并实现:
      - create_widget() -> QWidget: 返回工具的 UI 控件
      - execute(params: dict) -> Any: 执行工具逻辑
    """

    meta: ToolMeta

    # --- 信号 ---
    output_ready = pyqtSignal(str)
    progress_updated = pyqtSignal(int)
    finished = pyqtSignal(object)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

    @abstractmethod
    def create_widget(self) -> QWidget:
        """创建并返回工具的 UI 控件

        Returns:
            QWidget: 嵌入到主界面 QStackedWidget 中的工具面板
        """
        ...

    @abstractmethod
    def execute(self, params: dict[str, Any]) -> Any:
        """执行工具的核心逻辑

        Args:
            params: 工具参数，由 UI 控件收集后传入

        Returns:
            工具执行结果
        """
        ...

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        """验证参数，返回错误列表（空列表表示验证通过）"""
        return []

    def on_tab_activated(self) -> None:
        """当工具标签页被切换到时的回调（可选覆盖）"""
        pass

    def on_tab_deactivated(self) -> None:
        """当工具标签页被切换离开时的回调（可选覆盖）"""
        pass

    def cleanup(self) -> None:
        """工具被销毁时的清理工作（可选覆盖）"""
        pass
