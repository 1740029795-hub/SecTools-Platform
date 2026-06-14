# 🔐 网络安全工具平台 — SecTools Platform

> 为信息安全专业学生打造的集成化安全工具桌面应用

[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)
[![PyQt6](https://img.shields.io/badge/PyQt-6.x-green)](https://riverbankcomputing.com/software/pyqt)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 📖 简介

SecTools Platform 是一个**集成化网络安全工具平台**，将常用安全工具统一到现代化 GUI 中，降低学习门槛。适用于 Web 安全测试学习、漏洞挖掘辅助、以及漏洞盒子/补天等平台漏洞提交。

### ⚠️ 免责声明

**本工具仅供学习和授权的安全测试使用。** 禁止将本工具用于任何未经授权的渗透测试或非法活动。使用者应对自己的行为负责。

---

## ✨ 功能特性

- **插件式架构**：零配置添加新工具，`@register_tool` 装饰器自动注册
- **深色专业主题**：Catppuccin Mocha 暗色配色，护眼编程风格
- **19 个内置工具**：覆盖信息收集、Web 测试、实用工具、学习资源四大类别
- **后台线程执行**：QThread 异步执行，UI 永远不卡顿
- **统一输出控制台**：彩色日志、时间戳、自动滚动、一键清空
- **搜索导航**：侧边栏实时搜索过滤所有工具
- **历史记录**：HTTP 编辑器保留最近 50 条请求历史

---

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Windows 10/11（主要开发平台）
- （可选）Nmap 用于端口扫描

### 安装与启动

```bash
# 1. 进入项目目录
cd 安全上传漏洞平台

# 2. 创建虚拟环境
python -m venv .venv

# 3. 激活虚拟环境
.venv\Scripts\activate     # Windows

# 4. 安装依赖
pip install -r requirements.txt

# 5. 启动应用
python main.py
```

### 打包为单个 EXE

```bash
pip install pyinstaller
pyinstaller SecTools.spec
# 输出: dist/SecTools.exe
```

---

## 🧰 工具列表

### 🌐 信息收集 (5 个)

| 工具 | 说明 |
|------|------|
| **WHOIS 查询** | 查询域名/IP 注册信息，支持 python-whois + socket 双方案 |
| **DNS 枚举** | 查询 A/AAAA/MX/NS/CNAME/TXT/SOA 等 10 种 DNS 记录 |
| **子域名发现** | crt.sh 证书日志 + 字典爆破 + DNS 解析验证 |
| **端口扫描** | 内置 50+ 常用端口、150 扩展端口、自定义范围、Banner 抓取 |
| **技术指纹识别** | 识别 Web 服务器/CMS/CDN/JS 框架，100+ 签名规则 |

### 🧪 Web 测试 (5 个)

| 工具 | 说明 |
|------|------|
| **HTTP 请求编辑器** | 自定义 Method/Header/Body，响应查看，历史记录(50条)，JSON 美化 |
| **目录爆破** | 多线程目录/文件枚举，139 内置路径字典，状态码过滤 |
| **XSS Payload 生成器** | 7 类 54 个 Payload，上下文感知，5 种编码格式 |
| **SQL 注入辅助** | MySQL/MSSQL/Oracle/PG/SQLite 全覆盖，56 个 Payload |
| **URL 参数分析** | 参数提取/类型识别/注入风险评估(🔴🟡🟢) |

### 🔧 实用工具 (5 个)

| 工具 | 说明 |
|------|------|
| **编解码工具** | Base64/URL/Hex/Unicode/ROT13/HTML/二进制 **链式操作** |
| **哈希计算器** | MD5/SHA家族/SHA3/BLAKE2 + 文件哈希 + HMAC + 验证对比 |
| **JWT 调试器** | Token 解码/时间分析/none 算法检测/签名验证 |
| **随机生成器** | UUID/密码/API Key/Token/IP/MAC/Nano ID/XKCD 风格 |
| **差异对比** | 双栏文本 Diff + HTTP GET/POST 响应对比 |

### 📚 学习资源 (4 个)

| 工具 | 说明 |
|------|------|
| **OWASP Top 10** | 10 大类漏洞中文详解、示例和防护建议 |
| **漏洞检查清单** | 8 大分类 75+ 检查项，进度追踪，可导出 Markdown |
| **Writeup 助手** | 3 种模板(漏洞盒子/补天/通用)，表单填写，一键导出 |
| **Payload 库** | XSS/SQLi/SSRF/上传/命令注入/路径遍历 6 类 Payload，实时搜索 |

---

## 🏗️ 项目架构

```
安全上传漏洞平台/
├── main.py                       # 应用入口
├── SecTools.spec                 # PyInstaller 打包配置
├── requirements.txt
├── README.md
├── core/                         # 基础设施层
│   ├── tool_base.py              # BaseTool 抽象基类 (QObject+ABC)
│   ├── tool_registry.py          # 单例注册中心 + @register_tool 装饰器
│   ├── subprocess_manager.py     # QProcess 子进程管理器
│   ├── tool_worker.py            # QThread 后台执行引擎
│   └── logger.py                 # 统一日志系统
├── gui/                          # GUI 层
│   ├── main_window.py            # 主窗口 (菜单/侧边栏/工具区/状态栏)
│   ├── styles.py                 # 全局 QSS 样式常量
│   ├── widgets/
│   │   ├── sidebar.py            # 左侧分类导航 + 搜索
│   │   ├── tool_container.py     # QStackedWidget 工具页管理
│   │   ├── output_console.py     # 统一输出控制台
│   │   └── status_bar.py         # 状态栏 + 进度条
│   └── dialogs/
│       └── settings_dialog.py    # 设置对话框 (工具路径/代理/主题)
├── modules/                      # 工具模块 (插件式)
│   ├── info_gathering/           # 5 个信息收集工具
│   ├── web_testing/              # 5 个 Web 测试工具
│   ├── utilities/                # 5 个实用工具
│   └── learning/                 # 4 个学习资源
├── config/
│   ├── app_config.py             # 统一配置管理
│   └── default_config.json       # 默认配置文件
└── assets/                       # 图标等资源
```

### 添加新工具

只需 3 步：

```python
# 1. 在 modules/ 对应分类下创建文件
# 2. 继承 BaseTool，定义 meta
# 3. 添加 @register_tool 装饰器

from core.tool_base import BaseTool, ToolCategory, ToolMeta
from core.tool_registry import register_tool

@register_tool
class MyNewTool(BaseTool):
    meta = ToolMeta(
        name="my_tool",
        display_name="我的工具",
        category=ToolCategory.WEB_TESTING,
        description="工具描述",
        icon="🆕",
    )

    def create_widget(self):
        # 返回工具 UI
        pass

    def execute(self, params):
        # 工具逻辑
        pass
```

工具会被**自动发现**并注册到侧边栏，无需修改任何其他代码。

---

## ⌨️ 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+L` | 清空输出控制台 |
| `Ctrl+F` | 聚焦搜索框 |
| `Ctrl+S` | 导出输出 |
| `Ctrl+Q` | 退出应用 |
| `Ctrl+,` | 打开设置 |
| `F5` | 刷新工具列表 |

---

## 🔧 配置

配置文件位置：`%APPDATA%/SecTools/config.json`

可通过菜单 **设置 → 系统设置** 修改：
- 外部工具路径 (Nmap/SQLMap/Dirb/Nikto)
- HTTP/HTTPS 代理
- 主题切换 (暗色/亮色)
- 默认线程数和超时时间
- SSL 证书验证

---

## 📦 技术栈

| 技术 | 用途 |
|------|------|
| Python 3.10+ | 主语言 |
| PyQt6 | GUI 框架 |
| python-whois | WHOIS 查询 |
| dnspython | DNS 解析 |
| python-nmap | Nmap 集成 |
| PyJWT | JWT 解析 |
| requests / httpx | HTTP 客户端 |
| PyInstaller | 打包为 exe |

---

## 📝 更新日志

### v1.0.0 (2026-06)

- 🎉 首个完整版本发布
- ✅ 19 个内置安全工具
- 🎨 Catppuccin 暗色主题
- 🧵 后台线程执行引擎
- ⚙️ 设置对话框 (工具路径/代理/主题)
- 📦 PyInstaller 单文件打包支持

---

## 📄 License

MIT License
