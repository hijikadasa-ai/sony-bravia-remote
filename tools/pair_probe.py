"""诊断用：对着真机跑一遍 app.core.client 的注册流程，并打印原始响应。

用法：
    export SONY_TV_HOST=192.168.1.10
    python tools/pair_probe.py          # 只发不带凭据的请求，触发电视弹出 PIN
    python tools/pair_probe.py 2914     # 带 PIN 走 Basic 认证，打印结果并做一次真实校验
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, ".")

from app.core.client import TvClient  # noqa: E402
from app.core.errors import AuthRequired, TvError  # noqa: E402

HOST = os.environ.get("SONY_TV_HOST", "192.168.1.10")
PIN = sys.argv[1].strip() if len(sys.argv) > 1 and sys.argv[1].strip() not in ("-", "") else None

client = TvClient(host=HOST, client_id="SonyTvRemote:1", nickname="PC Remote", timeout=6.0)

print(f"PIN: {PIN or '(未提供，仅触发弹窗)'}")
try:
    cookie = client.act_register(PIN)
    print("SUCCESS  cookie =", cookie)
except AuthRequired as exc:
    print("401 需要 PIN:", exc, "| needs_pin =", exc.needs_pin)
    raise SystemExit(0)
except TvError as exc:
    print("失败:", exc, "| detail =", getattr(exc, "detail", ""))
    raise SystemExit(1)

if cookie:
    print("--- 校验：读取电源状态（只读，无需授权） ---")
    print("power =", client.get_power_status())
    print("--- 校验：把电源状态原样写回（需要授权） ---")
    try:
        status = client.get_power_status()
        client.set_power_status(status != "standby")
        print("控制接口已通过授权 ✓")
    except Exception as exc:  # noqa: BLE001
        print("控制接口仍被拒绝 ✗", type(exc).__name__, exc)
    print("--- 校验：发一个 Display 按键（IRCC） ---")
    try:
        client.send_ircc("AAAAAQAAAAEAAAA6Aw==")
        print("IRCC 已通过授权 ✓")
    except Exception as exc:  # noqa: BLE001
        print("IRCC 被拒绝 ✗", type(exc).__name__, exc)
    print("\n把以下值填进配置即可：\n  auth_cookie =", cookie)
