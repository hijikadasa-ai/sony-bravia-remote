"""索尼 BRAVIA 官方按键字典（IRCC Base64 指令表）。

数据来源：本机实测 XR-85X90K 通过 `system.getRemoteControllerInfo` 回传的 152 个按键，
并以索尼官方 IRCC-IP 文档 (pro-bravia.sony.net) 交叉校验。运行时会再用电视实时回传的
清单做一次覆盖合并，因此不同机型/固件的新增按键也会自动出现在「全部按键」中。
"""
from __future__ import annotations

from typing import Dict, Tuple

# ---------------------------------------------------------------------------
# 按键名 -> IRCC Base64 指令
# ---------------------------------------------------------------------------
KEY_CODES: Dict[str, str] = {
    # 数字与符号
    "Num1": "AAAAAQAAAAEAAAAAAw==",
    "Num2": "AAAAAQAAAAEAAAABAw==",
    "Num3": "AAAAAQAAAAEAAAACAw==",
    "Num4": "AAAAAQAAAAEAAAADAw==",
    "Num5": "AAAAAQAAAAEAAAAEAw==",
    "Num6": "AAAAAQAAAAEAAAAFAw==",
    "Num7": "AAAAAQAAAAEAAAAGAw==",
    "Num8": "AAAAAQAAAAEAAAAHAw==",
    "Num9": "AAAAAQAAAAEAAAAIAw==",
    "Num0": "AAAAAQAAAAEAAAAJAw==",
    "Num11": "AAAAAQAAAAEAAAAKAw==",
    "Num12": "AAAAAQAAAAEAAAALAw==",
    "Enter": "AAAAAQAAAAEAAAALAw==",
    "DOT": "AAAAAgAAAJcAAAAdAw==",
    "TenKey": "AAAAAgAAAJcAAAAMAw==",
    # 电源 / 输入
    "TvPower": "AAAAAQAAAAEAAAAVAw==",
    "WakeUp": "AAAAAQAAAAEAAAAuAw==",
    "PowerOff": "AAAAAQAAAAEAAAAvAw==",
    "Sleep": "AAAAAQAAAAEAAAAvAw==",
    "SleepTimer": "AAAAAQAAAAEAAAA2Aw==",
    "PicOff": "AAAAAQAAAAEAAAA+Aw==",
    "PictureOff": "AAAAAQAAAAEAAAA+Aw==",
    "Input": "AAAAAQAAAAEAAAAlAw==",
    "TvInput": "AAAAAQAAAAEAAAAlAw==",
    "Tv": "AAAAAQAAAAEAAAAkAw==",
    "TvAnalog": "AAAAAQAAAAEAAAA4Aw==",
    "Analog2": "AAAAAQAAAAEAAAA4Aw==",
    "Analog": "AAAAAgAAAHcAAAANAw==",
    "Digital": "AAAAAgAAAJcAAAAyAw==",
    "DigitalToggle": "AAAAAgAAAHcAAABSAw==",
    "TvAntennaCable": "AAAAAQAAAAEAAAAqAw==",
    "TvSatellite": "AAAAAgAAAMQAAABOAw==",
    "Tv_Radio": "AAAAAgAAABoAAABXAw==",
    "SyncMenu": "AAAAAgAAABoAAABYAw==",
    "Hdmi1": "AAAAAgAAABoAAABaAw==",
    "Hdmi2": "AAAAAgAAABoAAABbAw==",
    "Hdmi3": "AAAAAgAAABoAAABcAw==",
    "Hdmi4": "AAAAAgAAABoAAABdAw==",
    "Video1": "AAAAAQAAAAEAAABAAw==",
    "Video2": "AAAAAQAAAAEAAABBAw==",
    "Component1": "AAAAAgAAAKQAAAA2Aw==",
    "Component2": "AAAAAgAAAKQAAAA3Aw==",
    "AnalogRgb1": "AAAAAQAAAAEAAABDAw==",
    # 导航
    "Up": "AAAAAQAAAAEAAAB0Aw==",
    "Down": "AAAAAQAAAAEAAAB1Aw==",
    "Left": "AAAAAQAAAAEAAAA0Aw==",
    "Right": "AAAAAQAAAAEAAAAzAw==",
    "Confirm": "AAAAAQAAAAEAAABlAw==",
    "DpadCenter": "AAAAAgAAAJcAAABKAw==",
    "CursorUp": "AAAAAgAAAJcAAABPAw==",
    "CursorDown": "AAAAAgAAAJcAAABQAw==",
    "CursorLeft": "AAAAAgAAAJcAAABNAw==",
    "CursorRight": "AAAAAgAAAJcAAABOAw==",
    "Return": "AAAAAgAAAJcAAAAjAw==",
    "Exit": "AAAAAQAAAAEAAABjAw==",
    "Home": "AAAAAQAAAAEAAABgAw==",
    "Options": "AAAAAgAAAJcAAAA2Aw==",
    "ActionMenu": "AAAAAgAAAMQAAABLAw==",
    "ControlMenu": "AAAAAgAAABoAAAB1Aw==",
    "AndroidMenu": "AAAAAgAAAMQAAABPAw==",
    "ApplicationLauncher": "AAAAAgAAAMQAAAAqAw==",
    "Assists": "AAAAAgAAAMQAAAA7Aw==",
    "Help": "AAAAAgAAAMQAAABNAw==",
    "Display": "AAAAAQAAAAEAAAA6Aw==",
    "Jump": "AAAAAQAAAAEAAAA7Aw==",
    "TopMenu": "AAAAAgAAABoAAABgAw==",
    "PopUpMenu": "AAAAAgAAABoAAABhAw==",
    "Media": "AAAAAgAAAJcAAAA4Aw==",
    "GGuide": "AAAAAQAAAAEAAAAOAw==",
    "EPG": "AAAAAgAAAKQAAABbAw==",
    "iManual": "AAAAAgAAABoAAAB7Aw==",
    "GoogleDashboard": "AAAAAgAAAMQAAABwAw==",
    "FeaturedApp": "AAAAAgAAAMQAAABEAw==",
    "FeaturedAppVOD": "AAAAAgAAAMQAAABFAw==",
    "ACS": "AAAAAgAAAMQAAAArAw==",
    "B2bCustomizeKey": "AAAAAgAAAMQAAAB8Aw==",
    "AutoParingRequest": "AAAAAgAAAMQAAAB7Aw==",
    "DARWINLOOP": "AAAAAgAAAMQAAAAlAw==",
    "RecorderMenu": "AAAAAgAAAMQAAABIAw==",
    "STBMenu": "AAAAAgAAAMQAAABJAw==",
    "ShopRemoteControlForcedDynamic": "AAAAAgAAAJcAAABqAw==",
    "DemoMode": "AAAAAgAAAJcAAAB8Aw==",
    "DemoSurround": "AAAAAgAAAHcAAAB7Aw==",
    "*AD": "AAAAAgAAABoAAAA7Aw==",
    # 音量 / 频道 / 画面
    "VolumeUp": "AAAAAQAAAAEAAAASAw==",
    "VolumeDown": "AAAAAQAAAAEAAAATAw==",
    "Mute": "AAAAAQAAAAEAAAAUAw==",
    "Audio": "AAAAAQAAAAEAAAAXAw==",
    "MediaAudioTrack": "AAAAAQAAAAEAAAAXAw==",
    "AudioMixUp": "AAAAAgAAABoAAAA8Aw==",
    "AudioMixDown": "AAAAAgAAABoAAAA9Aw==",
    "AudioOutput_AudioSystem": "AAAAAgAAAMQAAAAiAw==",
    "AudioOutput_Toggle": "AAAAAgAAAMQAAAAkAw==",
    "WirelessSubwoofer": "AAAAAgAAAMQAAAB+Aw==",
    "ChannelUp": "AAAAAQAAAAEAAAAQAw==",
    "ChannelDown": "AAAAAQAAAAEAAAARAw==",
    "PAP": "AAAAAgAAAKQAAAB3Aw==",
    "Wide": "AAAAAgAAAKQAAAA9Aw==",
    "ClosedCaption": "AAAAAgAAAKQAAAAQAw==",
    "SubTitle": "AAAAAgAAAJcAAAAoAw==",
    "PictureMode": "AAAAAQAAAAEAAABkAw==",
    "FootballMode": "AAAAAgAAABoAAAB2Aw==",
    "Mode3D": "AAAAAgAAAHcAAABNAw==",
    "PhotoFrame": "AAAAAgAAABoAAABVAw==",
    # 播放控制
    "Play": "AAAAAgAAAJcAAAAaAw==",
    "Pause": "AAAAAgAAAJcAAAAZAw==",
    "PlayPause": "AAAAAgAAAJcAAAAPAw==",
    "Stop": "AAAAAgAAAJcAAAAYAw==",
    "Rewind": "AAAAAgAAAJcAAAAbAw==",
    "Forward": "AAAAAgAAAJcAAAAcAw==",
    "Prev": "AAAAAgAAAJcAAAA8Aw==",
    "Next": "AAAAAgAAAJcAAAA9Aw==",
    "FlashPlus": "AAAAAgAAAJcAAAB4Aw==",
    "FlashMinus": "AAAAAgAAAJcAAAB5Aw==",
    "Rec": "AAAAAgAAAJcAAAAgAw==",
    "OneTouchTimeRec": "AAAAAgAAABoAAABkAw==",
    "OneTouchView": "AAAAAgAAABoAAABlAw==",
    "BSCS": "AAAAAgAAAJcAAAAQAw==",
    "AdvancedBSCS": "AAAAAgAAAMQAAAAMAw==",
    "CS": "AAAAAgAAAJcAAAArAw==",
    "BS": "AAAAAgAAAJcAAAAsAw==",
    "Ddata": "AAAAAgAAAJcAAAAVAw==",
    "Teletext": "AAAAAQAAAAEAAAA/Aw==",
    # 彩色键
    "Red": "AAAAAgAAAJcAAAAlAw==",
    "Green": "AAAAAgAAAJcAAAAmAw==",
    "Yellow": "AAAAAgAAAJcAAAAnAw==",
    "Blue": "AAAAAgAAAJcAAAAkAw==",
    # 应用 / 语音
    "Netflix": "AAAAAgAAABoAAAB8Aw==",
    "YouTube": "AAAAAgAAAMQAAABHAw==",
    "GooglePlay": "AAAAAgAAAMQAAABGAw==",
    "MicPressedFromPairedRC": "AAAAAgAAAMQAAABuAw==",
    "MicPressedFromUnpairedRC": "AAAAAgAAAMQAAABvAw==",
}

# PartnerApp1..20（运营商/区域定制位，按需在「全部按键」里暴露）
# 末位十六进制递增，逐条精确列出，避免手写出错
_PARTNER = [
    "AAAAAgAACB8AAAAAAw==", "AAAAAgAACB8AAAABAw==", "AAAAAgAACB8AAAACAw==",
    "AAAAAgAACB8AAAADAw==", "AAAAAgAACB8AAAAEAw==", "AAAAAgAACB8AAAAFAw==",
    "AAAAAgAACB8AAAAGAw==", "AAAAAgAACB8AAAAHAw==", "AAAAAgAACB8AAAAIAw==",
    "AAAAAgAACB8AAAAJAw==", "AAAAAgAACB8AAAAKAw==", "AAAAAgAACB8AAAALAw==",
    "AAAAAgAACB8AAAAMAw==", "AAAAAgAACB8AAAANAw==", "AAAAAgAACB8AAAAOAw==",
    "AAAAAgAACB8AAAAPAw==", "AAAAAgAACB8AAAAQAw==", "AAAAAgAACB8AAAARAw==",
    "AAAAAgAACB8AAAASAw==", "AAAAAgAACB8AAAATAw==",
]
for _i, _code in enumerate(_PARTNER, start=1):
    KEY_CODES[f"PartnerApp{_i}"] = _code

# ---------------------------------------------------------------------------
# 中文标签
# ---------------------------------------------------------------------------
LABELS: Dict[str, str] = {
    "Num0": "0", "Num1": "1", "Num2": "2", "Num3": "3", "Num4": "4",
    "Num5": "5", "Num6": "6", "Num7": "7", "Num8": "8", "Num9": "9",
    "Num11": "#", "Num12": "确定", "Enter": "确认", "DOT": ".", "TenKey": "数字键盘",
    "TvPower": "电源", "WakeUp": "开机", "PowerOff": "关机", "Sleep": "待机",
    "SleepTimer": "睡眠定时", "PicOff": "关屏", "PictureOff": "关屏",
    "Input": "输入源", "TvInput": "输入源", "Tv": "电视", "TvAnalog": "模拟电视",
    "Analog2": "模拟电视", "Analog": "模拟", "Digital": "数字电视",
    "DigitalToggle": "数模切换", "TvAntennaCable": "天线/有线", "TvSatellite": "卫星",
    "Tv_Radio": "电视/收音", "SyncMenu": "BRAVIA Sync",
    "Hdmi1": "HDMI 1", "Hdmi2": "HDMI 2", "Hdmi3": "HDMI 3", "Hdmi4": "HDMI 4",
    "Video1": "视频 1", "Video2": "视频 2", "Component1": "分量 1", "Component2": "分量 2",
    "AnalogRgb1": "RGB",
    "Up": "上", "Down": "下", "Left": "左", "Right": "右", "Confirm": "确定",
    "DpadCenter": "方向键确定", "CursorUp": "光标上", "CursorDown": "光标下",
    "CursorLeft": "光标左", "CursorRight": "光标右",
    "Return": "返回", "Exit": "退出", "Home": "主页", "Options": "选项",
    "ActionMenu": "动作菜单", "ControlMenu": "控制菜单", "AndroidMenu": "安卓菜单",
    "ApplicationLauncher": "应用启动器", "Assists": "辅助", "Help": "帮助",
    "Display": "信息", "Jump": "跳转", "TopMenu": "顶部菜单", "PopUpMenu": "弹出菜单",
    "Media": "媒体", "GGuide": "节目指南", "EPG": "电子节目单", "iManual": "电子说明书",
    "GoogleDashboard": "Google 面板", "FeaturedApp": "推荐应用", "FeaturedAppVOD": "推荐点播",
    "ACS": "ACS", "B2bCustomizeKey": "商用自定义键", "AutoParingRequest": "自动配对",
    "DARWINLOOP": "DARWINLOOP", "RecorderMenu": "录像机菜单", "STBMenu": "机顶盒菜单",
    "ShopRemoteControlForcedDynamic": "商场动态模式", "DemoMode": "演示模式",
    "DemoSurround": "环绕演示", "*AD": "音频描述",
    "VolumeUp": "音量 +", "VolumeDown": "音量 −", "Mute": "静音", "Audio": "音轨",
    "MediaAudioTrack": "音轨切换", "AudioMixUp": "伴音 +", "AudioMixDown": "伴音 −",
    "AudioOutput_AudioSystem": "音频输出：音响", "AudioOutput_Toggle": "音频输出切换",
    "WirelessSubwoofer": "无线低音炮",
    "ChannelUp": "频道 +", "ChannelDown": "频道 −", "PAP": "画中画", "Wide": "画面比例",
    "ClosedCaption": "隐藏字幕", "SubTitle": "字幕", "PictureMode": "图像模式",
    "FootballMode": "足球模式", "Mode3D": "3D", "PhotoFrame": "相框模式",
    "Play": "播放", "Pause": "暂停", "PlayPause": "播放/暂停", "Stop": "停止",
    "Rewind": "快退", "Forward": "快进", "Prev": "上一个", "Next": "下一个",
    "FlashPlus": "快进 +", "FlashMinus": "快退 −", "Rec": "录制",
    "OneTouchTimeRec": "一键定时录制", "OneTouchView": "一键观看",
    "BSCS": "双语", "AdvancedBSCS": "高级双语", "CS": "CS", "BS": "BS",
    "Ddata": "数据广播", "Teletext": "图文电视",
    "Red": "红", "Green": "绿", "Yellow": "黄", "Blue": "蓝",
    "Netflix": "Netflix", "YouTube": "YouTube", "GooglePlay": "Google Play",
    "MicPressedFromPairedRC": "语音（已配对）", "MicPressedFromUnpairedRC": "语音（未配对）",
}
for _i in range(1, 21):
    LABELS.setdefault(f"PartnerApp{_i}", f"合作应用 {_i}")

# ---------------------------------------------------------------------------
# 分组（用于「全部按键」页；未列出的键自动归入「其他」）
# ---------------------------------------------------------------------------
GROUPS: Dict[str, Tuple[str, ...]] = {
    "电源与输入": (
        "TvPower", "WakeUp", "PowerOff", "Sleep", "SleepTimer", "PicOff", "PictureOff",
        "Input", "TvInput", "Tv", "TvAnalog", "Analog", "Analog2", "Digital",
        "DigitalToggle", "TvAntennaCable", "TvSatellite", "Tv_Radio", "SyncMenu",
        "Hdmi1", "Hdmi2", "Hdmi3", "Hdmi4", "Video1", "Video2", "Component1",
        "Component2", "AnalogRgb1",
    ),
    "导航与菜单": (
        "Up", "Down", "Left", "Right", "Confirm", "DpadCenter", "CursorUp", "CursorDown",
        "CursorLeft", "CursorRight", "Return", "Exit", "Home", "Options", "ActionMenu",
        "ControlMenu", "AndroidMenu", "ApplicationLauncher", "Assists", "Help", "Display",
        "Jump", "TopMenu", "PopUpMenu", "Media", "GGuide", "EPG", "iManual",
        "GoogleDashboard", "FeaturedApp", "FeaturedAppVOD", "ACS", "B2bCustomizeKey",
        "AutoParingRequest", "DARWINLOOP", "RecorderMenu", "STBMenu",
        "ShopRemoteControlForcedDynamic", "DemoMode", "DemoSurround", "*AD",
    ),
    "音量与画面": (
        "VolumeUp", "VolumeDown", "Mute", "Audio", "MediaAudioTrack", "AudioMixUp",
        "AudioMixDown", "AudioOutput_AudioSystem", "AudioOutput_Toggle", "WirelessSubwoofer",
        "ChannelUp", "ChannelDown", "PAP", "Wide", "ClosedCaption", "SubTitle",
        "PictureMode", "FootballMode", "Mode3D", "PhotoFrame",
    ),
    "数字键盘": ("Num1", "Num2", "Num3", "Num4", "Num5", "Num6", "Num7", "Num8", "Num9",
                 "Num0", "Num11", "DOT", "Enter", "TenKey"),
    "播放控制": (
        "Play", "Pause", "PlayPause", "Stop", "Rewind", "Forward", "Prev", "Next",
        "FlashPlus", "FlashMinus", "Rec", "OneTouchTimeRec", "OneTouchView",
        "BSCS", "AdvancedBSCS", "CS", "BS", "Ddata", "Teletext",
    ),
    "彩色键": ("Red", "Green", "Yellow", "Blue"),
    "应用与语音": (
        "Netflix", "YouTube", "GooglePlay", "MicPressedFromPairedRC",
        "MicPressedFromUnpairedRC",
    ) + tuple(f"PartnerApp{i}" for i in range(1, 21)),
}

GROUPED_NAMES = {n for names in GROUPS.values() for n in names}

# 主界面「遥控器」页使用的方向键别名（不同机型回传的命名不同）
DPAD_ALIASES = {
    "Up": ("Up", "CursorUp"),
    "Down": ("Down", "CursorDown"),
    "Left": ("Left", "CursorLeft"),
    "Right": ("Right", "CursorRight"),
    "Confirm": ("Confirm", "DpadCenter"),
}


def label(name: str) -> str:
    return LABELS.get(name, name)


def code_of(name: str) -> str | None:
    return KEY_CODES.get(name)


def resolve(names: tuple[str, ...] | str, available: set[str]) -> str | None:
    """在可用按键集合中挑一个存在的别名。"""
    if isinstance(names, str):
        names = (names,)
    for n in names:
        if n in available:
            return n
    return None


def all_keys() -> list[str]:
    """返回按键顺序：先分组顺序，再追加未分组的。"""
    ordered: list[str] = []
    for names in GROUPS.values():
        ordered.extend(names)
    ordered.extend(sorted(n for n in KEY_CODES if n not in GROUPED_NAMES))
    seen: set[str] = set()
    return [n for n in ordered if not (n in seen or seen.add(n))]
