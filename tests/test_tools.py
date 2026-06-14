"""
工具集成测试 — 验证 19 个工具的全部注册/实例化/核心功能。
"""

import sys
import io
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# 预导入所有工具
from modules.info_gathering.whois_lookup import WhoisLookupTool
from modules.info_gathering.dns_lookup import DnsLookupTool
from modules.info_gathering.subdomain_discovery import SubdomainDiscoveryTool
from modules.info_gathering.port_scanner import PortScanTool
from modules.info_gathering.tech_fingerprint import FingerprintTool
from modules.web_testing.http_editor import HttpEditorTool
from modules.web_testing.dir_bruteforce import DirBruteforceTool
from modules.web_testing.xss_generator import XssGeneratorTool
from modules.web_testing.sqli_helper import SqliHelperTool
from modules.web_testing.url_analyzer import UrlAnalyzerTool
from modules.utilities.codec_tool import CodecTool
from modules.utilities.hash_calculator import HashCalculatorTool
from modules.utilities.jwt_debugger import JwtDebuggerTool
from modules.utilities.random_generator import RandomGeneratorTool
from modules.utilities.diff_tool import DiffTool
from modules.learning.owasp_top10 import OwaspTop10Tool
from modules.learning.checklist import ChecklistTool
from modules.learning.writeup_helper import WriteupHelperTool
from modules.learning.payload_library import PayloadLibraryTool


class TestToolRegistration(unittest.TestCase):
    """测试工具注册"""

    def test_all_19_tools_registered(self):
        from core.tool_registry import tool_registry
        self.assertGreaterEqual(tool_registry.tool_count, 19)

    def test_categories_present(self):
        from core.tool_registry import tool_registry
        from core.tool_base import ToolCategory
        cats = tool_registry.get_categories()
        self.assertIn(ToolCategory.INFO_GATHERING, cats)
        self.assertIn(ToolCategory.WEB_TESTING, cats)
        self.assertIn(ToolCategory.UTILITIES, cats)
        self.assertIn(ToolCategory.LEARNING, cats)

    def test_all_tools_instantiable(self):
        from core.tool_registry import tool_registry
        for name, cls in tool_registry.get_all_tools().items():
            instance = cls()
            self.assertIsNotNone(instance, f"{name} should be instantiable")
            self.assertTrue(hasattr(instance, 'output_ready'), f"{name} should have output_ready signal")
            self.assertTrue(hasattr(instance, 'meta'), f"{name} should have meta")


class TestInfoGathering(unittest.TestCase):
    """信息收集工具功能测试"""

    def test_whois_lookup(self):
        tool = WhoisLookupTool()
        # 参数验证
        self.assertEqual(len(tool.validate_params({"target": ""})), 1)
        self.assertEqual(len(tool.validate_params({"target": "example.com"})), 0)
        # 执行
        result = tool.execute({"target": "example.com", "server": None})
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 100)

    def test_dns_lookup(self):
        tool = DnsLookupTool()
        result = tool.execute({
            "domain": "example.com",
            "dns_server": "8.8.8.8",
            "record_types": ["A", "MX"],
        })
        self.assertIn("example.com", result)
        self.assertGreater(len(result["example.com"]), 0)

    def test_tech_fingerprint(self):
        tool = FingerprintTool()
        result = tool.execute({"url": "https://httpbin.org"})
        self.assertIn("findings", result)
        self.assertIsInstance(result["findings"], dict)


class TestWebTesting(unittest.TestCase):
    """Web 测试工具功能测试"""

    def test_url_analyzer(self):
        tool = UrlAnalyzerTool()
        result = tool.execute({"urls": ["https://example.com/page?id=123&name=test"]})
        self.assertGreater(len(result), 0)
        self.assertEqual(result[0]["name"], "id")
        self.assertEqual(result[0]["decoded"], "123")

    def test_xss_generator_has_payloads(self):
        from modules.web_testing.xss_generator import XSS_PAYLOADS
        self.assertEqual(len(XSS_PAYLOADS), 7)
        self.assertIn("基础测试", XSS_PAYLOADS)
        self.assertIn("WAF 绕过", XSS_PAYLOADS)

    def test_sqli_helper_has_payloads(self):
        from modules.web_testing.sqli_helper import SQLI_PAYLOADS
        self.assertGreaterEqual(len(SQLI_PAYLOADS), 5)
        self.assertIn("联合查询 (UNION)", SQLI_PAYLOADS)
        self.assertIn("报错注入", SQLI_PAYLOADS)

    def test_dir_bruteforce_wordlist(self):
        from modules.web_testing.dir_bruteforce import DEFAULT_WORDLIST
        self.assertGreater(len(DEFAULT_WORDLIST), 50)


class TestUtilities(unittest.TestCase):
    """实用工具功能测试"""

    def test_codec_base64(self):
        tool = CodecTool()
        result = tool.execute({
            "text": "hello",
            "chain": [("Base64 编码", "encode", "Base64")],
        })
        self.assertEqual(result, "aGVsbG8=")

    def test_codec_chain(self):
        tool = CodecTool()
        result = tool.execute({
            "text": "hello",
            "chain": [
                ("Base64 编码", "encode", "Base64"),
                ("Base64 编码", "decode", "Base64"),
            ],
        })
        self.assertEqual(result, "hello")

    def test_hash_md5(self):
        tool = HashCalculatorTool()
        result = tool.execute({
            "text": "hello",
            "algorithms": ["MD5"],
            "hmac_key": "",
        })
        self.assertEqual(result["MD5"], "5d41402abc4b2a76b9719d911017c592")

    def test_hash_sha256(self):
        tool = HashCalculatorTool()
        result = tool.execute({
            "text": "hello",
            "algorithms": ["SHA256"],
            "hmac_key": "",
        })
        self.assertEqual(
            result["SHA256"],
            "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
        )

    def test_jwt_decode(self):
        tool = JwtDebuggerTool()
        test_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        result = tool.execute({"token": test_jwt})
        self.assertEqual(result["header"]["alg"], "HS256")
        self.assertEqual(result["payload"]["sub"], "1234567890")

    def test_random_uuid(self):
        tool = RandomGeneratorTool()
        result = tool.execute({"type": "UUID v4", "length": 36, "count": 3})
        self.assertEqual(len(result), 3)
        for uid in result:
            self.assertEqual(len(uid), 36)

    def test_random_password(self):
        tool = RandomGeneratorTool()
        result = tool.execute({
            "type": "安全密码", "length": 20, "count": 1,
            "upper": True, "lower": True, "digits": True, "symbols": True,
            "no_ambiguous": False,
        })
        self.assertEqual(len(result[0]), 20)

    def test_diff_identical(self):
        tool = DiffTool()
        result = tool.execute({
            "text_a": "hello\nworld",
            "text_b": "hello\nworld",
        })
        self.assertTrue(result["identical"])

    def test_diff_different(self):
        tool = DiffTool()
        result = tool.execute({
            "text_a": "hello\nworld",
            "text_b": "hello\nuniverse",
        })
        self.assertFalse(result["identical"])
        self.assertEqual(result["added"], 1)
        self.assertEqual(result["removed"], 1)


class TestLearning(unittest.TestCase):
    """学习资源工具测试"""

    def test_owasp_data(self):
        from modules.learning.owasp_top10 import OWASP_DATA
        self.assertEqual(len(OWASP_DATA), 10)
        self.assertEqual(OWASP_DATA[0]["id"], "A01:2021")

    def test_checklist_categories(self):
        from modules.learning.checklist import CHECKLIST
        self.assertGreaterEqual(len(CHECKLIST), 6)
        self.assertIn("信息收集", CHECKLIST)
        self.assertIn("注入攻击", CHECKLIST)

    def test_writeup_templates(self):
        from modules.learning.writeup_helper import WRITEUP_TEMPLATES
        self.assertIn("漏洞盒子标准", WRITEUP_TEMPLATES)
        self.assertIn("补天平台", WRITEUP_TEMPLATES)

    def test_payload_library(self):
        from modules.learning.payload_library import PAYLOAD_LIBRARY
        self.assertGreaterEqual(len(PAYLOAD_LIBRARY), 5)
        self.assertIn("XSS", PAYLOAD_LIBRARY)
        self.assertIn("SQL 注入", PAYLOAD_LIBRARY)


class TestToolWorker(unittest.TestCase):
    """测试后台线程"""

    def test_threaded_runner(self):
        from core.tool_worker import ThreadedToolRunner
        from modules.utilities.hash_calculator import HashCalculatorTool
        tool = HashCalculatorTool()
        runner = ThreadedToolRunner(tool)
        self.assertFalse(runner.is_running)

    def test_tool_worker_creation(self):
        from core.tool_worker import ToolWorker
        worker = ToolWorker(lambda p: p, {"key": "value"})
        self.assertIsNotNone(worker)


if __name__ == "__main__":
    unittest.main(verbosity=2)
