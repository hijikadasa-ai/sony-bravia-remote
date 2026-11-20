"""业务编排层：把「按键 / 应用 / 音量 / 宏」翻译成电视操作，并维护连接状态。

不依赖任何 UI 框架，因此可被单元测试直接使用；所有方法都在工作线程里被调用。
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from ..config import Config, CustomButton
from . import keys as keydb
from .client import TvClient, send_wol
from .errors import AuthRequired, NetworkError, TvError


@dataclass
class DeviceState:
    model: str = ""
    online: bool = False
    power: str = "unknown"       # active | standby | unknown
    volume: int = 0
    muted: bool = False
    max_volume: int = 100
    latency_ms: int = 0
    needs_pairing: bool = False
    error: str = ""
    keys: Dict[str, str] = field(default_factory=dict)      # 电视实际支持的按键
    apps: List[Dict[str, Any]] = field(default_factory=list)
    inputs: List[Dict[str, Any]] = field(default_factory=list)


class RemoteService:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.state = DeviceState()
        self._lock = threading.RLock()
        self.config.tv.normalized()   # 补齐 client_id 等派生字段
        self.client = self._make_client()

    # ------------------------------------------------------------------ 基础
    def _make_client(self) -> TvClient:
        tv = self.config.tv
        return TvClient(
            host=tv.host,
            port=tv.port,
            psk=tv.psk,
            auth_cookie=tv.auth_cookie,
            client_id=tv.client_id,
            nickname=tv.nickname,
            timeout=tv.timeout,
        )

    def rebuild(self) -> None:
        """设置变更后重建连接。"""
        old = self.client
        self.config.tv.normalized()   # 补齐 client_id 等派生字段
        self.client = self._make_client()
        old.close()
        with self._lock:
            self.state.online = False
            self.state.needs_pairing = False

    def persist_auth(self) -> None:
        self.config.tv.auth_cookie = self.client.auth_cookie
        self.config.save()

    # ------------------------------------------------------------------ 连接
    def connect(self) -> DeviceState:
        """探测设备、拉取按键表与能力清单。失败也返回状态而不抛异常。"""
        with self._lock:
            self.state = DeviceState()
        if not (self.config.tv.host or "").strip():
            with self._lock:
                self.state.error = "尚未设置电视 IP，请打开设置填写"
                self.state.online = False
            return self.state
        started = time.perf_counter()
        try:
            info = self.client.get_interface_information()
            power = self.client.get_power_status()
            latency = (time.perf_counter() - started) * 1000.0
            keys = {k["name"]: k["value"] for k in self.client.get_remote_controller_info()}
            volume: Dict[str, Any] = {}
            apps: List[Dict[str, Any]] = []
            inputs: List[Dict[str, Any]] = []
            if power == "active":
                try:
                    volume = self.client.get_volume_information()
                except TvError:
                    volume = {}
                try:
                    apps = self.client.get_application_list()
                except TvError:
                    apps = []
                try:
                    inputs = self.client.get_external_inputs()
                except TvError:
                    inputs = []
            merged = dict(keydb.KEY_CODES)
            merged.update(keys)  # 电视回传的为准
            with self._lock:
                self.state = DeviceState(
                    model=str(info.get("modelName", "") or "BRAVIA"),
                    online=True,
                    power=power,
                    volume=int(volume.get("volume", 0) or 0),
                    muted=bool(volume.get("mute", False)),
                    max_volume=int(volume.get("maxVolume", 100) or 100),
                    latency_ms=int(latency),
                    needs_pairing=False,
                    keys=merged,
                    apps=apps,
                    inputs=inputs,
                )
                return self.state
        except NetworkError as exc:
            with self._lock:
                self.state.online = False
                self.state.error = str(exc)
                self.state.power = "unknown"
            return self.state
        except TvError as exc:
            with self._lock:
                self.state.online = True
                self.state.error = str(exc)
                self.state.needs_pairing = isinstance(exc, AuthRequired)
            return self.state

    def refresh_state(self) -> DeviceState:
        """轻量轮询：只刷新电源与音量。"""
        try:
            power = self.client.get_power_status()
            with self._lock:
                self.state.online = True
                self.state.needs_pairing = False
                self.state.error = ""
                self.state.power = power
            if power == "active":
                vol = self.client.get_volume_information()
                with self._lock:
                    self.state.volume = int(vol.get("volume", self.state.volume) or 0)
                    self.state.muted = bool(vol.get("mute", False))
                    self.state.max_volume = int(vol.get("maxVolume", 100) or 100)
        except NetworkError as exc:
            with self._lock:
                self.state.online = False
                self.state.error = str(exc)
        except TvError as exc:
            with self._lock:
                self.state.online = True
                self.state.error = str(exc)
                self.state.needs_pairing = isinstance(exc, AuthRequired)
        return self.state

    # ------------------------------------------------------------------ 配对
    def begin_pairing(self) -> None:
        """触发电视弹出 PIN 对话框（预期抛 AuthRequired(needs_pin=True)）。"""
        self.client.act_register(None)

    def finish_pairing(self, pin: str) -> None:
        self.client.act_register(pin)
        # 有的机型会「200 但凭据不可用」，这里发一个无副作用的控制指令做真实校验：
        # 读当前电源状态后原样写回，未授权会返回 401/403。
        try:
            status = self.client.get_power_status()
            self.client.set_power_status(status != "standby")
        except AuthRequired as exc:
            self.client.auth_cookie = ""
            raise TvError("配对凭据未被电视接受，请重新点「开始配对」再试一次") from exc
        self.persist_auth()
        with self._lock:
            self.state.needs_pairing = False
            self.state.error = ""

    # ------------------------------------------------------------------ 按键
    def code_for(self, name: str) -> str:
        with self._lock:
            code = self.state.keys.get(name) or keydb.KEY_CODES.get(name, "")
        if not code:
            raise TvError(f"电视不支持按键「{keydb.label(name)}」")
        return code

    def press(self, name: str) -> None:
        self.client.send_ircc(self.code_for(name))

    def press_many(self, names: List[str], interval: float = 0.18) -> None:
        for i, name in enumerate(names):
            if i:
                time.sleep(interval)
            self.press(name)

    def send_raw(self, code: str) -> None:
        code = (code or "").strip()
        if not code or len(code) < 8:
            raise TvError("IRCC 指令格式不正确")
        self.client.send_ircc(code)

    # ------------------------------------------------------------------ 音量 / 电源
    def volume_step(self, delta: int) -> None:
        key = "VolumeUp" if delta > 0 else "VolumeDown"
        for _ in range(max(1, abs(int(delta)))):
            self.press(key)

    def set_volume(self, value: int) -> None:
        max_v = max(1, self.state.max_volume)
        value = max(0, min(max_v, int(value)))
        self.client.set_audio_volume(value)
        with self._lock:
            self.state.volume = value
            if value > 0:
                self.state.muted = False

    def set_muted(self, muted: bool) -> None:
        self.client.set_audio_mute(bool(muted))
        with self._lock:
            self.state.muted = bool(muted)

    def toggle_mute(self) -> None:
        try:
            self.set_muted(not self.state.muted)
        except TvError:
            self.press("Mute")

    def power_toggle(self) -> None:
        try:
            self.press("TvPower")
        except NetworkError:
            # 电视可能处于深度待机导致 HTTP 不可达：先唤醒再补一条开机指令
            self.wake_on_lan()
            time.sleep(1.5)
            self.press("WakeUp")

    def power_on(self) -> None:
        try:
            self.client.set_power_status(True)
        except NetworkError:
            self.wake_on_lan()
            time.sleep(1.2)
            self.press("WakeUp")

    def power_off(self) -> None:
        self.press("PowerOff")

    def wake_on_lan(self) -> None:
        mac = (self.config.tv.mac or "").strip()
        if mac:
            send_wol(mac)

    # ------------------------------------------------------------------ 应用 / 输入源
    def launch_app(self, uri: str) -> None:
        self.client.set_active_app(uri)

    def open_url(self, url: str) -> None:
        url = (url or "").strip()
        if not url:
            raise TvError("网址为空")
        if "://" not in url:
            url = "https://" + url
        self.client.set_active_app(f"localapp://webappruntime?url={quote(url, safe='')}")

    def switch_input(self, uri: str) -> None:
        self.client.set_play_content(uri)

    def refresh_apps(self) -> List[Dict[str, Any]]:
        apps = self.client.get_application_list()
        with self._lock:
            self.state.apps = apps
        return apps

    def refresh_inputs(self) -> List[Dict[str, Any]]:
        inputs = self.client.get_external_inputs()
        with self._lock:
            self.state.inputs = inputs
        return inputs

    # ------------------------------------------------------------------ 宏 / 自定义按键
    def run_macro(self, script: str) -> None:
        """宏脚本，每行一步：

        key:Home          按官方按键
        ircc:AAAA...      直接发 IRCC 指令
        app:<uri>         启动应用
        url:https://...   在电视浏览器打开网址
        delay:500         等待毫秒
        """
        for raw in (script or "").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            verb, _, arg = line.partition(":")
            verb = verb.strip().lower()
            arg = arg.strip()
            if verb == "key":
                self.press(arg)
            elif verb == "ircc":
                self.send_raw(arg)
            elif verb == "app":
                self.launch_app(arg)
            elif verb == "url":
                self.open_url(arg)
            elif verb == "delay":
                try:
                    time.sleep(max(0, int(arg)) / 1000.0)
                except ValueError:
                    pass
            else:
                raise TvError(f"无法识别的宏指令：{line}")
            time.sleep(0.12)

    def execute_custom(self, button: CustomButton) -> None:
        action = (button.action or "key").lower()
        value = button.value or ""
        if action == "key":
            self.press(value)
        elif action == "ircc":
            self.send_raw(value)
        elif action == "app":
            self.launch_app(value)
        elif action == "url":
            self.open_url(value)
        elif action == "macro":
            self.run_macro(value)
        else:
            raise TvError(f"未知的按键类型：{action}")
