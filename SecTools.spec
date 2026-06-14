# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置 — 将网络安全工具平台打包为单个 .exe 文件

构建命令:
    pyinstaller SecTools.spec
    输出: dist/SecTools.exe
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(".").resolve()

# ---- 收集所有 hidden imports ----
hiddenimports = [
    # PyQt6
    "PyQt6", "PyQt6.QtCore", "PyQt6.QtGui", "PyQt6.QtWidgets",
    # 核心模块
    "core", "core.tool_base", "core.tool_registry",
    "core.subprocess_manager", "core.tool_worker", "core.logger",
    # 配置
    "config", "config.app_config",
    # GUI
    "gui", "gui.main_window", "gui.styles",
    "gui.widgets", "gui.widgets.sidebar", "gui.widgets.tool_container",
    "gui.widgets.output_console", "gui.widgets.status_bar",
    "gui.dialogs", "gui.dialogs.settings_dialog",
    # 工具模块 - 信息收集
    "modules", "modules.info_gathering",
    "modules.info_gathering.whois_lookup",
    "modules.info_gathering.dns_lookup",
    "modules.info_gathering.subdomain_discovery",
    "modules.info_gathering.port_scanner",
    "modules.info_gathering.tech_fingerprint",
    # 工具模块 - Web 测试
    "modules.web_testing",
    "modules.web_testing.http_editor",
    "modules.web_testing.dir_bruteforce",
    "modules.web_testing.xss_generator",
    "modules.web_testing.sqli_helper",
    "modules.web_testing.url_analyzer",
    # 工具模块 - 实用工具
    "modules.utilities",
    "modules.utilities.codec_tool",
    "modules.utilities.hash_calculator",
    "modules.utilities.jwt_debugger",
    "modules.utilities.random_generator",
    "modules.utilities.diff_tool",
    # 工具模块 - 学习资源
    "modules.learning",
    "modules.learning.owasp_top10",
    "modules.learning.checklist",
    "modules.learning.writeup_helper",
    "modules.learning.payload_library",
    # 第三方库
    "whois", "dns", "dns.resolver",
    "jwt", "requests", "httpx",
    # Python 标准库（防止遗漏）
    "json", "hashlib", "base64", "html", "codecs",
    "secrets", "difflib", "logging", "logging.handlers",
    "urllib.parse", "concurrent.futures", "email", "email.mime",
    "socket", "ssl", "datetime", "pathlib", "re",
    # 编码相关
    "encodings.idna", "encodings.utf_8", "encodings.gbk",
]

# ---- 配置文件 ----
datas = [
    (str(PROJECT_ROOT / "config" / "default_config.json"), "config"),
    (str(PROJECT_ROOT / "README.md"), "."),
]

# ---- 图标 ----
icon_path = PROJECT_ROOT / "assets" / "icon.ico"
icon_file = str(icon_path) if icon_path.exists() else None

# ---- 分析 ----
a = Analysis(
    ["main.py"],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "pandas", "scipy"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="SecTools",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file,
)
