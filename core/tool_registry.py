"""
工具注册中心 — 单例模式，自动发现并管理所有安全工具。

工作流程:
  1. @register_tool 装饰器在模块导入时自动注册工具
  2. ToolRegistry 维护所有工具的注册表
  3. 启动时通过 import 各模块自动完成注册
  4. GUI 层通过 get_tools_by_category() 获取分类工具列表
"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path
from typing import Callable, Optional, Type

from core.tool_base import BaseTool, ToolCategory, ToolMeta


class ToolRegistry:
    """工具注册中心（单例模式）"""

    _instance: Optional["ToolRegistry"] = None
    _initialized: bool = False

    def __new__(cls) -> "ToolRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools: dict[str, Type[BaseTool]] = {}
            cls._instance._meta_map: dict[str, ToolMeta] = {}
        return cls._instance

    # ---- 注册 ----

    def register(self, tool_class: Type[BaseTool]) -> Type[BaseTool]:
        """注册一个工具类"""
        meta = tool_class.meta
        self._tools[meta.name] = tool_class
        self._meta_map[meta.name] = meta
        return tool_class

    # ---- 查询 ----

    def get_tool(self, name: str) -> Optional[Type[BaseTool]]:
        """根据名称获取工具类"""
        return self._tools.get(name)

    def get_meta(self, name: str) -> Optional[ToolMeta]:
        """获取工具元数据"""
        return self._meta_map.get(name)

    def get_all_tools(self) -> dict[str, Type[BaseTool]]:
        """获取所有已注册工具"""
        return dict(self._tools)

    def get_all_meta(self) -> dict[str, ToolMeta]:
        """获取所有工具元数据"""
        return dict(self._meta_map)

    def get_tools_by_category(self, category: ToolCategory) -> dict[str, ToolMeta]:
        """按分类获取工具元数据"""
        return {
            name: meta
            for name, meta in self._meta_map.items()
            if meta.category == category
        }

    def get_categories(self) -> dict[ToolCategory, dict[str, ToolMeta]]:
        """获取按分类组织的所有工具"""
        result: dict[ToolCategory, dict[str, ToolMeta]] = {}
        for cat in ToolCategory:
            tools = self.get_tools_by_category(cat)
            if tools:
                result[cat] = tools
        return result

    # ---- 自动发现 ----

    def auto_discover(self, modules_package: str = "modules") -> None:
        """自动发现并导入 modules/ 下的所有工具模块

        遍历 modules 包的子包，导入所有 .py 文件，
        @register_tool 装饰器在导入时自动完成注册。
        """
        try:
            package = importlib.import_module(modules_package)
            package_path = Path(package.__path__[0])  # type: ignore[attr-defined]

            for finder, name, is_pkg in pkgutil.iter_modules(
                [str(package_path)]
            ):
                if is_pkg:
                    # 子包（如 info_gathering），导入其中的所有模块
                    self._discover_subpackage(f"{modules_package}.{name}")
        except ModuleNotFoundError:
            pass   # modules 包不存在时跳过

    def _discover_subpackage(self, subpackage_name: str) -> None:
        """导入子包中的所有 .py 模块"""
        try:
            subpkg = importlib.import_module(subpackage_name)
            subpkg_path = Path(subpkg.__path__[0])  # type: ignore[attr-defined]

            for finder, name, is_pkg in pkgutil.iter_modules(
                [str(subpkg_path)]
            ):
                if not is_pkg and not name.startswith("_"):
                    try:
                        importlib.import_module(f"{subpackage_name}.{name}")
                    except ImportError as e:
                        print(f"[ToolRegistry] 无法导入 {subpackage_name}.{name}: {e}")
        except ModuleNotFoundError:
            pass

    @property
    def tool_count(self) -> int:
        """已注册工具数量"""
        return len(self._tools)


# ---- 全局单例 ----
tool_registry = ToolRegistry()


# ---- 装饰器 ----
def register_tool(tool_class: Type[BaseTool]) -> Type[BaseTool]:
    """@register_tool 装饰器 — 将工具类注册到全局注册中心"""
    return tool_registry.register(tool_class)
