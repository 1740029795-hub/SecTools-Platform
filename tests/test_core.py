"""
核心模块单元测试 — tool_base, tool_registry, app_config, logger, styles
"""

import sys
import io
import os
import json
import tempfile
import unittest
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


class TestToolMeta(unittest.TestCase):
    """测试 ToolMeta 数据类"""

    def test_create_meta(self):
        from core.tool_base import ToolMeta, ToolCategory
        meta = ToolMeta(
            name="test_tool",
            display_name="测试工具",
            category=ToolCategory.INFO_GATHERING,
            description="测试描述",
            icon="🧪",
        )
        self.assertEqual(meta.name, "test_tool")
        self.assertEqual(meta.display_name, "测试工具")
        self.assertEqual(meta.category, ToolCategory.INFO_GATHERING)
        self.assertEqual(meta.icon, "🧪")
        self.assertEqual(meta.version, "1.0.0")  # default

    def test_default_values(self):
        from core.tool_base import ToolMeta, ToolCategory
        meta = ToolMeta(name="test", display_name="Test", category=ToolCategory.UTILITIES)
        self.assertEqual(meta.description, "")
        self.assertEqual(meta.author, "")
        self.assertEqual(meta.keywords, [])
        self.assertEqual(meta.requires_external, [])


class TestToolRegistry(unittest.TestCase):
    """测试 ToolRegistry 单例和注册"""

    @classmethod
    def setUpClass(cls):
        # 确保所有工具已导入注册
        from modules.info_gathering import whois_lookup, dns_lookup, subdomain_discovery, port_scanner, tech_fingerprint  # noqa
        from modules.web_testing import http_editor, dir_bruteforce, xss_generator, sqli_helper, url_analyzer  # noqa
        from modules.utilities import codec_tool, hash_calculator, jwt_debugger, random_generator, diff_tool  # noqa
        from modules.learning import owasp_top10, checklist, writeup_helper, payload_library  # noqa
        from core.tool_registry import tool_registry
        cls.registry = tool_registry

    def test_singleton(self):
        from core.tool_registry import ToolRegistry
        r1 = ToolRegistry()
        r2 = ToolRegistry()
        self.assertIs(r1, r2)

    def test_register_tool(self):
        from core.tool_base import BaseTool, ToolMeta, ToolCategory
        from core.tool_registry import register_tool

        @register_tool
        class _TestTool(BaseTool):
            meta = ToolMeta(name="test_register", display_name="Test", category=ToolCategory.UTILITIES)
            def create_widget(self): pass
            def execute(self, params): pass

        tool_cls = self.registry.get_tool("test_register")
        self.assertIsNotNone(tool_cls)
        self.assertEqual(tool_cls.meta.name, "test_register")

    def test_get_tools_by_category(self):
        from core.tool_base import ToolCategory
        tools = self.registry.get_tools_by_category(ToolCategory.INFO_GATHERING)
        self.assertIn("whois_lookup", tools)

    def test_get_categories(self):
        categories = self.registry.get_categories()
        self.assertGreaterEqual(len(categories), 3)


class TestAppConfig(unittest.TestCase):
    """测试 AppConfig"""

    def setUp(self):
        from config.app_config import AppConfig
        self.config = AppConfig()

    def test_singleton(self):
        from config.app_config import AppConfig
        self.assertIs(self.config, AppConfig())

    def test_defaults(self):
        self.assertEqual(self.config.get("theme"), "dark")
        self.assertEqual(self.config.get("max_threads"), 10)

    def test_get_set(self):
        self.config.set("test.key", "value")
        self.assertEqual(self.config.get("test.key"), "value")

    def test_deep_path(self):
        self.config.set("proxy.http", "http://127.0.0.1:8080")
        self.assertEqual(self.config.get("proxy.http"), "http://127.0.0.1:8080")
        self.assertEqual(self.config.get("proxy.nonexistent", "fallback"), "fallback")

    def test_save_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "config.json")
            self.config.set("test_save", True)
            self.config.save(filepath)
            self.assertTrue(os.path.exists(filepath))

            # Load into new config
            from config.app_config import AppConfig
            config2 = AppConfig()
            config2._data = dict(AppConfig.DEFAULTS)
            config2.load(filepath)
            self.assertTrue(config2.get("test_save"))


class TestLogger(unittest.TestCase):
    """测试日志系统"""

    def test_init(self):
        from core.logger import LogManager
        lm = LogManager()
        logger = lm.init(level="DEBUG", log_dir=tempfile.gettempdir())
        self.assertIsNotNone(logger)
        logger.debug("test message")
        logger.info("test info")

    def test_safe_execute(self):
        from core.logger import safe_execute

        @safe_execute
        def func_ok():
            return 42

        self.assertEqual(func_ok(), 42)

        @safe_execute
        def func_fail():
            raise ValueError("test error")

        with self.assertRaises(ValueError):
            func_fail()


class TestStyles(unittest.TestCase):
    """测试全局样式"""

    def test_colors(self):
        from gui.styles import COLORS
        self.assertIn("base", COLORS)
        self.assertIn("text", COLORS)
        self.assertIn("blue", COLORS)
        self.assertEqual(len(COLORS), 20)

    def test_stylesheet_components(self):
        from gui.styles import (
            GROUP_BOX, LINE_EDIT, TEXT_EDIT, TABLE,
            BUTTON_PRIMARY, BUTTON_SECONDARY, GLOBAL_STYLESHEET,
        )
        self.assertIn("QGroupBox", GROUP_BOX)
        self.assertIn("QLineEdit", LINE_EDIT)
        self.assertIn("QTableWidget", TABLE)
        self.assertIn("QPushButton", BUTTON_PRIMARY)
        self.assertIn("QMainWindow", GLOBAL_STYLESHEET)


if __name__ == "__main__":
    unittest.main(verbosity=2)
