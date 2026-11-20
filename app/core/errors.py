"""类型化错误：UI 只看到可读文案，绝不暴露堆栈。"""
from __future__ import annotations


class TvError(Exception):
    """所有电视交互错误的基类。"""

    kind = "error"

    def __init__(self, message: str, *, detail: str = "", code: int | None = None):
        super().__init__(message)
        self.message = message
        self.detail = detail
        self.code = code

    def __str__(self) -> str:
        return self.message


class NetworkError(TvError):
    """电视不可达 / 超时 / 网络中断。"""

    kind = "network"


class AuthRequired(TvError):
    """需要设备注册（PIN 配对）或预共享密钥。"""

    kind = "auth"

    def __init__(self, message: str = "需要在电视上完成注册授权", *, needs_pin: bool = False, detail: str = ""):
        super().__init__(message, detail=detail, code=401)
        self.needs_pin = needs_pin


class TvResponseError(TvError):
    """电视返回了业务错误码。"""

    kind = "tv"


class ConfigError(TvError):
    kind = "config"
