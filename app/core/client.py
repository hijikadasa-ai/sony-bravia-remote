"""索尼 BRAVIA 局域网接口客户端（IRCC + REST）。

协议要点（实测 XR-85X90K / interfaceVersion 5.7.0）：
* 只读方法（getPowerStatus / getVolumeInformation / getRemoteControllerInfo …）无需授权；
* 控制方法（setAudioVolume / setActiveApp / ircc …）需要设备注册，否则返回 403 + auth_url；
* 设备注册走 POST /sony/accessControl 的 actRegister：先不带凭据调用 → 401 + 电视弹 4 位 PIN
  → 再带 Authorization: Basic base64(":"+PIN) 调用同一请求体 → 返回 Set-Cookie: auth=…
  → 之后所有请求携带该 Cookie；
* 若电视端设置了预共享密钥，则所有请求携带 X-Auth-PSK 头即可，无需 PIN。

本类只负责「怎么发请求」，不含任何业务编排与 UI 逻辑。
"""
from __future__ import annotations

import base64
import json
import re
import socket
import threading
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests

from .errors import AuthRequired, NetworkError, TvResponseError, TvError

IRCC_SOAP_ACTION = '"urn:schemas-sony-com:service:IRCC:1#X_SendIRCC"'
_COOKIE_RE = re.compile(r"auth=([^;,\s]+)")


class TvClient:
    """单个电视连接的线程安全 HTTP 客户端（内部串行化，保持长连接以降低按键延迟）。"""

    def __init__(
        self,
        host: str,
        port: int = 80,
        psk: str = "",
        auth_cookie: str = "",
        client_id: str = "SonyTvRemote:1",
        nickname: str = "PC Remote",
        timeout: float = 4.0,
    ) -> None:
        self.host = (host or "").strip()
        self.port = int(port or 80)
        self.psk = (psk or "").strip()
        self.auth_cookie = (auth_cookie or "").strip()
        self.client_id = client_id
        self.nickname = nickname
        self.timeout = timeout
        self._lock = threading.RLock()
        self._session = requests.Session()
        self._session.trust_env = False  # 避开系统代理，局域网直连
        self._req_id = 0

    # ------------------------------------------------------------------ 基础
    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def close(self) -> None:
        try:
            self._session.close()
        except Exception:
            pass

    def _headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        h = {"Connection": "keep-alive"}
        if self.psk:
            h["X-Auth-PSK"] = self.psk
        if self.auth_cookie:
            h["Cookie"] = f"auth={self.auth_cookie}"
        if extra:
            h.update(extra)
        return h

    def _request(
        self,
        method: str,
        path: str,
        data: Any = None,
        headers: Optional[Dict[str, str]] = None,
        retries: int = 1,
    ) -> requests.Response:
        last_exc: Optional[Exception] = None
        with self._lock:  # 串行化：requests.Session 非线程安全，局域网下串行开销可忽略
            for attempt in range(retries + 1):
                try:
                    resp = self._session.request(
                        method,
                        self.base_url + path,
                        data=data,
                        headers=self._headers(headers),
                        timeout=self.timeout,
                    )
                except requests.exceptions.RequestException as exc:
                    last_exc = exc
                    if attempt < retries:
                        time.sleep(0.12)
                        continue
                    raise NetworkError(
                        f"无法连接电视 {self.host}，请确认电视已开机、与本机在同一局域网且 IP 正确",
                        detail=type(exc).__name__,
                    ) from exc
                if resp.status_code >= 500 and attempt < retries:
                    time.sleep(0.15)
                    continue
                return resp
        raise NetworkError("连接电视失败", detail=str(last_exc))

    # ------------------------------------------------------------------ REST
    def rest(self, service: str, method: str, params: Optional[list] = None, version: str = "1.0") -> list:
        self._req_id += 1
        payload = {"method": method, "params": params or [], "id": self._req_id, "version": version}
        resp = self._request(
            "POST",
            f"/sony/{service}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        if resp.status_code in (401, 403):
            raise AuthRequired(
                "电视拒绝了该操作：需要在电视上完成设备注册（PIN 配对）或填写预共享密钥",
                needs_pin=(resp.status_code == 401),
                detail=resp.text[:200],
            )
        if resp.status_code != 200:
            raise TvError(f"电视返回异常状态 HTTP {resp.status_code}", detail=resp.text[:200], code=resp.status_code)
        try:
            body = resp.json()
        except ValueError as exc:
            raise TvError("电视返回了无法解析的数据", detail=resp.text[:200]) from exc
        if "error" in body and body["error"]:
            code = body["error"][0] if isinstance(body["error"], list) else None
            name = body["error"][1] if isinstance(body["error"], list) and len(body["error"]) > 1 else ""
            raise TvResponseError(f"电视处理失败：{name or '未知原因'}（错误码 {code}）", code=code)
        return body.get("result") or []

    def rest_one(self, service: str, method: str, params: Optional[list] = None, version: str = "1.0") -> Any:
        result = self.rest(service, method, params, version)
        return result[0] if result else None

    # ------------------------------------------------------------------ IRCC
    def send_ircc(self, code: str) -> None:
        """发送一个 IRCC 按键指令。

        端点要求标准的 SOAP 信封（直接把 Base64 码当 body 发，
        2021+ 机型会返回 500）。
        """
        if not code:
            raise TvError("按键指令为空")
        body = (
            '<?xml version="1.0"?>'
            '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
            's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
            "<s:Body>"
            '<u:X_SendIRCC xmlns:u="urn:schemas-sony-com:service:IRCC:1">'
            f"<IRCCCode>{code}</IRCCCode>"
            "</u:X_SendIRCC>"
            "</s:Body>"
            "</s:Envelope>"
        )
        resp = self._request(
            "POST",
            "/sony/ircc",
            data=body.encode("utf-8"),
            headers={"Content-Type": 'text/xml; charset="utf-8"', "SOAPACTION": IRCC_SOAP_ACTION},
        )
        if resp.status_code in (401, 403):
            raise AuthRequired("电视拒绝了按键：需要先在电视上完成配对授权", needs_pin=(resp.status_code == 401))
        if resp.status_code not in (200, 204):
            raise TvError(f"按键发送失败（HTTP {resp.status_code}）", code=resp.status_code, detail=resp.text[:200])

    # ------------------------------------------------------------------ 配对
    def act_register(self, pin: Optional[str] = None) -> str:
        """设备注册（对应索尼 accessControl / actRegister）。

        索尼的注册流程是标准的 HTTP Basic 挑战：
        1. 不带凭据调用 → 401 + ``WWW-Authenticate: Basic realm="Private Page"``，
           同时电视屏幕上弹出 4 位 PIN；
        2. 带上 ``Authorization: Basic base64(":"+PIN)`` 再次调用同一个请求体
           → 200 + ``Set-Cookie: auth=...``，此后所有请求携带该 Cookie。

        注意：PIN **只能**放在 Authorization 头里。若塞进 params 第三项，
        电视会返回 200 却不签发凭据（表现为「已完成注册但未返回授权凭据」）。

        返回 None 表示需要用户输入 PIN；返回 cookie 字符串表示注册成功。
        """
        params: list = [
            {"clientid": self.client_id, "nickname": self.nickname, "level": "private"},
            [{"value": "yes", "function": "WOL"}],
        ]
        self._req_id += 1
        payload = {"method": "actRegister", "params": params, "id": self._req_id, "version": "1.0"}
        headers = {"Content-Type": "application/json"}
        if pin:
            raw = f":{str(pin).strip()}".encode("utf-8")
            headers["Authorization"] = "Basic " + base64.b64encode(raw).decode("ascii")

        # 注册请求可能要在电视上等人看 PIN，超时给长一点
        old_timeout = self.timeout
        self.timeout = max(self.timeout, 25.0)
        try:
            resp = self._request(
                "POST",
                "/sony/accessControl",
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                retries=0,
            )
        finally:
            self.timeout = old_timeout

        if resp.status_code == 200:
            cookie = self._extract_auth_cookie(resp)
            if cookie:
                self.auth_cookie = cookie
                return cookie
            body = resp.text[:200]
            if pin:
                raise TvError(
                    "电视接受了 PIN 但没有下发授权凭据，请重试一次；若反复失败，"
                    "可在电视「IP 控制」中改用预共享密钥方式",
                    detail=body,
                )
            raise TvError("电视未下发授权凭据，请重试", detail=body)
        if resp.status_code == 401:
            raise AuthRequired("请查看电视屏幕上的 4 位 PIN 并输入", needs_pin=True)
        if resp.status_code == 403:
            raise TvError("电视禁止注册：请检查电视「IP 控制」设置中的认证方式")
        raise TvError(f"注册失败（HTTP {resp.status_code}）", detail=resp.text[:200], code=resp.status_code)

    @staticmethod
    def _extract_auth_cookie(resp: requests.Response) -> str:
        """从响应中取出 auth 哈希。

        索尼部分机型的 Set-Cookie 不符合 RFC（引号/多余分号），requests 的
        CookieJar 可能解析不到，所以这里直接扫原始响应头兜底。
        """
        try:
            jar = resp.cookies.get("auth")
            if jar:
                return jar.strip()
        except Exception:
            pass
        candidates: List[str] = []
        try:
            candidates.extend(resp.raw.headers.getlist("Set-Cookie"))  # type: ignore[union-attr]
        except Exception:
            pass
        header = resp.headers.get("Set-Cookie", "")
        if header:
            candidates.append(header)
        for raw in candidates:
            m = _COOKIE_RE.search(raw or "")
            if m:
                return m.group(1).strip().strip('"')
        return ""

    # ------------------------------------------------------------------ 业务快捷方法
    def get_interface_information(self) -> Dict[str, Any]:
        return self.rest_one("system", "getInterfaceInformation") or {}

    def get_power_status(self) -> str:
        data = self.rest_one("system", "getPowerStatus") or {}
        return str(data.get("status", "unknown"))

    def set_power_status(self, on: bool) -> None:
        self.rest("system", "setPowerStatus", [{"status": bool(on)}])

    def get_volume_information(self) -> Dict[str, Any]:
        data = self.rest_one("audio", "getVolumeInformation")
        if isinstance(data, list) and data:
            return data[0]
        return data if isinstance(data, dict) else {}

    def set_audio_volume(self, volume: int) -> None:
        self.rest("audio", "setAudioVolume", [{"target": "speaker", "volume": str(int(volume))}])

    def set_audio_mute(self, mute: bool) -> None:
        self.rest("audio", "setAudioMute", [{"status": bool(mute)}])

    def get_application_list(self) -> List[Dict[str, Any]]:
        data = self.rest_one("appControl", "getApplicationList")
        return data if isinstance(data, list) else []

    def set_active_app(self, uri: str) -> None:
        self.rest("appControl", "setActiveApp", [{"uri": uri}])

    def get_external_inputs(self) -> List[Dict[str, Any]]:
        data = self.rest_one("avContent", "getCurrentExternalInputsStatus")
        return data if isinstance(data, list) else []

    def set_play_content(self, uri: str) -> None:
        self.rest("avContent", "setPlayContent", [{"uri": uri}])

    def get_remote_controller_info(self) -> List[Dict[str, str]]:
        result = self.rest("system", "getRemoteControllerInfo")
        if len(result) >= 2 and isinstance(result[1], list):
            return [
                {"name": str(k.get("name", "")), "value": str(k.get("value", ""))}
                for k in result[1]
                if k.get("name") and k.get("value")
            ]
        return []

    def ping_latency(self) -> float:
        """用只读接口测一次往返延迟（毫秒）。"""
        started = time.perf_counter()
        self.get_power_status()
        return (time.perf_counter() - started) * 1000.0


# ---------------------------------------------------------------------- WOL
def send_wol(mac: str, broadcast: str = "255.255.255.255", port: int = 9) -> None:
    """发送 Wake-on-LAN 魔术包（电视处于深度待机、HTTP 不可达时使用）。"""
    cleaned = re.sub(r"[^0-9A-Fa-f]", "", mac or "")
    if len(cleaned) != 12:
        raise TvError("网卡地址格式不正确，应为 AA:BB:CC:DD:EE:FF")
    payload = b"\xff" * 6 + bytes.fromhex(cleaned) * 16
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(payload, (broadcast, port))


def host_from_input(text: str) -> tuple[str, int]:
    """允许用户输入 192.168.1.10 或 http://192.168.1.10:80 两种形式。"""
    raw = (text or "").strip()
    if not raw:
        return "", 80
    if "://" not in raw:
        raw = "http://" + raw
    parsed = urlparse(raw)
    return parsed.hostname or "", parsed.port or 80
