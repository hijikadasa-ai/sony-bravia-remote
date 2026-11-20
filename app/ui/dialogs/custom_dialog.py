"""自定义按键编辑对话框：官方按键 / 原始 IRCC 指令 / 启动应用 / 打开网址 / 宏。"""
from __future__ import annotations

from typing import Any, Dict, List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...config import CustomButton
from ...core import keys as keydb
from ..widgets import set_variant

ACTION_TYPES = [
    ("key", "官方按键"),
    ("ircc", "IRCC 原始指令"),
    ("app", "启动电视应用"),
    ("url", "在电视浏览器打开网址"),
    ("macro", "组合宏（多步）"),
]
QUICK_EMOJI = ["⭐", "📺", "🔊", "🎵", "🎬", "🌐", "💡", "⚽", "🎮", "📱", "🔴", "🎯"]


class CustomButtonDialog(QDialog):
    def __init__(
        self,
        button: CustomButton | None = None,
        apps: List[Dict[str, Any]] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("编辑自定义按键" if button else "添加自定义按键")
        self.setModal(True)
        self.setFixedWidth(440)
        self._apps = apps or []
        self._result: CustomButton | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(12)

        title = QLabel(self.windowTitle())
        title.setObjectName("DialogTitle")
        root.addWidget(title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        grid.setColumnStretch(1, 1)

        row = 0
        grid.addWidget(self._label("名称"), row, 0)
        self.name_edit = QLineEdit(button.label if button else "")
        self.name_edit.setPlaceholderText("显示在按钮上的文字，例如：客厅氛围灯")
        self.name_edit.setMaxLength(12)
        grid.addWidget(self.name_edit, row, 1)

        row += 1
        grid.addWidget(self._label("图标"), row, 0)
        emoji_row = QHBoxLayout()
        emoji_row.setSpacing(6)
        self.emoji_edit = QLineEdit(button.emoji if button else "⭐")
        self.emoji_edit.setFixedWidth(56)
        self.emoji_edit.setMaxLength(4)
        self.emoji_edit.setAlignment(Qt.AlignCenter)
        self.emoji_edit.setStyleSheet("font-family:'Segoe UI Emoji'; font-size:18px;")
        emoji_row.addWidget(self.emoji_edit)
        for ch in QUICK_EMOJI[:8]:
            chip = QPushButton(ch)
            chip.setCursor(Qt.PointingHandCursor)
            chip.setFixedSize(30, 30)
            chip.setStyleSheet("font-family:'Segoe UI Emoji'; font-size:14px; border-radius:8px;")
            chip.clicked.connect(lambda _=False, c=ch: self.emoji_edit.setText(c))
            emoji_row.addWidget(chip)
        emoji_row.addStretch(1)
        grid.addLayout(emoji_row, row, 1)

        row += 1
        grid.addWidget(self._label("类型"), row, 0)
        self.type_combo = QComboBox()
        for value, text in ACTION_TYPES:
            self.type_combo.addItem(text, value)
        self.type_combo.currentIndexChanged.connect(self._sync_editor)
        grid.addWidget(self.type_combo, row, 1)

        row += 1
        grid.addWidget(self._label("参数"), row, 0)
        self.editor_box = QWidget()
        self.editor_layout = QVBoxLayout(self.editor_box)
        self.editor_layout.setContentsMargins(0, 0, 0, 0)
        self.editor_layout.setSpacing(0)
        grid.addWidget(self.editor_box, row, 1)

        # 官方按键
        self.key_combo = QComboBox()
        self.key_combo.setEditable(True)
        self.key_combo.setInsertPolicy(QComboBox.NoInsert)
        for name in keydb.all_keys():
            self.key_combo.addItem(f"{keydb.label(name)}  ·  {name}", name)
        completer = self.key_combo.completer()
        if completer:
            completer.setFilterMode(Qt.MatchContains)
            completer.setCompletionMode(QCompleter.PopupCompletion)
        self.editor_layout.addWidget(self.key_combo)

        # IRCC
        self.ircc_edit = QLineEdit()
        self.ircc_edit.setPlaceholderText("Base64 指令，例如 AAAAAQAAAAEAAAASAw==")
        self.editor_layout.addWidget(self.ircc_edit)

        # 应用
        self.app_combo = QComboBox()
        self.app_combo.setEditable(True)
        for app in self._apps:
            self.app_combo.addItem(str(app.get("title") or "未命名"), str(app.get("uri") or ""))
        self.app_combo.setToolTip("在「应用」页刷新后，这里会列出电视上已安装的应用")
        self.editor_layout.addWidget(self.app_combo)

        # 网址
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://www.bilibili.com")
        self.editor_layout.addWidget(self.url_edit)

        # 宏
        self.macro_edit = QPlainTextEdit()
        self.macro_edit.setFixedHeight(110)
        self.macro_edit.setPlaceholderText(
            "每行一步，例如：\nkey:Home\ndelay:400\napp:com.sony.dtv.com.netflix.ninja...\nkey:Confirm"
        )
        self.macro_edit.setStyleSheet("font-family:Consolas, monospace; font-size:12px;")
        self.editor_layout.addWidget(self.macro_edit)

        root.addLayout(grid)

        self.error_label = QLabel("")
        self.error_label.setObjectName("ErrorText")
        self.error_label.setWordWrap(True)
        root.addWidget(self.error_label)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton("取消")
        cancel.clicked.connect(self.reject)
        set_variant(cancel, "ghost")
        cancel.setFixedHeight(34)
        buttons.addWidget(cancel)
        save = QPushButton("保存")
        save.setFixedHeight(34)
        save.setMinimumWidth(84)
        set_variant(save, "primary")
        save.clicked.connect(self._save)
        buttons.addWidget(save)
        root.addLayout(buttons)

        self._editing = button
        self._apply_initial(button)
        self._sync_editor()

    # ---------------------------------------------------------------- 辅助
    @staticmethod
    def _label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("Hint")
        label.setFixedWidth(40)
        return label

    def _apply_initial(self, button: CustomButton | None) -> None:
        if not button:
            return
        index = self.type_combo.findData((button.action or "key").lower())
        if index >= 0:
            self.type_combo.setCurrentIndex(index)
        value = button.value or ""
        action = (button.action or "key").lower()
        if action == "key":
            pos = self.key_combo.findData(value)
            if pos >= 0:
                self.key_combo.setCurrentIndex(pos)
            else:
                self.key_combo.setEditText(value)
        elif action == "ircc":
            self.ircc_edit.setText(value)
        elif action == "app":
            pos = self.app_combo.findData(value)
            if pos >= 0:
                self.app_combo.setCurrentIndex(pos)
            else:
                self.app_combo.setEditText(value)
        elif action == "url":
            self.url_edit.setText(value)
        elif action == "macro":
            self.macro_edit.setPlainText(value)

    def _current_action(self) -> str:
        return self.type_combo.currentData() or "key"

    def _sync_editor(self) -> None:
        order = {"key": 0, "ircc": 1, "app": 2, "url": 3, "macro": 4}
        active = order.get(self._current_action(), 0)
        for index, editor in enumerate(
            [self.key_combo, self.ircc_edit, self.app_combo, self.url_edit, self.macro_edit]
        ):
            editor.setVisible(index == active)
        self.editor_box.adjustSize()

    # ---------------------------------------------------------------- 保存
    def _collect_value(self) -> str:
        action = self._current_action()
        if action == "key":
            data = self.key_combo.currentData()
            if isinstance(data, str) and data:
                return data
            return self.key_combo.currentText().split("·")[-1].strip()
        if action == "ircc":
            return self.ircc_edit.text().strip()
        if action == "app":
            data = self.app_combo.currentData()
            return data if isinstance(data, str) and data else self.app_combo.currentText().strip()
        if action == "url":
            return self.url_edit.text().strip()
        return self.macro_edit.toPlainText().strip()

    def _save(self) -> None:
        label = self.name_edit.text().strip()
        if not label:
            self.error_label.setText("请填写名称")
            return
        value = self._collect_value()
        if not value:
            self.error_label.setText("请填写参数")
            return
        action = self._current_action()
        if action == "ircc" and len(value) < 8:
            self.error_label.setText("IRCC 指令看起来不完整")
            return
        button = CustomButton(
            id=self._editing.id if self._editing else CustomButton().id,
            label=label,
            emoji=self.emoji_edit.text().strip() or "⭐",
            action=action,
            value=value,
            color=self._editing.color if self._editing else "",
        )
        self._result = button
        self.accept()

    @property
    def result_button(self) -> CustomButton | None:
        return self._result
