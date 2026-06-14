"""
全局 CSS 样式常量 — 统一管理所有 QSS 样式。

所有工具模块应该从本文件导入样式常量，
避免在 19 个工具文件中重复定义相同样式。
"""

from __future__ import annotations

# ============================================================
# 颜色主题 (Catppuccin Mocha 暗色)
# ============================================================

COLORS = {
    "base": "#1e1e2e",
    "mantle": "#181825",
    "crust": "#11111b",
    "surface0": "#313244",
    "surface1": "#45475a",
    "surface2": "#585b70",
    "overlay0": "#6c7086",
    "text": "#cdd6f4",
    "subtext0": "#a6adc8",
    "subtext1": "#bac2de",
    "blue": "#89b4fa",
    "lavender": "#b4befe",
    "green": "#a6e3a1",
    "teal": "#94e2d5",
    "sky": "#89dceb",
    "yellow": "#f9e2af",
    "peach": "#fab387",
    "red": "#f38ba8",
    "pink": "#f5c2e7",
    "mauve": "#cba6f7",
}

# ============================================================
# 可复用 QSS 组件样式
# ============================================================

GROUP_BOX = f"""
    QGroupBox {{
        color: {COLORS["text"]};
        font-size: 14px;
        font-weight: bold;
        border: 1px solid {COLORS["surface0"]};
        border-radius: 8px;
        margin-top: 8px;
        padding-top: 20px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 16px;
        padding: 0 8px;
    }}
"""

LINE_EDIT = f"""
    QLineEdit {{
        background-color: {COLORS["surface0"]};
        color: {COLORS["text"]};
        border: 1px solid {COLORS["surface1"]};
        border-radius: 6px;
        padding: 10px 12px;
        font-size: 14px;
    }}
    QLineEdit:focus {{
        border-color: {COLORS["blue"]};
    }}
"""

TEXT_EDIT = f"""
    QTextEdit {{
        background-color: {COLORS["crust"]};
        color: {COLORS["text"]};
        border: 1px solid {COLORS["surface0"]};
        border-radius: 6px;
        padding: 10px;
        font-family: "Consolas", "Microsoft YaHei Mono", monospace;
        font-size: 13px;
    }}
    QTextEdit:focus {{
        border-color: {COLORS["blue"]};
    }}
"""

COMBO_BOX = f"""
    QComboBox {{
        background-color: {COLORS["surface0"]};
        color: {COLORS["text"]};
        border: 1px solid {COLORS["surface1"]};
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 13px;
    }}
    QComboBox::drop-down {{
        border: none;
        padding-right: 8px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {COLORS["base"]};
        color: {COLORS["text"]};
        selection-background-color: {COLORS["surface1"]};
        border: 1px solid {COLORS["surface0"]};
    }}
"""

TABLE = f"""
    QTableWidget {{
        background-color: {COLORS["crust"]};
        color: {COLORS["text"]};
        border: 1px solid {COLORS["surface0"]};
        border-radius: 6px;
        gridline-color: {COLORS["surface0"]};
        font-size: 12px;
        alternate-background-color: {COLORS["mantle"]};
    }}
    QTableWidget::item:selected {{
        background-color: {COLORS["surface1"]};
    }}
    QHeaderView::section {{
        background-color: {COLORS["base"]};
        color: {COLORS["text"]};
        border: 1px solid {COLORS["surface0"]};
        padding: 6px 8px;
        font-weight: bold;
        font-size: 12px;
    }}
"""

BUTTON_PRIMARY = f"""
    QPushButton {{
        background-color: {COLORS["blue"]};
        color: {COLORS["base"]};
        border: none;
        border-radius: 6px;
        padding: 10px 24px;
        font-size: 13px;
        font-weight: bold;
    }}
    QPushButton:hover {{ background-color: {COLORS["sky"]}; }}
    QPushButton:pressed {{ background-color: {COLORS["teal"]}; }}
    QPushButton:disabled {{
        background-color: {COLORS["surface1"]};
        color: {COLORS["overlay0"]};
    }}
"""

BUTTON_SECONDARY = f"""
    QPushButton {{
        background-color: {COLORS["surface0"]};
        color: {COLORS["text"]};
        border: 1px solid {COLORS["surface1"]};
        border-radius: 6px;
        padding: 10px 24px;
        font-size: 13px;
    }}
    QPushButton:hover {{ background-color: {COLORS["surface1"]}; }}
"""

BUTTON_ACCENT = f"""
    QPushButton {{
        background-color: {COLORS["green"]};
        color: {COLORS["base"]};
        border: none;
        border-radius: 6px;
        padding: 10px 24px;
        font-size: 13px;
        font-weight: bold;
    }}
    QPushButton:hover {{ background-color: {COLORS["teal"]}; }}
"""

BUTTON_DANGER = f"""
    QPushButton {{
        background-color: {COLORS["red"]};
        color: {COLORS["base"]};
        border: none;
        border-radius: 6px;
        padding: 10px 24px;
        font-size: 13px;
        font-weight: bold;
    }}
    QPushButton:hover {{ background-color: {COLORS["peach"]}; }}
"""

BUTTON_SMALL = f"""
    QPushButton {{
        background-color: {COLORS["surface1"]};
        color: {COLORS["text"]};
        border: none;
        border-radius: 4px;
        padding: 4px 10px;
        font-size: 11px;
    }}
    QPushButton:hover {{ background-color: {COLORS["surface2"]}; }}
"""

PROGRESS_BAR = f"""
    QProgressBar {{
        background-color: {COLORS["surface0"]};
        border: 1px solid {COLORS["surface1"]};
        border-radius: 4px;
        text-align: center;
        color: {COLORS["text"]};
        height: 20px;
    }}
    QProgressBar::chunk {{
        background-color: {COLORS["blue"]};
        border-radius: 3px;
    }}
"""

TAB_WIDGET = f"""
    QTabWidget::pane {{
        border: 1px solid {COLORS["surface0"]};
        background-color: {COLORS["base"]};
    }}
    QTabBar::tab {{
        background-color: {COLORS["mantle"]};
        color: {COLORS["subtext0"]};
        padding: 6px 16px;
        font-size: 12px;
        border: 1px solid {COLORS["surface0"]};
        border-bottom: none;
    }}
    QTabBar::tab:selected {{
        background-color: {COLORS["base"]};
        color: {COLORS["text"]};
    }}
"""

SCROLL_AREA = f"""
    QScrollArea {{
        border: none;
        background: transparent;
    }}
    QScrollBar:vertical {{
        background-color: {COLORS["base"]};
        width: 10px;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical {{
        background-color: {COLORS["surface1"]};
        border-radius: 5px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background-color: {COLORS["surface2"]};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
"""

GLOBAL_STYLESHEET = f"""
    QMainWindow {{
        background-color: {COLORS["base"]};
    }}
    QWidget {{
        font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    }}
    QToolTip {{
        background-color: {COLORS["surface0"]};
        color: {COLORS["text"]};
        border: 1px solid {COLORS["surface1"]};
        padding: 4px 8px;
        font-size: 12px;
    }}
    {SCROLL_AREA}
"""
