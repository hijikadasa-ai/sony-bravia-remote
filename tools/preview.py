"""开发用：离屏渲染各页签，检查布局与字体（不联网、不读写用户配置）。"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("SONY_REMOTE_HOME", os.path.join(ROOT, ".preview_home"))
sys.path.insert(0, ROOT)

from PySide6.QtWidgets import QApplication

from app.config import Config, CustomButton
from app.core import keys as keydb
from app.core.service import DeviceState, RemoteService
from app.ui.main_window import MainWindow
from app.ui.tasks import TaskRunner


def main() -> None:
    app = QApplication(sys.argv)
    cfg = Config()
    cfg.ui.always_on_top = True
    cfg.custom_buttons = [
        CustomButton(label="影院模式", emoji="🎬", action="macro",
                     value="key:PictureMode\ndelay:300\nkey:Confirm"),
        CustomButton(label="B 站", emoji="📺", action="url", value="https://www.bilibili.com"),
        CustomButton(label="低音炮", emoji="🔊", action="key", value="Audio"),
    ]
    service = RemoteService(cfg)
    runner = TaskRunner(max_threads=1)
    win = MainWindow(cfg, service, runner)

    state = DeviceState(
        model="XR-85X90K", online=True, power="active", volume=8, muted=False,
        max_volume=100, latency_ms=13, keys=dict(keydb.KEY_CODES),
        apps=[
            {"title": "Netflix", "uri": "com.sony.dtv.com.netflix.ninja/.MainActivity"},
            {"title": "YouTube", "uri": "com.sony.dtv.com.google.android.youtube"},
            {"title": "Prime Video", "uri": "com.sony.dtv.com.amazon"},
            {"title": "Disney+", "uri": "com.sony.dtv.com.disney"},
            {"title": "哔哩哔哩", "uri": "com.sony.dtv.tv.danmaku.bili"},
            {"title": "Spotify", "uri": "com.sony.dtv.com.spotify"},
        ],
        inputs=[
            {"title": "HDMI 1", "uri": "extInput:hdmi?port=1"},
            {"title": "HDMI 2", "uri": "extInput:hdmi?port=2"},
            {"title": "HDMI 3", "uri": "extInput:hdmi?port=3"},
            {"title": "HDMI 4", "uri": "extInput:hdmi?port=4"},
        ],
    )
    win.service.state = state
    win._on_connected(state)
    win.move(-4000, -4000)   # 移出可视区，避免打断使用者
    win.show()
    win.poll_timer.stop()
    app.processEvents()

    out = os.path.dirname(os.path.abspath(__file__))
    for index, name in enumerate(["remote", "apps", "allkeys", "custom"]):
        win.tabs.setCurrentIndex(index)
        app.processEvents()
        win.grab().save(os.path.join(out, f".preview_{name}.png"))

    # 单独渲染"全部按键"页与方向盘特写
    win.dpad.grab().save(os.path.join(out, ".preview_dpad.png"))
    win.close()
    print("rendered")


if __name__ == "__main__":
    main()
