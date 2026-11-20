"""深色主题：遥控器类应用长时间近距离使用，深色底更适合，也更能突出按键边界。"""
from __future__ import annotations

# 调色板（供自绘控件复用）
BG = "#0f1115"
SURFACE = "#171a20"
SURFACE_2 = "#1e222a"
SURFACE_3 = "#262b35"
BORDER = "#2b313b"
BORDER_HI = "#3a4250"
TEXT = "#e9edf3"
TEXT_DIM = "#8e9aab"
ACCENT = "#4b8bf5"
ACCENT_DIM = "#2f5cad"
DANGER = "#ef5350"
OK_GREEN = "#35c48a"
RED = "#e5534b"
GREEN = "#3fb950"
YELLOW = "#d4a72c"
BLUE = "#4b8bf5"

FONT_STACK = '"Microsoft YaHei UI", "Segoe UI", "PingFang SC", sans-serif'
EMOJI_STACK = '"Segoe UI Emoji", "Microsoft YaHei UI", sans-serif'


def stylesheet() -> str:
    return f"""
* {{
    font-family: {FONT_STACK};
    outline: none;
}}
QWidget {{
    color: {TEXT};
    font-size: 13px;
}}
QWidget#Root {{ background: {BG}; }}
QDialog {{ background: {BG}; }}

/* ------------------------------------------------------------ 标题区 */
QLabel#AppTitle {{ font-size: 15px; font-weight: 600; color: {TEXT}; }}
QLabel#AppSub {{ font-size: 11px; color: {TEXT_DIM}; }}
QLabel#SectionTitle {{ font-size: 12px; font-weight: 600; color: {TEXT_DIM}; padding: 2px 2px 4px 2px; }}
QLabel#Hint {{ font-size: 11px; color: {TEXT_DIM}; }}
QLabel#DialogTitle {{ font-size: 16px; font-weight: 600; }}
QLabel#ErrorText {{ color: {DANGER}; font-size: 12px; }}

/* ------------------------------------------------------------ 按键 */
QPushButton {{
    background: {SURFACE_2};
    border: 1px solid {BORDER};
    border-radius: 12px;
    color: {TEXT};
    padding: 0px 10px;   /* 纯文字按钮左右留白，固定尺寸按钮不受影响 */
    font-size: 13px;
}}
QPushButton:hover {{ background: #2a303a; border-color: {BORDER_HI}; }}
QPushButton:pressed {{ background: {ACCENT_DIM}; border-color: {ACCENT}; }}
QPushButton:disabled {{ color: #5b6472; background: #191d24; border-color: #242932; }}

QPushButton[variant="primary"] {{
    background: {ACCENT};
    border: 1px solid {ACCENT};
    color: #ffffff;
    font-weight: 600;
}}
QPushButton[variant="primary"]:hover {{ background: #5c98f8; }}
QPushButton[variant="primary"]:pressed {{ background: {ACCENT_DIM}; }}

QPushButton[variant="danger"] {{
    background: #2c1c1e;
    border: 1px solid #5a2a2c;
    color: #ff8b88;
}}
QPushButton[variant="danger"]:hover {{ background: #3a2225; border-color: #7c3639; }}
QPushButton[variant="danger"]:pressed {{ background: #52262a; }}

QPushButton[variant="ghost"] {{
    background: transparent;
    border: 1px solid transparent;
    color: {TEXT_DIM};
}}
QPushButton[variant="ghost"]:hover {{ background: {SURFACE_2}; color: {TEXT}; }}

QPushButton[variant="tap"] {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 10px;
    font-size: 12px;
}}
QPushButton[variant="tap"]:hover {{ background: {SURFACE_3}; }}
QPushButton[variant="tap"]:pressed {{ background: {ACCENT_DIM}; border-color: {ACCENT}; }}

QPushButton#IconButton {{
    border-radius: 18px;
    font-size: 15px;
    font-family: {EMOJI_STACK};
}}

/* ------------------------------------------------------------ 标签页 */
QTabWidget::pane {{ border: none; background: transparent; }}
QTabBar {{ background: transparent; }}
QTabBar::tab {{
    background: transparent;
    color: {TEXT_DIM};
    padding: 7px 13px;
    margin-right: 3px;
    border-radius: 9px;
    font-size: 12px;
}}
QTabBar::tab:hover {{ color: {TEXT}; background: {SURFACE}; }}
QTabBar::tab:selected {{ background: {SURFACE_3}; color: {TEXT}; font-weight: 600; }}

/* ------------------------------------------------------------ 滚动 */
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px 0 2px 0; }}
QScrollBar::handle:vertical {{ background: #333a45; border-radius: 4px; min-height: 28px; }}
QScrollBar::handle:vertical:hover {{ background: #46505f; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QScrollBar:horizontal {{ height: 0px; }}

/* ------------------------------------------------------------ 输入控件 */
QLineEdit, QComboBox, QSpinBox, QPlainTextEdit {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 9px;
    padding: 6px 9px;
    selection-background-color: {ACCENT};
    color: {TEXT};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QPlainTextEdit:focus {{ border-color: {ACCENT}; }}
QLineEdit::placeholder {{ color: #5f6b7c; }}
QComboBox::drop-down {{ border: none; width: 20px; }}
QSpinBox {{
    padding-right: 18px;
}}
QSpinBox::up-button, QSpinBox::down-button {{
    background: transparent;
    width: 15px;
    border: none;
    margin-right: 3px;
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
    background: {SURFACE_3};
    border-radius: 4px;
}}
QComboBox QAbstractItemView {{
    background: {SURFACE_2};
    border: 1px solid {BORDER_HI};
    border-radius: 8px;
    selection-background-color: {ACCENT_DIM};
    padding: 4px;
}}
QCheckBox {{ spacing: 8px; color: {TEXT}; }}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border-radius: 5px;
    border: 1px solid {BORDER_HI};
    background: {SURFACE};
}}
QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}
QLabel#PinHint {{ font-size: 12px; color: {TEXT_DIM}; }}

/* ------------------------------------------------------------ 提示条 */
QLabel#Toast {{
    background: {SURFACE_3};
    border: 1px solid {BORDER_HI};
    border-radius: 10px;
    padding: 8px 14px;
    color: {TEXT};
    font-size: 12px;
}}
QLabel#Toast[kind="error"] {{ background: #341f22; border-color: #6b3034; color: #ffb3b0; }}
QLabel#Toast[kind="ok"] {{ background: #16302a; border-color: #2a5a4a; color: #a5e8cd; }}

/* ------------------------------------------------------------ 菜单 */
QMenu {{
    background: {SURFACE_2};
    border: 1px solid {BORDER_HI};
    border-radius: 10px;
    padding: 5px;
}}
QMenu::item {{ padding: 6px 22px 6px 12px; border-radius: 6px; }}
QMenu::item:selected {{ background: {ACCENT_DIM}; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 4px 8px; }}
QToolTip {{
    background: {SURFACE_3};
    color: {TEXT};
    border: 1px solid {BORDER_HI};
    border-radius: 6px;
    padding: 4px 7px;
    font-size: 11px;
}}
"""
