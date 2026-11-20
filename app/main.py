"""程序入口：单实例守护 + 系统托盘 + 主窗口。

启动流程：加载配置 → 建服务与线程池 → 建托盘 → 显示主窗口（或最小化到托盘）→ 自动连接电视。
"""
from __future__ import annotations

import sys
from pathlib import Path

# 允许 `python main.py` 直接运行
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QIcon, QLinearGradient, QPainter, QPainterPath, QPixmap
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from app.config import Config, config_path
from app.core.service import RemoteService
from app.ui import theme as ui_theme
from app.ui.main_window import MainWindow
from app.ui.tasks import TaskRunner

SERVER_NAME = "SonyTVRemote-single-instance"


def build_icon(size: int = 64) -> QIcon:
    """用绘制方式生成托盘/窗口图标，避免外部资源依赖。"""
    icon = QIcon()
    for side in (16, 24, 32, 48, 64, 128, 256):
        pix = QPixmap(side, side)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.Antialiasing)
        unit = side / 64.0

        # 底板
        radius = 14 * unit
        grad = QLinearGradient(0, 0, side, side)
        grad.setColorAt(0.0, QColor("#5b96f7"))
        grad.setColorAt(1.0, QColor("#2f5cad"))
        painter.setPen(Qt.NoPen)
        painter.setBrush(grad)
        painter.drawRoundedRect(QRectF(2 * unit, 2 * unit, 60 * unit, 60 * unit), radius, radius)

        # 屏幕
        screen = QRectF(12 * unit, 16 * unit, 40 * unit, 28 * unit)
        painter.setBrush(QColor("#0f1420"))
        painter.drawRoundedRect(screen, 4 * unit, 4 * unit)

        # 播放三角
        path = QPainterPath()
        path.moveTo(QPointF(27 * unit, 22 * unit))
        path.lineTo(QPointF(27 * unit, 38 * unit))
        path.lineTo(QPointF(41 * unit, 30 * unit))
        path.closeSubpath()
        painter.setBrush(QColor("#ffffff"))
        painter.drawPath(path)

        # 底座
        painter.setBrush(QColor(255, 255, 255, 200))
        painter.drawRoundedRect(QRectF(26 * unit, 48 * unit, 12 * unit, 3 * unit), 1.5 * unit, 1.5 * unit)
        painter.end()
        icon.addPixmap(pix)
    return icon


class TrayApp:
    def __init__(self, app: QApplication) -> None:
        self.app = app
        self.first_run = not config_path().exists()
        self.config = Config.load()
        self.service = RemoteService(self.config)
        self.runner = TaskRunner(max_threads=4)

        self.window = MainWindow(self.config, self.service, self.runner)
        self.window.setWindowIcon(build_icon())
        self.window.quit_requested.connect(self.quit)
        self.window.hidden_to_tray.connect(self._notify_tray)

        self.tray = QSystemTrayIcon(build_icon(), app)
        self.tray.setToolTip("索尼电视遥控器")
        self.tray.setContextMenu(self._build_menu())
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

        self._notify_once = True
        self.window.start()

        minimized = "--minimized" in sys.argv or self.config.ui.start_minimized
        needs_setup = not (self.config.tv.host or "").strip()
        if minimized and not needs_setup:
            self.window.hide()
        else:
            # 还没填电视 IP 时不要躲进托盘，直接把界面摆出来
            self.window.show()
            self.window.activateWindow()
            self.window.raise_()

        if needs_setup or self.first_run:
            QTimer.singleShot(600, self.window.open_settings)

    # ---------------------------------------------------------------- 托盘
    def _build_menu(self) -> QMenu:
        menu = QMenu()
        show_action = menu.addAction("显示遥控器")
        show_action.triggered.connect(self.show_window)
        menu.addSeparator()
        menu.addAction("开机 / 关机").triggered.connect(
            lambda: self.window.cmd_runner.submit(self.service.power_toggle, on_err=self.window._on_error)
        )
        menu.addAction("静音").triggered.connect(
            lambda: self.window.cmd_runner.submit(self.service.toggle_mute, on_err=self.window._on_error)
        )
        volume_menu = menu.addMenu("音量")
        volume_menu.addAction("音量 +").triggered.connect(lambda: self.window._press("VolumeUp"))
        volume_menu.addAction("音量 −").triggered.connect(lambda: self.window._press("VolumeDown"))
        menu.addSeparator()
        menu.addAction("设置…").triggered.connect(self.window.open_settings)
        menu.addSeparator()
        menu.addAction("退出").triggered.connect(self.quit)
        return menu

    def _on_tray_activated(self, reason) -> None:
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            if self.window.isVisible() and not self.window.isMinimized():
                self.window.hide()
            else:
                self.show_window()

    def show_window(self) -> None:
        self.window.showNormal()
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()
        # 已连接时只需轻量刷新，避免每次呼出都重拉 152 个按键与应用列表
        if self.service.state.online:
            self.window.poll_now()
        else:
            self.window.start()

    def _notify_tray(self) -> None:
        if self._notify_once:
            self._notify_once = False
            self.tray.showMessage(
                "索尼电视遥控器", "已最小化到托盘，双击右下角图标可呼出。",
                QSystemTrayIcon.Information, 2600,
            )

    # ---------------------------------------------------------------- 退出
    def quit(self) -> None:
        try:
            self.config.ui.last_tab = self.window.tabs.currentIndex()
            self.config.save()
        except Exception:
            pass
        self.window.cmd_runner.shutdown()
        self.runner.shutdown()
        self.service.client.close()
        self.tray.hide()
        self.app.quit()


def main() -> int:
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName("SonyTVRemote")
    app.setApplicationDisplayName("索尼电视遥控器")
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(ui_theme.stylesheet())
    app.setWindowIcon(build_icon())

    # 单实例：已有进程时唤起它的窗口
    socket = QLocalSocket()
    socket.connectToServer(SERVER_NAME)
    if socket.waitForConnected(300):
        socket.write(b"show")
        socket.flush()
        socket.waitForBytesWritten(300)
        socket.disconnectFromServer()
        return 0

    QLocalServer.removeServer(SERVER_NAME)
    server = QLocalServer()
    server.listen(SERVER_NAME)

    tray_app = TrayApp(app)

    def on_new_connection() -> None:
        conn = server.nextPendingConnection()
        if conn:
            conn.readyRead.connect(lambda: tray_app.show_window())
            conn.disconnected.connect(conn.deleteLater)

    server.newConnection.connect(on_new_connection)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        tray_app.window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
