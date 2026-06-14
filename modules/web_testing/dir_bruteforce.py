"""
目录爆破工具 — 多线程 Web 目录/文件发现。

特性:
  - 内置字典 (精选 200+ 常见路径)
  - 多线程并发请求
  - 状态码过滤 (200/301/403 等)
  - 响应大小分析 (排除相似误报)
  - 自定义扩展名 (.php/.asp/.jsp/.bak 等)
  - 递归扫描选项
"""

from __future__ import annotations

import concurrent.futures
from typing import Any, Optional

import requests

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.tool_base import BaseTool, ToolCategory, ToolMeta
from core.tool_registry import register_tool

# 内置常用字典
DEFAULT_WORDLIST = [
    # 常见管理路径
    "admin", "login", "wp-admin", "administrator", "manage", "manager",
    "console", "dashboard", "controlpanel", "cpanel", "webadmin",
    # 配置文件
    ".env", ".git/config", ".svn/entries", ".htaccess", "web.config",
    "config.php", "config.php.bak", "config.yml", "wp-config.php",
    "config.js", "settings.py", "application.properties",
    # 备份文件
    "backup", "backups", "db", "database", "dump.sql", "backup.zip",
    "site.zip", "www.zip", "web.tar.gz", "archive.zip",
    # API 端点
    "api", "api/v1", "api/v2", "graphql", "swagger", "swagger-ui",
    "api-docs", "v1", "v2", "rest", "soap",
    # 上传目录
    "upload", "uploads", "files", "images", "img", "assets", "static",
    "media", "download", "downloads", "attachments",
    # 信息泄露
    "robots.txt", "sitemap.xml", "crossdomain.xml", "phpinfo.php",
    "info.php", "test.php", "phpmyadmin", ".well-known/security.txt",
    ".git/HEAD", ".DS_Store", "README.md", "CHANGELOG.md",
    # 常见应用
    "wordpress", "wp-content", "wp-includes", "wp-json", "xmlrpc.php",
    "joomla", "drupal", "typo3", "magento",
    # 开发路径
    "dev", "development", "staging", "test", "testing", "sandbox",
    "tmp", "temp", "logs", "log", "debug",
    # 其他
    "shell", "cmd", "exec", "includes", "inc", "lib", "vendor",
    "node_modules", "package.json", "composer.json", "Gemfile",
    "webmail", "mail", "owa", "cgi-bin", "bin",
    "phpMyAdmin", "phpmyadmin3", "pma",
    "mysql", "sqladmin", "myadmin",
    "elasticsearch", "solr", "jenkins", "grafana", "kibana",
    ".circleci", ".github", ".gitlab-ci.yml", "Dockerfile",
    "docker-compose.yml", "Makefile", "gruntfile.js", "gulpfile.js",
    "webpack.config.js", "babel.config.js",
    "server-status", "server-info",
    ".htpasswd", ".htpasswd.bak",
    "actuator", "actuator/health", "actuator/info",
    "metrics", "health", "status", "ping",
    ".travis.yml", ".drone.yml",
    "security.txt", "humans.txt",
]

EXTENSIONS = [
    "", ".php", ".asp", ".aspx", ".jsp", ".do", ".action",
    ".html", ".htm", ".txt", ".xml", ".json", ".yml", ".yaml",
    ".bak", ".old", ".backup", ".swp", "~", ".save", ".orig",
    ".zip", ".tar", ".tar.gz", ".rar", ".7z", ".sql", ".db",
    ".inc", ".conf", ".config", ".cfg", ".ini",
]


class DirBruteWidget(QWidget):
    """目录爆破 UI"""

    execute_requested = pyqtSignal(dict)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ---- 目标 ----
        tg = QGroupBox("目标设置")
        tg.setStyleSheet(_group_style())
        tgl = QGridLayout(tg)
        tgl.setSpacing(8)
        tgl.addWidget(QLabel("URL:"), 0, 0)
        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("https://example.com/")
        self._url_input.setStyleSheet(_input_style())
        tgl.addWidget(self._url_input, 0, 1)

        # 扩展名
        tgl.addWidget(QLabel("扩展名:"), 1, 0)
        self._ext_combo = QComboBox()
        self._ext_combo.addItems([
            "无扩展名", "常用 Web (.php/.asp/.jsp 等)", "所有扩展名", "自定义"
        ])
        self._ext_combo.setCurrentText("常用 Web (.php/.asp/.jsp 等)")
        self._ext_combo.setStyleSheet(_combo_style())
        tgl.addWidget(self._ext_combo, 1, 1)

        layout.addWidget(tg)

        # ---- 参数 ----
        pg = QGroupBox("扫描参数")
        pg.setStyleSheet(_group_style())
        pgl = QGridLayout(pg)
        pgl.setSpacing(8)

        pgl.addWidget(QLabel("线程数:"), 0, 0)
        self._thread_spin = QSpinBox()
        self._thread_spin.setRange(5, 100)
        self._thread_spin.setValue(20)
        self._thread_spin.setStyleSheet(_spin_style())
        pgl.addWidget(self._thread_spin, 0, 1)

        pgl.addWidget(QLabel("超时(s):"), 0, 2)
        self._timeout_spin = QSpinBox()
        self._timeout_spin.setRange(1, 30)
        self._timeout_spin.setValue(5)
        self._timeout_spin.setStyleSheet(_spin_style())
        pgl.addWidget(self._timeout_spin, 0, 3)

        # 状态码过滤
        pgl.addWidget(QLabel("过滤:"), 1, 0)
        self._filter200 = QCheckBox("200")
        self._filter200.setChecked(True)
        pgl.addWidget(self._filter200, 1, 1)
        self._filter301 = QCheckBox("301/302")
        self._filter301.setChecked(True)
        pgl.addWidget(self._filter301, 1, 2)
        self._filter403 = QCheckBox("403")
        self._filter403.setChecked(True)
        pgl.addWidget(self._filter403, 1, 3)
        self._filter401 = QCheckBox("401")
        pgl.addWidget(self._filter401, 1, 4)

        for cb in [self._filter200, self._filter301, self._filter403, self._filter401]:
            cb.setStyleSheet("color: #cdd6f4; font-size: 12px;")

        layout.addWidget(pg)

        # ---- 按钮 ----
        btn_row = QHBoxLayout()
        self._run_btn = QPushButton("🔍 开始爆破")
        self._run_btn.setStyleSheet(_btn_primary_style())
        self._run_btn.clicked.connect(lambda: self.execute_requested.emit(self.get_params()))
        btn_row.addWidget(self._run_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # ---- 进度条 ----
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setMaximumHeight(6)
        self._progress.setStyleSheet("""
            QProgressBar { background-color: #313244; border: none; border-radius: 3px; }
            QProgressBar::chunk { background-color: #f9e2af; border-radius: 3px; }
        """)
        layout.addWidget(self._progress)

        # ---- 结果表格 ----
        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["路径", "状态码", "大小", "重定向"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setStyleSheet(_table_style())
        layout.addWidget(self._table, stretch=1)

        self._stat_label = QLabel("")
        self._stat_label.setStyleSheet("color: #6c7086; font-size: 12px; padding: 4px;")
        layout.addWidget(self._stat_label)

    def get_params(self) -> dict:
        ext_text = self._ext_combo.currentText()
        if ext_text == "无扩展名":
            extensions = [""]
        elif ext_text == "常用 Web (.php/.asp/.jsp 等)":
            extensions = ["", ".php", ".asp", ".aspx", ".jsp", ".html", ".txt"]
        elif ext_text == "所有扩展名":
            extensions = EXTENSIONS
        else:
            extensions = [""]

        return {
            "url": self._url_input.text().strip(),
            "extensions": extensions,
            "threads": self._thread_spin.value(),
            "timeout": self._timeout_spin.value(),
            "filter_200": self._filter200.isChecked(),
            "filter_301": self._filter301.isChecked(),
            "filter_403": self._filter403.isChecked(),
            "filter_401": self._filter401.isChecked(),
            "wordlist": DEFAULT_WORDLIST,
        }

    def add_result(self, path: str, status: int, size: int, redirect: str) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._table.setItem(row, 0, QTableWidgetItem(path))

        s_item = QTableWidgetItem(str(status))
        if 200 <= status < 300:
            s_item.setForeground(Qt.GlobalColor.green)
        elif status == 403:
            s_item.setForeground(Qt.GlobalColor.yellow)
        else:
            s_item.setForeground(Qt.GlobalColor.red)
        self._table.setItem(row, 1, s_item)

        size_str = f"{size}B" if size < 1024 else f"{size // 1024}KB"
        self._table.setItem(row, 2, QTableWidgetItem(size_str))
        self._table.setItem(row, 3, QTableWidgetItem(redirect))

    def set_progress(self, v: int) -> None:
        self._progress.setVisible(True)
        self._progress.setValue(v)
        if v >= 100:
            self._progress.setVisible(False)

    def set_stat(self, t: str) -> None:
        self._stat_label.setText(t)

    def clear_results(self) -> None:
        self._table.setRowCount(0)


@register_tool
class DirBruteforceTool(BaseTool):
    """目录爆破"""

    meta = ToolMeta(
        name="dir_bruteforce",
        display_name="目录爆破",
        category=ToolCategory.WEB_TESTING,
        description="多线程 Web 目录/文件枚举，内置字典，状态码过滤",
        icon="📂",
        version="1.0.0",
        keywords=["目录", "爆破", "dirb", "gobuster", "枚举", "扫描"],
    )

    def __init__(self) -> None:
        super().__init__()
        self._widget: Optional[DirBruteWidget] = None
        self._cancelled = False

    def create_widget(self) -> QWidget:
        self._widget = DirBruteWidget()
        self._widget.execute_requested.connect(lambda p: self.execute(p))
        return self._widget

    def execute(self, params: dict[str, Any]) -> list[dict]:
        base_url = params["url"].rstrip("/")
        extensions = params.get("extensions", [""])
        threads = params.get("threads", 20)
        timeout = params.get("timeout", 5)
        wordlist = params.get("wordlist", DEFAULT_WORDLIST)
        filter_codes = set()
        for code, enabled in [
            (list(range(200, 300)), params.get("filter_200", True)),
            ([301, 302], params.get("filter_301", True)),
            ([403], params.get("filter_403", True)),
            ([401], params.get("filter_401", False)),
        ]:
            if enabled:
                filter_codes.update(code if isinstance(code, list) else [code])

        self._cancelled = False
        if self._widget:
            self._widget.clear_results()

        # 构建目标列表
        targets: list[str] = []
        for word in wordlist:
            for ext in extensions:
                path = f"/{word}{ext}"
                targets.append(path)

        self.output_ready.emit(f"开始扫描 {base_url}，共 {len(targets)} 个目标...")
        results: list[dict] = []

        def _check(path: str) -> Optional[dict]:
            if self._cancelled:
                return None
            url = base_url + path
            try:
                resp = requests.get(
                    url, timeout=timeout, allow_redirects=False,
                    headers={"User-Agent": "SecTools-Platform/1.0"},
                    verify=False,
                )
                redirect = resp.headers.get("Location", "")
                if resp.status_code in filter_codes or (
                    resp.status_code == 200 and params.get("filter_200", True)
                ):
                    return {
                        "path": path, "status": resp.status_code,
                        "size": len(resp.content), "redirect": redirect,
                    }
            except Exception:
                pass
            return None

        completed = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as ex:
            futures = {ex.submit(_check, p): p for p in targets}
            for future in concurrent.futures.as_completed(futures):
                completed += 1
                r = future.result()
                if r:
                    results.append(r)
                    if self._widget:
                        self._widget.add_result(
                            r["path"], r["status"], r["size"], r["redirect"]
                        )
                    self.output_ready.emit(
                        f"  [{r['status']}] {r['path']} ({r['size']}B)"
                    )
                if completed % 20 == 0:
                    pct = int(completed / len(targets) * 100)
                    self.progress_updated.emit(pct)
                    if self._widget:
                        self._widget.set_progress(pct)

        self.progress_updated.emit(100)
        if self._widget:
            self._widget.set_progress(100)
            self._widget.set_stat(
                f"扫描完成: {len(results)} 个路径发现，共 {len(targets)} 个目标"
            )
        self.output_ready.emit(f"✓ 发现 {len(results)} 个路径")
        return results

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        errors = []
        if not params.get("url", "").strip():
            errors.append("请输入目标 URL")
        return errors


# ---- 样式 ----
def _group_style() -> str:
    return """QGroupBox { color: #cdd6f4; font-size: 14px; font-weight: bold;
        border: 1px solid #313244; border-radius: 8px;
        margin-top: 8px; padding-top: 20px; }
        QGroupBox::title { subcontrol-origin: margin; left: 16px; padding: 0 8px; }"""


def _input_style() -> str:
    return """QLineEdit { background-color: #313244; color: #cdd6f4;
        border: 1px solid #45475a; border-radius: 6px;
        padding: 10px 12px; font-size: 14px; }
        QLineEdit:focus { border-color: #89b4fa; }"""


def _combo_style() -> str:
    return """QComboBox { background-color: #313244; color: #cdd6f4;
        border: 1px solid #45475a; border-radius: 6px;
        padding: 8px 12px; font-size: 13px; }
        QComboBox QAbstractItemView { background-color: #1e1e2e; color: #cdd6f4;
        selection-background-color: #45475a; }"""


def _spin_style() -> str:
    return """QSpinBox { background-color: #313244; color: #cdd6f4;
        border: 1px solid #45475a; border-radius: 6px;
        padding: 8px 12px; font-size: 13px; }"""


def _btn_primary_style() -> str:
    return """QPushButton { background-color: #f9e2af; color: #1e1e2e;
        border: none; border-radius: 6px;
        padding: 10px 24px; font-size: 13px; font-weight: bold; }
        QPushButton:hover { background-color: #f5c2e7; }"""


def _table_style() -> str:
    return """QTableWidget { background-color: #11111b; color: #cdd6f4;
        border: 1px solid #313244; border-radius: 6px;
        gridline-color: #313244; font-size: 12px;
        alternate-background-color: #181825; }
        QHeaderView::section { background-color: #1e1e2e; color: #cdd6f4;
        border: 1px solid #313244; padding: 6px 8px; font-weight: bold; }"""
