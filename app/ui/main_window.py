"""遥控器主窗口。

布局分四页：
  遥控器   —— 与实体遥控器一致的按键排布（电源/输入/方向/音量/频道/媒体/数字/彩键）
  应用输入 —— 电视上已安装的应用与 HDMI 等输入源，一键切换
  全部按键 —— 电视回传的全部官方按键（可搜索），保证「一个都不缺」
  自定义   —— 用户自建按键，支持按键/IRCC 原始指令/应用/网址/多步宏
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtCore import QEvent, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QPlainTextEdit,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QTextEdit,
    QWidget,
)

from ..config import Config, CustomButton
from ..core import keys as keydb
from ..core.errors import AuthRequired, NetworkError, TvError
from ..core.service import DeviceState, RemoteService
from . import theme
from .dialogs.custom_dialog import CustomButtonDialog
from .dialogs.pair_dialog import PairDialog
from .dialogs.settings_dialog import SettingsDialog
from .tasks import TaskRunner
from .widgets import DPad, HoldButton, LevelBar, Rocker, StatusDot, Toast, set_variant

APP_EMOJI = [
    ("netflix", "🎬"), ("youtube", "▶"), ("prime", "🎞"), ("disney", "🏰"),
    ("spotify", "🎵"), ("bilibili", "📺"), ("iqiyi", "🍿"), ("tencent", "🐧"),
    ("apple", "🍎"), ("music", "🎵"), ("game", "🎮"), ("video", "🎥"),
]


class MainWindow(QWidget):
    quit_requested = Signal()
    hidden_to_tray = Signal()

    def __init__(self, config: Config, service: RemoteService, runner: TaskRunner) -> None:
        super().__init__()
        self.config = config
        self.service = service
        self.runner = runner
        # 按键指令走单线程队列，保证连点/长按时指令顺序与实体遥控器一致
        self.cmd_runner = TaskRunner(self, max_threads=1)
        self._poll_busy = False
        self._pair_prompted = False
        self._all_key_buttons: Dict[str, QPushButton] = {}
        self._key_sections: List[tuple[str, QGridLayout, List[str]]] = []

        self.setWindowTitle("索尼电视遥控器")
        self.setMinimumSize(400, 560)
        self.resize(424, 776)
        self.setObjectName("Root")
        self.setStyleSheet(theme.stylesheet())

        self._build()
        self._install_shortcuts()
        self.apply_window_flags()

        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self._poll)
        self.poll_timer.start(int(max(1.0, config.ui.poll_interval) * 1000))

    # ================================================================== 构建
    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 10)
        root.setSpacing(8)
        root.addLayout(self._build_header())

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.addTab(self._build_remote_tab(), "遥控器")
        self.tabs.addTab(self._build_apps_tab(), "应用 / 输入")
        self.tabs.addTab(self._build_allkeys_tab(), "全部按键")
        self.tabs.addTab(self._build_custom_tab(), "自定义")
        self.tabs.setCurrentIndex(min(self.config.ui.last_tab, 3))
        root.addWidget(self.tabs, 1)

        root.addWidget(self._build_footer())
        self.toast = Toast(self)

    # ------------------------------------------------------------ 顶部
    def _build_header(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.setSpacing(9)

        self.status_dot = StatusDot()
        bar.addWidget(self.status_dot)

        text_col = QVBoxLayout()
        text_col.setSpacing(0)
        self.title_label = QLabel("BRAVIA 遥控器")
        self.title_label.setObjectName("AppTitle")
        self.sub_label = QLabel("正在连接电视…")
        self.sub_label.setObjectName("AppSub")
        text_col.addWidget(self.title_label)
        text_col.addWidget(self.sub_label)
        bar.addLayout(text_col)
        bar.addStretch(1)

        self.power_btn = HoldButton("电源")
        self.power_btn.setFixedSize(58, 34)
        self.power_btn.setToolTip("电源（开关机）")
        self.power_btn.setStyleSheet("font-size:12px;")
        set_variant(self.power_btn, "danger")
        self.power_btn.fired.connect(lambda: self._do("电源", self.service.power_toggle))
        bar.addWidget(self.power_btn)

        self.pin_btn = HoldButton("置顶")
        self.pin_btn.setFixedSize(50, 34)
        self.pin_btn.setToolTip("窗口始终置顶")
        self.pin_btn.setStyleSheet("font-size:12px;")
        set_variant(self.pin_btn, "ghost")
        self.pin_btn.fired.connect(self._toggle_on_top)
        bar.addWidget(self.pin_btn)

        self.settings_btn = HoldButton("⚙")
        self.settings_btn.setFixedSize(34, 34)
        self.settings_btn.setToolTip("设置")
        self.settings_btn.setStyleSheet("font-family:'Segoe UI Symbol'; font-size:14px;")
        set_variant(self.settings_btn, "ghost")
        self.settings_btn.fired.connect(self.open_settings)
        bar.addWidget(self.settings_btn)

        self._sync_pin_button()
        return bar

    # ------------------------------------------------------------ 遥控器页
    def _build_remote_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(2, 6, 2, 6)
        layout.setSpacing(10)

        # 第一行：电视 / 输入源 / 主页 / 返回
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        for text, names, tip in [
            ("电视", ("Tv", "TvInput"), "切到电视调谐器"),
            ("输入源", ("Input", "TvInput"), "切换输入源"),
            ("主页", ("Home",), "回到电视主页"),
            ("返回", ("Return", "Exit"), "返回上一级"),
        ]:
            btn = HoldButton(text)
            btn.setFixedHeight(40)
            btn.setToolTip(tip)
            set_variant(btn, "tap")
            btn.fired.connect(lambda n=names: self._press_alias(n))
            row1.addWidget(btn)
        layout.addLayout(row1)

        # 第二行：频道摇杆 + 方向盘 + 音量摇杆
        row2 = QHBoxLayout()
        row2.setSpacing(6)
        self.channel_rocker = Rocker("频道", show_value=False)
        self.channel_rocker.plus.fired.connect(lambda: self._press("ChannelUp"))
        self.channel_rocker.minus.fired.connect(lambda: self._press("ChannelDown"))
        row2.addWidget(self.channel_rocker)
        row2.addStretch(1)

        self.dpad = DPad()
        self.dpad.keyPressed.connect(self._press)
        row2.addWidget(self.dpad)
        row2.addStretch(1)

        self.volume_rocker = Rocker("音量", show_value=True)
        self.volume_rocker.plus.fired.connect(lambda: self._press("VolumeUp"))
        self.volume_rocker.minus.fired.connect(lambda: self._press("VolumeDown"))
        row2.addWidget(self.volume_rocker)
        layout.addLayout(row2)

        # 第三行：媒体控制（用中文短标签，避免不同机器的符号字体差异）
        media = QHBoxLayout()
        media.setSpacing(6)
        for text, name, tip in [
            ("上一", "Prev", "上一个"),
            ("快退", "Rewind", "快退"),
            ("播放", "PlayPause", "播放 / 暂停"),
            ("快进", "Forward", "快进"),
            ("下一", "Next", "下一个"),
            ("停止", "Stop", "停止"),
        ]:
            btn = HoldButton(text)
            btn.setFixedHeight(38)
            btn.setToolTip(tip)
            btn.setStyleSheet("font-size:12px;")
            btn.fired.connect(lambda n=name: self._press(n))
            media.addWidget(btn)
        layout.addLayout(media)

        # 第四行：数字键盘
        number_grid = QGridLayout()
        number_grid.setSpacing(7)
        digits = ["1", "2", "3", "4", "5", "6", "7", "8", "9", ".", "0", "确认"]
        for index, text in enumerate(digits):
            r, c = divmod(index, 3)
            if text == ".":
                name = "DOT"
            elif text == "确认":
                name = "Enter"
            else:
                name = f"Num{text}"
            btn = HoldButton(text)
            btn.setFixedHeight(42)
            btn.setStyleSheet("font-size:15px;")
            btn.fired.connect(lambda n=name: self._press(n))
            number_grid.addWidget(btn, r, c)
        layout.addLayout(number_grid)

        # 第五行：彩色键
        colors = QHBoxLayout()
        colors.setSpacing(7)
        for text, name, color in [
            ("红", "Red", theme.RED),
            ("绿", "Green", theme.GREEN),
            ("黄", "Yellow", theme.YELLOW),
            ("蓝", "Blue", theme.BLUE),
        ]:
            btn = HoldButton(text)
            btn.setFixedHeight(34)
            btn.setStyleSheet(
                f"color:{color}; font-weight:600; border-radius:10px;"
            )
            btn.fired.connect(lambda n=name: self._press(n))
            colors.addWidget(btn)
        layout.addLayout(colors)

        # 第六行：常用功能
        extras = QHBoxLayout()
        extras.setSpacing(7)
        for text, names in [
            ("图像模式", ("PictureMode",)),
            ("音轨", ("Audio",)),
            ("画面比例", ("Wide",)),
            ("字幕", ("SubTitle", "ClosedCaption")),
        ]:
            btn = HoldButton(text)
            btn.setFixedHeight(34)
            btn.setStyleSheet("font-size:12px; border-radius:10px;")
            btn.fired.connect(lambda n=names: self._press_alias(n))
            extras.addWidget(btn)
        layout.addLayout(extras)
        layout.addStretch(1)

        scroll.setWidget(body)
        return scroll

    # ------------------------------------------------------------ 应用页
    def _build_apps_tab(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(2, 6, 2, 6)
        outer.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("电视应用")
        title.setObjectName("SectionTitle")
        header.addWidget(title)
        header.addStretch(1)
        self.refresh_apps_btn = QPushButton("刷新")
        self.refresh_apps_btn.setFixedSize(56, 26)
        self.refresh_apps_btn.setStyleSheet("font-size:11px; border-radius:8px;")
        self.refresh_apps_btn.clicked.connect(self.refresh_catalog)
        header.addWidget(self.refresh_apps_btn)
        outer.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        inner = QWidget()
        self.apps_layout = QVBoxLayout(inner)
        self.apps_layout.setContentsMargins(0, 0, 0, 0)
        self.apps_layout.setSpacing(8)

        self.apps_grid = QGridLayout()
        self.apps_grid.setSpacing(7)
        self.apps_layout.addLayout(self.apps_grid)

        inputs_title = QLabel("输入源")
        inputs_title.setObjectName("SectionTitle")
        self.apps_layout.addWidget(inputs_title)
        self.inputs_grid = QGridLayout()
        self.inputs_grid.setSpacing(7)
        self.apps_layout.addLayout(self.inputs_grid)

        self.apps_hint = QLabel("连接电视后会自动读取已安装的应用。")
        self.apps_hint.setObjectName("Hint")
        self.apps_hint.setWordWrap(True)
        self.apps_layout.addWidget(self.apps_hint)
        self.apps_layout.addStretch(1)

        scroll.setWidget(inner)
        outer.addWidget(scroll, 1)

        self._render_inputs([])
        return page

    # ------------------------------------------------------------ 全部按键
    def _build_allkeys_tab(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(2, 6, 2, 6)
        outer.setSpacing(8)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索按键：字幕 / Hdmi / SubTitle…")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._filter_all_keys)
        outer.addWidget(self.search_edit)

        self.allkey_count = QLabel("")
        self.allkey_count.setObjectName("Hint")
        outer.addWidget(self.allkey_count)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.allkeys_body = QWidget()
        self.allkeys_layout = QVBoxLayout(self.allkeys_body)
        self.allkeys_layout.setContentsMargins(0, 0, 4, 0)
        self.allkeys_layout.setSpacing(10)
        scroll.setWidget(self.allkeys_body)
        outer.addWidget(scroll, 1)
        return page

    # ------------------------------------------------------------ 自定义页
    def _build_custom_tab(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(2, 6, 2, 6)
        outer.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("我的按键")
        title.setObjectName("SectionTitle")
        header.addWidget(title)
        header.addStretch(1)
        add_btn = QPushButton("＋ 新建")
        add_btn.setFixedSize(70, 26)
        add_btn.setStyleSheet("font-size:11px; border-radius:8px;")
        set_variant(add_btn, "primary")
        add_btn.clicked.connect(self.add_custom_button)
        header.addWidget(add_btn)
        outer.addLayout(header)

        hint = QLabel("支持官方按键、IRCC 原始指令、启动应用、在电视上打开网址，以及多步组合宏。右键图标可编辑或删除。")
        hint.setObjectName("Hint")
        hint.setWordWrap(True)
        outer.addWidget(hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        inner = QWidget()
        self.custom_layout = QGridLayout(inner)
        self.custom_layout.setContentsMargins(0, 2, 4, 2)
        self.custom_layout.setSpacing(8)
        scroll.setWidget(inner)
        outer.addWidget(scroll, 1)

        self._render_custom_buttons()
        return page

    # ------------------------------------------------------------ 底部
    def _build_footer(self) -> QWidget:
        frame = QFrame()
        frame.setFixedHeight(34)
        bar = QHBoxLayout(frame)
        bar.setContentsMargins(2, 0, 2, 0)
        bar.setSpacing(8)

        self.footer_label = QLabel("—")
        self.footer_label.setObjectName("Hint")
        bar.addWidget(self.footer_label)
        bar.addStretch(1)

        self.level_bar = LevelBar()
        bar.addWidget(self.level_bar)

        self.volume_label = QLabel("音量 –")
        self.volume_label.setObjectName("Hint")
        self.volume_label.setMinimumWidth(56)
        self.volume_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        bar.addWidget(self.volume_label)

        self.mute_btn = QPushButton("静音")
        self.mute_btn.setFixedSize(48, 24)
        self.mute_btn.setStyleSheet("font-size:11px; border-radius:8px;")
        self.mute_btn.clicked.connect(lambda: self._do("静音", self.service.toggle_mute))
        bar.addWidget(self.mute_btn)
        return frame

    # ------------------------------------------------------------ 快捷键
    def _install_shortcuts(self) -> None:
        """通过应用级事件过滤器实现快捷键。

        不用 QShortcut 的原因：窗口级快捷键会抢走搜索框里的字母输入，
        这里改为「焦点不在文本控件上才响应」，输入体验与全局热键兼得。
        """
        self._shortcut_map = {
            Qt.Key_Up: ("Up",),
            Qt.Key_Down: ("Down",),
            Qt.Key_Left: ("Left",),
            Qt.Key_Right: ("Right",),
            Qt.Key_Return: ("Confirm",),
            Qt.Key_Enter: ("Confirm",),
            Qt.Key_Backspace: ("Return", "Exit"),
            Qt.Key_Escape: ("Return", "Exit"),
            Qt.Key_H: ("Home",),
            Qt.Key_O: ("Options",),
            Qt.Key_I: ("Input", "TvInput"),
            Qt.Key_M: ("Mute",),
            Qt.Key_Space: ("PlayPause", "Play"),
            Qt.Key_Plus: ("VolumeUp",),
            Qt.Key_Equal: ("VolumeUp",),
            Qt.Key_Minus: ("VolumeDown",),
            Qt.Key_Underscore: ("VolumeDown",),
        }
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

    def eventFilter(self, obj, event) -> bool:
        if event.type() == QEvent.KeyPress and self.isActiveWindow() and self.isVisible():
            if QApplication.activePopupWidget() is None:
                focus = QApplication.focusWidget()
                if not isinstance(focus, (QLineEdit, QPlainTextEdit, QTextEdit, QComboBox)):
                    names = self._shortcut_map.get(event.key())
                    if names:
                        self._press_alias(names)
                        return True
        return super().eventFilter(obj, event)

    # ================================================================== 交互
    def _press(self, name: str) -> None:
        self.cmd_runner.submit(lambda: self.service.press(name), on_err=self._on_error)

    def _press_alias(self, names: tuple[str, ...]) -> None:
        available = set(self.service.state.keys) or set(keydb.KEY_CODES)
        resolved = keydb.resolve(names, available) or names[0]
        self._press(resolved)

    def _do(self, label: str, fn) -> None:
        self.cmd_runner.submit(fn, on_err=self._on_error)

    # ------------------------------------------------------------ 页面刷新
    def start(self) -> None:
        self.runner.submit(self.service.connect, self._on_connected, self._on_error)

    def refresh_catalog(self) -> None:
        def load():
            apps = self.service.refresh_apps()
            inputs = self.service.refresh_inputs()
            return apps, inputs

        self.runner.submit(load, lambda res: self._on_catalog(*res), self._on_error)

    def _on_connected(self, state: DeviceState) -> None:
        self._update_status(state)
        self._render_apps(state.apps)
        self._render_inputs(state.inputs)
        self._rebuild_all_keys(state.keys)
        self._update_volume(state)
        if state.needs_pairing and not self._pair_prompted:
            self._pair_prompted = True
            self.toast.show_message("需要在电视上完成配对授权", "error", 3200)
            QTimer.singleShot(400, lambda: self.open_pairing(auto=True))
        elif state.error and not state.online:
            self.toast.show_message(state.error, "error", 4000)

    def _on_catalog(self, apps: List[Dict[str, Any]], inputs: List[Dict[str, Any]]) -> None:
        self._render_apps(apps)
        self._render_inputs(inputs)
        self.toast.show_message("应用与输入源已刷新", "ok", 1600)

    # ------------------------------------------------------------ 状态展示
    def _update_status(self, state: DeviceState) -> None:
        if state.needs_pairing:
            self.status_dot.set_color("#e0a33a")
            text = "待配对 · 需要在电视上授权"
        elif not state.online:
            self.status_dot.set_color(theme.DANGER)
            text = "未连接 · 请检查电视电源与网络"
        elif state.power == "standby":
            self.status_dot.set_color("#e0a33a")
            text = f"{state.model} · 待机中"
        else:
            self.status_dot.set_color(theme.OK_GREEN)
            text = f"{state.model} · 已连接"

        self.sub_label.setText(text)
        if state.online and state.power == "active":
            self.footer_label.setText(f"延迟 {state.latency_ms} ms" if state.latency_ms else "已连接")
        elif state.needs_pairing:
            self.footer_label.setText("待配对")
        else:
            self.footer_label.setText("离线")

    def _update_volume(self, state: DeviceState) -> None:
        self.level_bar.set_value(state.volume, state.max_volume, state.muted)
        if state.muted:
            self.volume_label.setText("已静音")
            set_variant(self.mute_btn, "primary")
        else:
            self.volume_label.setText(f"音量 {state.volume}")
            set_variant(self.mute_btn, "")
        self.volume_rocker.set_value(str(state.volume))

    # ------------------------------------------------------------ 轮询
    def poll_now(self) -> None:
        """立即刷新一次状态（呼出窗口时用，比整轮重连轻得多）。"""
        self._poll_busy = False
        self._poll()

    def _poll(self) -> None:
        if self._poll_busy:
            return
        self._poll_busy = True

        def done(state: DeviceState) -> None:
            self._poll_busy = False
            self._update_status(state)
            self._update_volume(state)
            if state.needs_pairing and not self._pair_prompted:
                # 凭据失效（电视恢复出厂 / 重置 IP 控制）时自动重新引导配对
                self._pair_prompted = True
                self.toast.show_message("授权已失效，需要重新与电视配对", "error", 3200)
                QTimer.singleShot(400, lambda: self.open_pairing(auto=True))

        def failed(exc: Exception) -> None:
            self._poll_busy = False

        self.runner.submit(self.service.refresh_state, done, failed)

    # ------------------------------------------------------------ 应用/输入
    def _render_apps(self, apps: List[Dict[str, Any]]) -> None:
        self._clear_grid(self.apps_grid)
        if not apps:
            self.apps_hint.setText("没有读取到应用列表。确认电视已开机后再点「刷新」。")
            return
        self.apps_hint.setText(f"共 {len(apps)} 个应用，点击即可在电视上启动。")
        self._apps_total = len(apps)
        for index, app in enumerate(apps):
            title = str(app.get("title") or "未命名")
            uri = str(app.get("uri") or "")
            if not uri:
                continue
            row, col = divmod(index, 3)
            btn = QPushButton(f"{self._app_emoji(title)}  {self._elide(title, 8)}")
            btn.setFixedHeight(52)
            btn.setToolTip(f"{title}\n{uri}")
            set_variant(btn, "tap")
            btn.clicked.connect(lambda _=False, u=uri: self._launch_app(u))
            self.apps_grid.addWidget(btn, row, col)

    @staticmethod
    def _app_emoji(title: str) -> str:
        lowered = title.lower()
        for keyword, glyph in APP_EMOJI:
            if keyword in lowered:
                return glyph
        return "▦"

    def _render_inputs(self, inputs: List[Dict[str, Any]]) -> None:
        self._clear_grid(self.inputs_grid)
        items = [(str(i.get("title") or "输入"), str(i.get("uri") or "")) for i in inputs if i.get("uri")]
        if not items:
            items = [(f"HDMI {n}", "") for n in range(1, 5)]
        for index, (title, uri) in enumerate(items):
            row, col = divmod(index, 3)
            btn = QPushButton(title[:8])
            btn.setFixedHeight(40)
            btn.setToolTip(uri or "按 HDMI 按键切换")
            set_variant(btn, "tap")
            if uri:
                btn.clicked.connect(lambda _=False, u=uri: self._switch_input(u))
            else:
                btn.clicked.connect(lambda _=False, t=title: self._press("Hdmi" + t.split()[-1]))
            self.inputs_grid.addWidget(btn, row, col)

    def _launch_app(self, uri: str) -> None:
        self.cmd_runner.submit(
            lambda: self.service.launch_app(uri),
            on_ok=lambda _: self.toast.show_message("已在电视上启动应用", "ok", 1400),
            on_err=self._on_error,
        )

    def _switch_input(self, uri: str) -> None:
        self.cmd_runner.submit(
            lambda: self.service.switch_input(uri),
            on_ok=lambda _: self.toast.show_message("已切换输入源", "ok", 1400),
            on_err=self._on_error,
        )

    # ------------------------------------------------------------ 全部按键
    def _rebuild_all_keys(self, available: Dict[str, str]) -> None:
        # 清空旧内容
        while self.allkeys_layout.count():
            item = self.allkeys_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._key_sections.clear()
        self._all_key_buttons.clear()

        if not available:
            available = dict(keydb.KEY_CODES)

        names = [n for n in keydb.all_keys() if n in available]
        extras = sorted(n for n in available if n not in keydb.GROUPED_NAMES)
        # 同一台电视常有多个别名指向同一条 IRCC 指令（如 Input/TvInput），界面上只保留一个
        seen_codes: set[str] = set()

        def unique(candidates: List[str]) -> List[str]:
            keep: List[str] = []
            for name in candidates:
                token = available.get(name) or name
                if token in seen_codes:
                    continue
                seen_codes.add(token)
                keep.append(name)
            return keep

        sections: List[tuple[str, List[str]]] = []
        for title, group_names in keydb.GROUPS.items():
            present = unique([n for n in group_names if n in available])
            if present:
                sections.append((title, present))
        if extras:
            remaining = unique(extras)
            if remaining:
                sections.append(("其他指令", remaining))

        for title, group_names in sections:
            label = QLabel(title)
            label.setObjectName("SectionTitle")
            self.allkeys_layout.addWidget(label)
            grid = QGridLayout()
            grid.setSpacing(6)
            for index, name in enumerate(group_names):
                row, col = divmod(index, 4)
                btn = QPushButton(keydb.label(name))
                btn.setFixedHeight(32)
                btn.setToolTip(f"{name}\n{available.get(name, '')}")
                btn.setStyleSheet("font-size:11px; border-radius:9px;")
                btn.clicked.connect(lambda _=False, n=name: self._press(n))
                grid.addWidget(btn, row, col)
                self._all_key_buttons[name] = btn
            self.allkeys_layout.addLayout(grid)
            self._key_sections.append((title, grid, group_names))
        self.allkeys_layout.addStretch(1)
        self.allkey_count.setText(f"共 {len(self._all_key_buttons)} 个按键（电视实时回传）")
        self._filter_all_keys(self.search_edit.text())

    def _filter_all_keys(self, text: str) -> None:
        query = (text or "").strip().lower()
        visible_total = 0
        for title, grid, names in self._key_sections:
            any_visible = False
            for name in names:
                btn = self._all_key_buttons.get(name)
                if not btn:
                    continue
                haystack = f"{keydb.label(name)} {name} {self.service.state.keys.get(name, '')}".lower()
                match = not query or query in haystack
                btn.setVisible(match)
                any_visible = any_visible or match
                visible_total += int(match)
            # 分组标题：grid 位于 layout 中，标题紧随其后
            index = self._find_grid_index(grid)
            if index > 0:
                label_item = self.allkeys_layout.itemAt(index - 1)
                label = label_item.widget() if label_item else None
                if label:
                    label.setVisible(any_visible)
        if query:
            self.allkey_count.setText(f"匹配 {visible_total} 个按键")
        elif self._all_key_buttons:
            self.allkey_count.setText(f"共 {len(self._all_key_buttons)} 个按键（电视实时回传）")

    def _find_grid_index(self, grid: QGridLayout) -> int:
        for i in range(self.allkeys_layout.count()):
            item = self.allkeys_layout.itemAt(i)
            if item and item.layout() is grid:
                return i
        return -1

    # ------------------------------------------------------------ 自定义按键
    def _render_custom_buttons(self) -> None:
        self._clear_grid(self.custom_layout)
        buttons = self.config.custom_buttons
        if not buttons:
            placeholder = QLabel("还没有自定义按键。点右上角「＋ 新建」，或在「全部按键」里把常用键固定到这里。")
            placeholder.setObjectName("Hint")
            placeholder.setWordWrap(True)
            self.custom_layout.addWidget(placeholder, 0, 0, 1, 3)
            self.custom_layout.setRowStretch(1, 1)
            return
        for index, button in enumerate(buttons):
            row, col = divmod(index, 3)
            tile = QPushButton(f"{button.emoji}\n{button.label}")
            tile.setFixedHeight(64)
            tile.setStyleSheet("font-size:12px; border-radius:12px;")
            tile.setToolTip(self._describe(button))
            tile.setContextMenuPolicy(Qt.CustomContextMenu)
            tile.customContextMenuRequested.connect(
                lambda pos, b=button, w=tile: self._custom_context_menu(b, w, pos)
            )
            tile.clicked.connect(lambda _=False, b=button: self._run_custom(b))
            self.custom_layout.addWidget(tile, row, col)
        rows = (len(buttons) + 2) // 3
        self.custom_layout.setRowStretch(rows, 1)
        self.custom_layout.setColumnStretch(3, 1)

    @staticmethod
    def _elide(text: str, limit: int) -> str:
        return text if len(text) <= limit else text[: limit - 1] + "…"

    @staticmethod
    def _describe(button: CustomButton) -> str:
        labels = {
            "key": "官方按键", "ircc": "IRCC 指令", "app": "启动应用",
            "url": "打开网址", "macro": "组合宏",
        }
        return f"{labels.get(button.action, button.action)}：{button.value[:80]}"

    def _run_custom(self, button: CustomButton) -> None:
        self.cmd_runner.submit(
            lambda: self.service.execute_custom(button),
            on_err=self._on_error,
        )

    def _custom_context_menu(self, button: CustomButton, widget: QWidget, pos) -> None:
        from PySide6.QtWidgets import QMenu

        menu = QMenu(self)
        edit = menu.addAction("编辑")
        remove = menu.addAction("删除")
        chosen = menu.exec(widget.mapToGlobal(pos))
        if chosen is edit:
            self.edit_custom_button(button)
        elif chosen is remove:
            self.config.custom_buttons.remove(button)
            self.config.save()
            self._render_custom_buttons()
            self.toast.show_message("已删除自定义按键", "ok", 1400)

    def add_custom_button(self) -> None:
        dialog = CustomButtonDialog(None, self.service.state.apps, self)
        if dialog.exec() == QDialog.Accepted and dialog.result_button:
            self.config.upsert_button(dialog.result_button)
            self.config.save()
            self._render_custom_buttons()
            self.toast.show_message("已添加自定义按键", "ok", 1600)

    def edit_custom_button(self, button: CustomButton) -> None:
        dialog = CustomButtonDialog(button, self.service.state.apps, self)
        if dialog.exec() == QDialog.Accepted and dialog.result_button:
            self.config.upsert_button(dialog.result_button)
            self.config.save()
            self._render_custom_buttons()

    # ------------------------------------------------------------ 设置/配对
    def open_settings(self) -> None:
        dialog = SettingsDialog(self.config, self.service, self.runner, self)
        if dialog.exec() == QDialog.Accepted:
            self.apply_window_flags()
            self.poll_timer.start(int(max(1.0, self.config.ui.poll_interval) * 1000))
            self.toast.show_message("设置已保存", "ok", 1600)
            self.start()

    def open_pairing(self, auto: bool = False) -> None:
        dialog = PairDialog(self.service, self.runner, self)
        if dialog.exec() == QDialog.Accepted:
            self.toast.show_message("配对成功，遥控已可用", "ok", 2000)
            self.start()
        elif auto:
            self.toast.show_message("未完成配对：控制类操作会被电视拒绝", "error", 3000)

    def _toggle_on_top(self) -> None:
        self.config.ui.always_on_top = not self.config.ui.always_on_top
        self.config.save()
        self.apply_window_flags()
        self._sync_pin_button()

    def _sync_pin_button(self) -> None:
        set_variant(self.pin_btn, "primary" if self.config.ui.always_on_top else "ghost")

    def apply_window_flags(self) -> None:
        on_top = bool(self.config.ui.always_on_top)
        if bool(self.windowFlags() & Qt.WindowStaysOnTopHint) != on_top:
            self.setWindowFlag(Qt.WindowStaysOnTopHint, on_top)
            if self.isVisible():
                self.show()

    # ------------------------------------------------------------ 错误处理
    def _on_error(self, exc: Exception) -> None:
        if isinstance(exc, AuthRequired):
            self.status_dot.set_color("#e0a33a")
            self.sub_label.setText("待配对 · 需要在电视上授权")
            if not self._pair_prompted:
                self._pair_prompted = True
                self.toast.show_message("电视需要授权：请完成 PIN 配对", "error", 3600)
                QTimer.singleShot(300, lambda: self.open_pairing(auto=True))
            else:
                self.toast.show_message("操作被拒绝：请先完成配对或填写预共享密钥", "error", 3000)
            return
        if isinstance(exc, NetworkError):
            self.status_dot.set_color(theme.DANGER)
            self.sub_label.setText("未连接 · 请检查电视电源与网络")
            self.footer_label.setText("离线")
            self.toast.show_message("电视没有响应，请确认已开机且在同一网络", "error", 3000)
            return
        message = str(exc) if isinstance(exc, TvError) else f"操作失败：{exc}"
        self.toast.show_message(message, "error", 2800)

    # ------------------------------------------------------------ 工具
    @staticmethod
    def _clear_grid(grid: QGridLayout) -> None:
        while grid.count():
            item = grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "toast"):
            self.toast._reposition()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if hasattr(self, "toast") and self.toast.isVisible():
            self.toast._reposition()

    def closeEvent(self, event) -> None:
        self.config.ui.last_tab = self.tabs.currentIndex()
        self.config.save()
        if self.config.ui.minimize_to_tray:
            event.ignore()
            self.hide()
            self.hidden_to_tray.emit()
        else:
            event.accept()
            self.quit_requested.emit()
