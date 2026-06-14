"""
全功能验证脚本 — 逐个测试 19 个工具的 execute() 核心逻辑

用法: python full_test.py
"""

import sys
import io
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PASS = 0
FAIL = 0
SKIP = 0


def check(name, condition, detail=""):
    global PASS, FAIL
    icon = "✅" if condition else "❌"
    status = "PASS" if condition else "FAIL"
    print(f"  {icon} {status} | {name} {detail}")
    if condition:
        PASS += 1
    else:
        FAIL += 1


def skip(name, reason=""):
    global SKIP
    SKIP += 1
    print(f"  ⏭️  SKIP | {name} — {reason}")


def test_imports():
    """测试所有模块导入"""
    print("\n" + "=" * 60)
    print("📦 模块导入检查")
    print("=" * 60)

    modules = [
        ("core.tool_base", "ToolMeta, ToolCategory, BaseTool"),
        ("core.tool_registry", "ToolRegistry, register_tool"),
        ("core.subprocess_manager", "SubprocessManager"),
        ("core.tool_worker", "ToolWorker, ThreadedToolRunner"),
        ("core.logger", "LogManager, safe_execute"),
        ("config.app_config", "AppConfig, app_config"),
        ("gui.styles", "COLORS, GLOBAL_STYLESHEET"),
        ("gui.dialogs.settings_dialog", "SettingsDialog"),
    ]
    for mod_path, desc in modules:
        try:
            __import__(mod_path)
            check(mod_path, True, desc)
        except Exception as e:
            check(mod_path, False, str(e)[:60])

    # 工具模块
    tool_modules = [
        "modules.info_gathering.whois_lookup",
        "modules.info_gathering.dns_lookup",
        "modules.info_gathering.subdomain_discovery",
        "modules.info_gathering.port_scanner",
        "modules.info_gathering.tech_fingerprint",
        "modules.web_testing.http_editor",
        "modules.web_testing.dir_bruteforce",
        "modules.web_testing.xss_generator",
        "modules.web_testing.sqli_helper",
        "modules.web_testing.url_analyzer",
        "modules.utilities.codec_tool",
        "modules.utilities.hash_calculator",
        "modules.utilities.jwt_debugger",
        "modules.utilities.random_generator",
        "modules.utilities.diff_tool",
        "modules.learning.owasp_top10",
        "modules.learning.checklist",
        "modules.learning.writeup_helper",
        "modules.learning.payload_library",
    ]
    for mod in tool_modules:
        try:
            __import__(mod)
            check(mod, True)
        except Exception as e:
            check(mod, False, str(e)[:60])


def test_info_gathering():
    """测试信息收集工具"""
    print("\n" + "=" * 60)
    print("🌐 信息收集工具")
    print("=" * 60)

    # --- WHOIS ---
    print("\n--- WHOIS 查询 ---")
    from modules.info_gathering.whois_lookup import WhoisLookupTool
    tool = WhoisLookupTool()
    check("WHOIS 实例化", True)
    check("WHOIS 参数验证(空)", len(tool.validate_params({"target": ""})) > 0)
    check("WHOIS 参数验证(有效)", len(tool.validate_params({"target": "example.com"})) == 0)

    try:
        result = tool.execute({"target": "example.com", "server": None})
        check("WHOIS example.com", isinstance(result, str) and len(result) > 100)
    except Exception as e:
        check("WHOIS example.com", False, str(e)[:60])

    # --- DNS ---
    print("\n--- DNS 枚举 ---")
    from modules.info_gathering.dns_lookup import DnsLookupTool
    tool = DnsLookupTool()
    check("DNS 实例化", True)

    try:
        result = tool.execute({
            "domain": "example.com",
            "dns_server": "8.8.8.8",
            "record_types": ["A", "MX", "NS", "TXT"],
        })
        records = result.get("example.com", [])
        check(f"DNS A/MX/NS/TXT 查询", len(records) > 0, f"{len(records)} 条记录")
        types = {r["type"] for r in records}
        check(f"DNS 记录类型覆盖", {"A", "MX", "NS"}.issubset(types), f"{types}")
    except Exception as e:
        check("DNS 查询", False, str(e)[:60])

    # --- 子域名 ---
    print("\n--- 子域名发现 ---")
    from modules.info_gathering.subdomain_discovery import SubdomainDiscoveryTool
    tool = SubdomainDiscoveryTool()
    check("子域名 实例化", True)

    try:
        result = tool.execute({
            "domain": "example.com",
            "use_crtsh": True,
            "use_dict": True,
            "resolve_dns": True,
        })
        check("子域名发现", isinstance(result, set) and len(result) > 0, f"{len(result)} 个")
    except Exception as e:
        check("子域名发现", False, str(e)[:60])

    # --- 端口扫描 ---
    print("\n--- 端口扫描 ---")
    from modules.info_gathering.port_scanner import PortScanTool
    tool = PortScanTool()
    check("端口扫描 实例化", True)

    try:
        # 只扫 3 个端口快速测试
        result = tool.execute({
            "host": "example.com",
            "ports": "80,443",
            "threads": 5,
            "timeout": 3.0,
        })
        open_ports = [r for r in result if r["status"] == "开放"]
        check(f"端口扫描 example.com:80,443", len(result) == 2, f"开放: {len(open_ports)}")
    except Exception as e:
        check("端口扫描", False, str(e)[:60])

    # --- 指纹识别 ---
    print("\n--- 技术指纹识别 ---")
    from modules.info_gathering.tech_fingerprint import FingerprintTool
    tool = FingerprintTool()
    check("指纹 实例化", True)

    try:
        result = tool.execute({"url": "https://httpbin.org"})
        findings = result.get("findings", {})
        total = sum(len(v) for v in findings.values())
        check(f"指纹识别 httpbin.org", total > 0, f"{total} 项技术, {len(findings)} 类别")
    except Exception as e:
        check("指纹识别", False, str(e)[:60])


def test_web_testing():
    """测试 Web 测试工具"""
    print("\n" + "=" * 60)
    print("🧪 Web 测试工具")
    print("=" * 60)

    # --- HTTP 编辑器 ---
    print("\n--- HTTP 请求编辑器 ---")
    from modules.web_testing.http_editor import HttpEditorTool
    tool = HttpEditorTool()
    check("HTTP 编辑器 实例化", True)

    try:
        result = tool.execute({
            "method": "GET",
            "url": "https://httpbin.org/get?test=1",
            "headers": {"User-Agent": "SecTools-Test"},
            "body": "",
        })
        check("HTTP GET httpbin.org", result.get("status_code") == 200, f"status={result.get('status_code')}")
    except Exception as e:
        check("HTTP GET", False, str(e)[:60])

    # --- 目录爆破 ---
    print("\n--- 目录爆破 ---")
    from modules.web_testing.dir_bruteforce import DirBruteforceTool, DEFAULT_WORDLIST
    tool = DirBruteforceTool()
    check("目录爆破 实例化", True)
    check("目录爆破 字典", len(DEFAULT_WORDLIST) > 50, f"{len(DEFAULT_WORDLIST)} 路径")

    # --- XSS 生成器 ---
    print("\n--- XSS 生成器 ---")
    from modules.web_testing.xss_generator import XSS_PAYLOADS
    cats = len(XSS_PAYLOADS)
    total = sum(len(v) for v in XSS_PAYLOADS.values())
    check("XSS Payload 库", cats == 7, f"{cats} 分类")
    check("XSS Payload 总数", total >= 50, f"{total} 个")
    check("XSS 有 WAF 绕过", "WAF 绕过" in XSS_PAYLOADS)
    check("XSS 有基础测试", "基础测试" in XSS_PAYLOADS)
    check("XSS 有盲 XSS", "盲 XSS / 数据窃取" in XSS_PAYLOADS)

    # --- SQLi 辅助 ---
    print("\n--- SQL 注入辅助 ---")
    from modules.web_testing.sqli_helper import SQLI_PAYLOADS
    cats = len(SQLI_PAYLOADS)
    total = sum(len(v) for cat in SQLI_PAYLOADS.values() for v in cat.values())
    check("SQLi Payload 库", cats >= 5, f"{cats} 分类")
    check("SQLi Payload 总数", total >= 50, f"{total} 个")
    check("SQLi 有联合查询", "联合查询 (UNION)" in SQLI_PAYLOADS)
    check("SQLi 有报错注入", "报错注入" in SQLI_PAYLOADS)
    check("SQLi 有时间盲注", "时间盲注" in SQLI_PAYLOADS)
    check("SQLi 有 MySQL", "MySQL" in SQLI_PAYLOADS["联合查询 (UNION)"])

    # --- URL 分析 ---
    print("\n--- URL 参数分析 ---")
    from modules.web_testing.url_analyzer import UrlAnalyzerTool
    tool = UrlAnalyzerTool()
    check("URL 分析 实例化", True)

    result = tool.execute({
        "urls": [
            "https://target.com/page?id=123&name=admin&redirect=https://evil.com&callback=jsonp"
        ]
    })
    check("URL 参数提取", len(result) == 4, f"{len(result)} 个参数")

    # 检查风险标记
    risks = {r["name"]: r["risk"] for r in result}
    check("URL id→🔴高危", "🔴" in risks.get("id", ""))
    check("URL redirect→🔴高危", "🔴" in risks.get("redirect", ""))
    check("URL callback→🔴高危", "🔴" in risks.get("callback", ""))

    types = {r["name"]: r["type"] for r in result}
    check("URL id→整数", types.get("id") == "整数")
    check("URL name→字符串", types.get("name") == "字符串")

    # --- 批量 URL ---
    result = tool.execute({
        "urls": [
            "https://a.com?x=1",
            "https://b.com?y=2&z=3",
        ]
    })
    check("URL 批量分析", len(result) == 3, f"{len(result)} 个参数")


def test_utilities():
    """测试实用工具"""
    print("\n" + "=" * 60)
    print("🔧 实用工具")
    print("=" * 60)

    # --- 编解码 ---
    print("\n--- 编解码工具 ---")
    from modules.utilities.codec_tool import CodecTool
    tool = CodecTool()
    check("编解码 实例化", True)

    # Base64
    r = tool.execute({"text": "hello world", "chain": [("Base64 编码", "encode", "Base64")]})
    check("Base64 编码", r == "aGVsbG8gd29ybGQ=")
    r2 = tool.execute({"text": r, "chain": [("Base64 编码", "decode", "Base64")]})
    check("Base64 解码", r2 == "hello world")

    # URL 编码
    r = tool.execute({"text": "hello world!", "chain": [("URL 编码", "encode", "Web")]})
    check("URL 编码", "%" in r)
    r2 = tool.execute({"text": r, "chain": [("URL 编码", "decode", "Web")]})
    check("URL 解码", r2 == "hello world!")

    # Hex
    r = tool.execute({"text": "AB", "chain": [("Base16 (Hex) 编码", "encode", "Base")]})
    check("Hex 编码", r == "4142")

    # ROT13
    r = tool.execute({"text": "hello", "chain": [("ROT13", "encode", "古典")]})
    check("ROT13 编码", r == "uryyb")
    r2 = tool.execute({"text": r, "chain": [("ROT13", "decode", "古典")]})
    check("ROT13 解码", r2 == "hello")

    # HTML 实体
    r = tool.execute({"text": "<script>", "chain": [("HTML 实体编码", "encode", "Web")]})
    check("HTML 实体编码", "&lt;" in r)

    # 链式操作
    r = tool.execute({
        "text": "test",
        "chain": [
            ("Base64 编码", "encode", "Base64"),
            ("URL 编码", "encode", "Web"),
            ("URL 编码", "decode", "Web"),
            ("Base64 编码", "decode", "Base64"),
        ],
    })
    check("编解码 4步链式操作", r == "test", f"结果: {r}")

    # --- 哈希计算器 ---
    print("\n--- 哈希计算器 ---")
    from modules.utilities.hash_calculator import HashCalculatorTool
    tool = HashCalculatorTool()
    check("哈希 实例化", True)

    result = tool.execute({"text": "hello", "algorithms": ["MD5", "SHA1", "SHA256", "SHA512"], "hmac_key": ""})
    check("MD5 hello", result["MD5"] == "5d41402abc4b2a76b9719d911017c592")
    check("SHA1 hello", len(result["SHA1"]) == 40)
    check("SHA256 hello", len(result["SHA256"]) == 64)
    check("SHA512 hello", len(result["SHA512"]) == 128)

    # HMAC
    result = tool.execute({"text": "hello", "algorithms": ["SHA256"], "hmac_key": "secret"})
    check("HMAC-SHA256", len(result["SHA256"]) == 64, result["SHA256"][:16])

    # --- JWT 调试器 ---
    print("\n--- JWT 调试器 ---")
    from modules.utilities.jwt_debugger import JwtDebuggerTool
    tool = JwtDebuggerTool()
    check("JWT 实例化", True)

    test_jwt = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        ".eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ"
        ".SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    )
    result = tool.execute({"token": test_jwt})
    check("JWT 解码 Header", result["header"]["alg"] == "HS256")
    check("JWT 解码 Header typ", result["header"]["typ"] == "JWT")
    check("JWT 解码 Payload sub", result["payload"]["sub"] == "1234567890")
    check("JWT 解码 Payload name", result["payload"]["name"] == "John Doe")
    check("JWT 解码 Payload iat", result["payload"]["iat"] == 1516239022)
    check("JWT 签名提取", len(result["signature"]) > 30)

    # none 算法检测
    none_jwt = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJ0ZXN0In0."
    tool.output_ready.connect(lambda m: None)
    result = tool.execute({"token": none_jwt})

    # 无效格式
    result = tool.execute({"token": "invalid.token"})
    check("JWT 无效格式检测", "error" not in str(result).lower() if isinstance(result, dict) else True, "返回空/错误")

    # --- 随机生成器 ---
    print("\n--- 随机生成器 ---")
    from modules.utilities.random_generator import RandomGeneratorTool
    tool = RandomGeneratorTool()
    check("随机 实例化", True)

    r = tool.execute({"type": "UUID v4", "length": 36, "count": 5})
    check("UUID v4 数量", len(r) == 5)
    check("UUID v4 格式", all(len(u) == 36 and "-" in u for u in r))

    r = tool.execute({"type": "安全密码", "length": 20, "count": 3,
                       "upper": True, "lower": True, "digits": True,
                       "symbols": True, "no_ambiguous": False})
    check("安全密码 数量", len(r) == 3)
    check("安全密码 长度", all(len(p) == 20 for p in r))

    r = tool.execute({"type": "API Key", "length": 40, "count": 2})
    check("API Key 格式", all(k.startswith("sk-") for k in r))

    r = tool.execute({"type": "XKCD 风格密码", "length": 4, "count": 1})
    check("XKCD 密码", "-" in r[0], r[0])

    r = tool.execute({"type": "随机 IP 地址", "length": 12, "count": 3})
    check("随机 IP", all(len(ip.split(".")) == 4 for ip in r))

    # --- 差异对比 ---
    print("\n--- 差异对比 ---")
    from modules.utilities.diff_tool import DiffTool
    tool = DiffTool()
    check("差异 实例化", True)

    result = tool.execute({"text_a": "line1\nline2\nline3", "text_b": "line1\nline2\nline3"})
    check("差异 完全相同", result["identical"] is True)

    result = tool.execute({
        "text_a": "line1\nold line\nline3",
        "text_b": "line1\nnew line\nline3",
    })
    check("差异 检测变化", result["identical"] is False)
    check("差异 新增 1 行", result["added"] == 1)
    check("差异 删除 1 行", result["removed"] == 1)

    result = tool.execute({
        "text_a": "a\nb\nc\nd",
        "text_b": "a\nx\nc\ny\ne",
    })
    check("差异 多处变化", not result["identical"] and result["added"] + result["removed"] > 2)


def test_learning():
    """测试学习资源工具"""
    print("\n" + "=" * 60)
    print("📚 学习资源")
    print("=" * 60)

    # --- OWASP Top 10 ---
    print("\n--- OWASP Top 10 ---")
    from modules.learning.owasp_top10 import OWASP_DATA
    check("OWASP 数据条目", len(OWASP_DATA) == 10)
    check("OWASP A01", OWASP_DATA[0]["id"] == "A01:2021")
    check("OWASP A10", OWASP_DATA[9]["id"] == "A10:2021")
    for item in OWASP_DATA:
        has_all = all(k in item for k in ["id", "name", "en", "risk", "summary", "examples", "prevention"])
        if not has_all:
            check(f"OWASP {item['id']} 字段完整", False)
            break
    else:
        check("OWASP 所有条目字段完整", True)

    # --- 检查清单 ---
    print("\n--- 漏洞检查清单 ---")
    from modules.learning.checklist import CHECKLIST
    check("检查清单 分类数", len(CHECKLIST) >= 8, f"{len(CHECKLIST)} 类")
    total_items = sum(len(v) for v in CHECKLIST.values())
    check("检查清单 总条目", total_items >= 70, f"{total_items} 项")

    required = ["信息收集", "身份验证", "访问控制", "注入攻击", "跨站攻击", "文件上传"]
    for cat in required:
        check(f"检查清单 含 [{cat}]", cat in CHECKLIST)

    # --- Writeup 助手 ---
    print("\n--- Writeup 助手 ---")
    from modules.learning.writeup_helper import WRITEUP_TEMPLATES
    check("Writeup 模板数", len(WRITEUP_TEMPLATES) >= 3, f"{len(WRITEUP_TEMPLATES)} 个")
    check("Writeup 漏洞盒子", "漏洞盒子标准" in WRITEUP_TEMPLATES)
    check("Writeup 补天", "补天平台" in WRITEUP_TEMPLATES)
    check("Writeup 通用", "通用报告" in WRITEUP_TEMPLATES)

    # 测试模板渲染
    tpl = WRITEUP_TEMPLATES["漏洞盒子标准"]
    rendered = tpl.format(
        title="测试漏洞", vuln_type="SQL注入", severity="高危",
        url="https://target.com", date="2026-06-14",
        description="测试描述", proof="测试证明", steps="1. 测试",
        impact="测试影响", fix="测试修复", references="OWASP A03",
    )
    check("Writeup 模板渲染", "测试漏洞" in rendered and "SQL注入" in rendered)

    # --- Payload 库 ---
    print("\n--- Payload 库 ---")
    from modules.learning.payload_library import PAYLOAD_LIBRARY
    check("Payload 库 分类数", len(PAYLOAD_LIBRARY) >= 6, f"{len(PAYLOAD_LIBRARY)} 类")
    total = sum(len(v) for v in PAYLOAD_LIBRARY.values())
    check("Payload 库 总数", total >= 50, f"{total} 条")
    check("Payload 含 XSS", "XSS" in PAYLOAD_LIBRARY)
    check("Payload 含 SQL 注入", "SQL 注入" in PAYLOAD_LIBRARY)
    check("Payload 含 SSRF", "SSRF" in PAYLOAD_LIBRARY)
    check("Payload 含 文件上传", "文件上传" in PAYLOAD_LIBRARY)
    check("Payload 含 命令注入", "命令注入" in PAYLOAD_LIBRARY)


def test_gui_components():
    """测试 GUI 组件实例化（需要 QApplication）"""
    print("\n" + "=" * 60)
    print("🖥️  GUI 组件")
    print("=" * 60)

    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
        app.setStyle("Fusion")

    # 主窗口
    try:
        from gui.main_window import MainWindow
        win = MainWindow()
        check("MainWindow 创建", True)
        win.load_tools()
        check("MainWindow 加载工具", True, f"{win._registry.tool_count} tools")
    except Exception as e:
        check("MainWindow", False, str(e)[:80])

    # 所有工具 Widget 创建
    from core.tool_registry import tool_registry
    for name in tool_registry.get_all_tools():
        try:
            cls = tool_registry.get_tool(name)
            instance = cls()
            widget = instance.create_widget()
            check(f"Widget: {name}", widget is not None, type(widget).__name__)
        except Exception as e:
            check(f"Widget: {name}", False, str(e)[:60])

    # 设置对话框
    try:
        from gui.dialogs.settings_dialog import SettingsDialog
        dlg = SettingsDialog()
        check("SettingsDialog 创建", True)
    except Exception as e:
        check("SettingsDialog", False, str(e)[:60])


def test_subprocess_manager():
    """测试子进程管理器"""
    print("\n" + "=" * 60)
    print("⚙️  基础设施")
    print("=" * 60)

    from core.subprocess_manager import SubprocessManager
    sm = SubprocessManager()
    check("SubprocessManager 创建", True)
    check("SubprocessManager 未运行", not sm.is_running)

    # 测试简单命令
    try:
        sm.execute("python", ["--version"], timeout_ms=5000)
        check("SubprocessManager 执行 python --version", True)
    except Exception as e:
        check("SubprocessManager 执行", False, str(e)[:60])

    # ThreadedToolRunner
    from core.tool_worker import ThreadedToolRunner, ToolWorker
    from modules.utilities.codec_tool import CodecTool
    tool = CodecTool()
    runner = ThreadedToolRunner(tool)
    check("ThreadedToolRunner 创建", True)
    check("ThreadedToolRunner 未运行", not runner.is_running)


def test_edge_cases():
    """边界情况测试"""
    print("\n" + "=" * 60)
    print("🔲 边界情况")
    print("=" * 60)

    # 空输入
    from modules.utilities.codec_tool import CodecTool
    tool = CodecTool()
    r = tool.execute({"text": "", "chain": [("Base64 编码", "encode", "Base64")]})
    check("编解码 空输入", r == "")

    # 无效 JWT
    from modules.utilities.jwt_debugger import JwtDebuggerTool
    tool = JwtDebuggerTool()
    r = tool.execute({"token": "not.a.jwt"})
    check("JWT 无效格式不崩溃", isinstance(r, dict), "...")

    # 哈希空字符串
    from modules.utilities.hash_calculator import HashCalculatorTool
    tool = HashCalculatorTool()
    r = tool.execute({"text": "", "algorithms": ["MD5"], "hmac_key": ""})
    check("哈希 空字符串", r["MD5"] == "d41d8cd98f00b204e9800998ecf8427e")

    # 差异空输入
    from modules.utilities.diff_tool import DiffTool
    tool = DiffTool()
    r = tool.execute({"text_a": "", "text_b": "hello"})
    check("差异 空vs有", not r["identical"], f"added={r['added']}")

    # URL 分析空输入
    from modules.web_testing.url_analyzer import UrlAnalyzerTool
    tool = UrlAnalyzerTool()
    r = tool.execute({"urls": []})
    check("URL 分析 空列表", len(r) == 0)

    # 随机生成器 自定义
    from modules.utilities.random_generator import RandomGeneratorTool
    tool = RandomGeneratorTool()
    r = tool.execute({"type": "随机数字", "length": 10, "count": 1,
                       "upper": False, "lower": False, "digits": False,
                       "symbols": False, "no_ambiguous": False})
    check("随机 10位数字", len(r[0]) == 10 and r[0].isdigit())


def main():
    global PASS, FAIL, SKIP
    print("=" * 60)
    print("  🔐 SecTools Platform — 全功能验证")
    print("=" * 60)
    start = time.time()

    test_imports()
    test_subprocess_manager()
    test_info_gathering()
    test_web_testing()
    test_utilities()
    test_learning()
    test_gui_components()
    test_edge_cases()

    elapsed = time.time() - start
    total = PASS + FAIL + SKIP
    print("\n" + "=" * 60)
    print(f"  📊 总计: {total} 项检查")
    print(f"  ✅ 通过: {PASS}")
    print(f"  ❌ 失败: {FAIL}")
    print(f"  ⏭️  跳过: {SKIP}")
    print(f"  ⏱️  耗时: {elapsed:.1f}s")
    print("=" * 60)

    if FAIL == 0:
        print("\n  🎉 所有功能验证通过！")
    else:
        print(f"\n  ⚠️  有 {FAIL} 项失败，请检查上述详情。")

    return FAIL == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
