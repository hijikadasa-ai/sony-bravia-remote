"""配置持久化：JSON + 原子写入，存储于 %APPDATA%\\SonyTVRemote\\config.json。"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List

APP_NAME = "SonyTVRemote"


def app_data_dir() -> Path:
    override = os.environ.get("SONY_REMOTE_HOME")
    if override:
        path = Path(override)
    elif os.name == "nt":
        path = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / APP_NAME
    else:
        path = Path.home() / ".config" / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_path() -> Path:
    # 便携模式：程序目录下有 config.json 时优先使用（方便放 U 盘）
    if getattr(sys, "frozen", False):
        portable = Path(sys.executable).parent / "config.json"
    else:
        portable = Path(__file__).resolve().parent.parent / "config.json"
    if portable.exists():
        return portable
    return app_data_dir() / "config.json"


@dataclass
class TvSettings:
    host: str = ""          # 首次运行时在设置里填写电视 IP
    port: int = 80
    psk: str = ""
    auth_cookie: str = ""
    client_id: str = ""
    nickname: str = "PC Remote"
    mac: str = ""
    timeout: float = 4.0

    def normalized(self) -> "TvSettings":
        if not self.client_id:
            self.client_id = f"SonyTvRemote:{uuid.uuid4().hex[:8]}"
        self.host = (self.host or "").strip()
        try:
            self.port = int(self.port or 80)
        except (TypeError, ValueError):
            self.port = 80
        self.timeout = max(1.0, min(15.0, float(self.timeout or 4.0)))
        return self


@dataclass
class UiSettings:
    always_on_top: bool = True
    minimize_to_tray: bool = True
    start_with_windows: bool = False
    start_minimized: bool = False
    poll_interval: float = 3.0
    last_tab: int = 0


@dataclass
class CustomButton:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    label: str = "新按键"
    emoji: str = "★"
    action: str = "key"          # key | ircc | app | url | macro
    value: str = ""              # 按键名 / IRCC Base64 / 应用 URI / 网址 / 宏脚本
    color: str = ""              # 留空用主题色

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Config:
    tv: TvSettings = field(default_factory=TvSettings)
    ui: UiSettings = field(default_factory=UiSettings)
    custom_buttons: List[CustomButton] = field(default_factory=list)

    # ---------------------------------------------------------------- 读写
    @classmethod
    def load(cls) -> "Config":
        path = config_path()
        data: Dict[str, Any] = {}
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                data = {}
        tv = TvSettings(**(data.get("tv") or {}))
        ui_raw = data.get("ui") or {}
        ui = UiSettings(**{k: v for k, v in ui_raw.items() if k in UiSettings.__annotations__})
        buttons: List[CustomButton] = []
        for item in data.get("custom_buttons") or []:
            if not isinstance(item, dict):
                continue
            fields = {k: v for k, v in item.items() if k in CustomButton.__annotations__}
            buttons.append(CustomButton(**fields))
        cfg = cls(tv=tv.normalized(), ui=ui, custom_buttons=buttons)
        return cfg

    def save(self) -> None:
        path = config_path()
        payload = {
            "version": 1,
            "tv": asdict(self.tv),
            "ui": asdict(self.ui),
            "custom_buttons": [b.to_dict() for b in self.custom_buttons],
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".cfg-", dir=str(path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                try:
                    os.unlink(tmp)
                except OSError:
                    pass

    # ---------------------------------------------------------------- 自定义按键
    def find_button(self, button_id: str) -> CustomButton | None:
        return next((b for b in self.custom_buttons if b.id == button_id), None)

    def upsert_button(self, button: CustomButton) -> None:
        existing = self.find_button(button.id)
        if existing:
            idx = self.custom_buttons.index(existing)
            self.custom_buttons[idx] = button
        else:
            self.custom_buttons.append(button)
