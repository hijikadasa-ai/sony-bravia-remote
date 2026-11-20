"""设置对话框：连接参数、配对入口、程序行为。"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...config import Config
from ...core.errors import TvError
from ...platform_win import set_autostart
from ..tasks import TaskRunner
from ..widgets import set_variant
from .pair_dialog import PairDialog


class SettingsDialog(QDialog):
    def __init__(self, config: Config, service, runner: TaskRunner, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config = config
        self.service = service
        self.runner = runner
        self.setWindowTitle("设置")
        self.setModal(True)
        self.setFixedWidth(430)
        self.saved = False

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(12)

        title = QLabel("设置")
        title.setObjectName("DialogTitle")
        root.addWidget(title)

        # ---------------------------------------------------------- 连接
        conn = QLabel("电视连接")
        conn.setObjectName("SectionTitle")
        root.addWidget(conn)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(9)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)

        tv = config.tv
        grid.addWidget(self._hint("IP 地址"), 0, 0)
        self.host_edit = QLineEdit(tv.host)
        self.host_edit.setPlaceholderText("例如 192.168.1.10")
        grid.addWidget(self.host_edit, 0, 1)

        grid.addWidget(self._hint("端口"), 0, 2)
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(tv.port)
        grid.addWidget(self.port_spin, 0, 3)

        grid.addWidget(self._hint("预共享密钥"), 1, 0)
        self.psk_edit = QLineEdit(tv.psk)
        self.psk_edit.setEchoMode(QLineEdit.PasswordEchoOnEdit)
        self.psk_edit.setPlaceholderText("电视未启用可留空")
        grid.addWidget(self.psk_edit, 1, 1)

        grid.addWidget(self._hint("备注名"), 1, 2)
        self.nick_edit = QLineEdit(tv.nickname)
        self.nick_edit.setPlaceholderText("电视上显示的名称")
        grid.addWidget(self.nick_edit, 1, 3)

        grid.addWidget(self._hint("网卡地址"), 2, 0)
        self.mac_edit = QLineEdit(tv.mac)
        self.mac_edit.setPlaceholderText("AA:BB:CC:DD:EE:FF（用于网络唤醒，可留空）")
        grid.addWidget(self.mac_edit, 2, 1, 1, 3)

        root.addLayout(grid)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.test_btn = QPushButton("测试连接")
        self.test_btn.setFixedHeight(34)
        self.test_btn.clicked.connect(self._test)
        actions.addWidget(self.test_btn)

        self.pair_btn = QPushButton("与电视配对…")
        self.pair_btn.setFixedHeight(34)
        self.pair_btn.clicked.connect(self._pair)
        actions.addWidget(self.pair_btn)
        actions.addStretch(1)
        root.addLayout(actions)

        self.result_label = QLabel("")
        self.result_label.setObjectName("Hint")
        self.result_label.setWordWrap(True)
        root.addWidget(self.result_label)

        # ---------------------------------------------------------- 行为
        behaviour = QLabel("程序行为")
        behaviour.setObjectName("SectionTitle")
        root.addWidget(behaviour)

        self.on_top_cb = QCheckBox("遥控器窗口始终置顶")
        self.on_top_cb.setChecked(config.ui.always_on_top)
        root.addWidget(self.on_top_cb)

        self.tray_cb = QCheckBox("点击关闭按钮时隐藏到系统托盘")
        self.tray_cb.setChecked(config.ui.minimize_to_tray)
        root.addWidget(self.tray_cb)

        self.autostart_cb = QCheckBox("开机自动启动（最小化到托盘）")
        self.autostart_cb.setChecked(config.ui.start_with_windows)
        root.addWidget(self.autostart_cb)

        poll_row = QHBoxLayout()
        poll_row.setSpacing(8)
        poll_row.addWidget(self._hint("状态刷新间隔"))
        self.poll_spin = QSpinBox()
        self.poll_spin.setRange(1, 30)
        self.poll_spin.setSuffix(" 秒")
        self.poll_spin.setFixedWidth(90)
        self.poll_spin.setValue(max(1, int(config.ui.poll_interval or 3)))
        poll_row.addWidget(self.poll_spin)
        poll_row.addStretch(1)
        root.addLayout(poll_row)

        # ---------------------------------------------------------- 底部
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton("取消")
        cancel.setFixedHeight(34)
        set_variant(cancel, "ghost")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)
        save = QPushButton("保存")
        save.setFixedHeight(34)
        save.setMinimumWidth(84)
        set_variant(save, "primary")
        save.clicked.connect(self._save)
        buttons.addWidget(save)
        root.addLayout(buttons)

    # ---------------------------------------------------------------- 辅助
    @staticmethod
    def _hint(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("Hint")
        return label

    def _apply_to_service(self) -> None:
        tv = self.config.tv
        tv.host = self.host_edit.text().strip() or tv.host
        tv.port = int(self.port_spin.value())
        tv.psk = self.psk_edit.text().strip()
        tv.mac = self.mac_edit.text().strip()
        tv.nickname = self.nick_edit.text().strip() or "PC Remote"
        self.service.rebuild()

    def _test(self) -> None:
        self._apply_to_service()
        self.result_label.setText("正在连接…")
        self.test_btn.setEnabled(False)

        def probe():
            info = self.service.client.get_interface_information()
            latency = self.service.client.ping_latency()
            power = self.service.client.get_power_status()
            return info, latency, power

        def ok(result):
            info, latency, power = result
            state = {"active": "开机", "standby": "待机"}.get(power, power)
            self.result_label.setText(
                f"已连接 {info.get('modelName', 'BRAVIA')}（{state}），往返延迟 {latency:.0f} ms"
            )
            self.test_btn.setEnabled(True)

        def err(exc):
            message = str(exc) if isinstance(exc, TvError) else f"连接失败：{exc}"
            self.result_label.setText(message)
            self.test_btn.setEnabled(True)

        self.runner.submit(probe, ok, err)

    def _pair(self) -> None:
        self._apply_to_service()
        dialog = PairDialog(self.service, self.runner, self)
        if dialog.exec() == QDialog.Accepted:
            self.result_label.setText("配对成功，已保存授权凭据。")
            self.service.persist_auth()

    def _save(self) -> None:
        if not self.host_edit.text().strip():
            self.result_label.setText("请填写电视的 IP 地址")
            return
        self._apply_to_service()
        self.config.ui.always_on_top = self.on_top_cb.isChecked()
        self.config.ui.minimize_to_tray = self.tray_cb.isChecked()
        self.config.ui.start_with_windows = self.autostart_cb.isChecked()
        self.config.ui.poll_interval = float(self.poll_spin.value())
        set_autostart(self.config.ui.start_with_windows)
        self.config.save()
        self.saved = True
        self.accept()
