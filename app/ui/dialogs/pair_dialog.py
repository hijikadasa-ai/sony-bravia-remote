"""PIN 配对对话框：引导用户在电视屏幕上读出 4 位 PIN 并完成设备注册。"""
from __future__ import annotations

from PySide6.QtCore import QRegularExpression, Qt
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from ...core.errors import AuthRequired, TvError
from ..tasks import TaskRunner
from ..widgets import set_variant


class PairDialog(QDialog):
    def __init__(self, service, runner: TaskRunner, parent=None) -> None:
        super().__init__(parent)
        self.service = service
        self.runner = runner
        self.setWindowTitle("与电视配对")
        self.setModal(True)
        self.setFixedWidth(400)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(12)

        title = QLabel("在本机与电视之间建立授权")
        title.setObjectName("DialogTitle")
        root.addWidget(title)

        steps = QLabel(
            "1. 点击「开始配对」\n"
            "2. 电视屏幕上会弹出注册提示，并显示 4 位 PIN\n"
            "3. 把 PIN 填到下面，点「完成配对」"
        )
        steps.setObjectName("Hint")
        steps.setWordWrap(True)
        root.addWidget(steps)

        self.status = QLabel("尚未开始")
        self.status.setObjectName("Hint")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

        pin_row = QHBoxLayout()
        pin_row.setSpacing(10)
        self.pin_edit = QLineEdit()
        self.pin_edit.setPlaceholderText("电视上显示的 PIN")
        self.pin_edit.setMaxLength(6)
        self.pin_edit.setValidator(QRegularExpressionValidator(QRegularExpression(r"\d{0,6}")))
        self.pin_edit.setAlignment(Qt.AlignCenter)
        self.pin_edit.setStyleSheet("font-size:20px; letter-spacing:6px; padding:8px;")
        self.pin_edit.setEnabled(False)
        self.pin_edit.returnPressed.connect(self._finish)
        pin_row.addWidget(self.pin_edit, 1)
        root.addLayout(pin_row)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self.begin_btn = QPushButton("开始配对")
        self.begin_btn.clicked.connect(self._begin)
        set_variant(self.begin_btn, "primary")
        self.begin_btn.setFixedHeight(36)
        buttons.addWidget(self.begin_btn)

        self.finish_btn = QPushButton("完成配对")
        self.finish_btn.clicked.connect(self._finish)
        self.finish_btn.setFixedHeight(36)
        self.finish_btn.setEnabled(False)
        buttons.addWidget(self.finish_btn)

        buttons.addStretch(1)
        cancel = QPushButton("取消")
        cancel.clicked.connect(self.reject)
        set_variant(cancel, "ghost")
        cancel.setFixedHeight(36)
        buttons.addWidget(cancel)
        root.addLayout(buttons)

        tip = QLabel("提示：若不想每次配对，可在电视「设置 → 网络 → 家庭网络 → IP 控制」中"
                     "把认证方式设为「Normal and Pre-Shared Key」并设置预共享密钥，然后在设置里填入同一密钥。")
        tip.setObjectName("Hint")
        tip.setWordWrap(True)
        root.addWidget(tip)

    # ---------------------------------------------------------------- 动作
    def _begin(self) -> None:
        self.begin_btn.setEnabled(False)
        self.pin_edit.clear()
        self.pin_edit.setEnabled(False)
        self.finish_btn.setEnabled(False)
        self.status.setText("正在请求配对，请看电视屏幕…")
        self.service.client.auth_cookie = ""
        self.runner.submit(
            self.service.begin_pairing,
            on_ok=self._on_begin_ok,
            on_err=self._on_begin_err,
        )

    def _on_begin_ok(self, _result) -> None:
        # 已被授权（可能之前注册过）：直接视为成功
        self.status.setText("电视已授权本机，无需再次输入 PIN。")
        self.accept()

    def _on_begin_err(self, exc: Exception) -> None:
        self.begin_btn.setEnabled(True)
        if isinstance(exc, AuthRequired) and exc.needs_pin:
            self.status.setText("电视应已显示 PIN。请把 PIN 填到下方后点「完成配对」。")
            self.pin_edit.setEnabled(True)
            self.finish_btn.setEnabled(True)
            self.pin_edit.setFocus()
        elif isinstance(exc, TvError):
            self.status.setText(str(exc))
        else:
            self.status.setText(f"配对失败：{exc}")

    def _finish(self) -> None:
        pin = "".join(ch for ch in self.pin_edit.text() if ch.isdigit())
        if not pin:
            self.status.setText("请先输入电视上显示的 PIN")
            return
        self.finish_btn.setEnabled(False)
        self.status.setText("正在校验 PIN…")
        self.runner.submit(
            lambda: self.service.finish_pairing(pin),
            on_ok=self._on_finish_ok,
            on_err=self._on_finish_err,
        )

    def _on_finish_ok(self, _result) -> None:
        self.status.setText("配对成功")
        self.accept()

    def _on_finish_err(self, exc: Exception) -> None:
        self.finish_btn.setEnabled(True)
        message = str(exc) if isinstance(exc, TvError) else f"配对失败：{exc}"
        self.status.setText(message)
        if isinstance(exc, AuthRequired):
            self.status.setText("PIN 不正确或已超时，请重新点「开始配对」。")
            self.pin_edit.clear()
