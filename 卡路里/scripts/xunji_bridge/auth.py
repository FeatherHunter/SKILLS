#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""训记鉴权与 KEY 管理。

环境变量约定(本技能唯一权威名):
    XUNJI_TRAINS_KEY    训记 API KEY(优先读这个)
    XUNJI_API_KEY       兼容旧名(无 XUNJI_TRAINS_KEY 时 fallback 读这个)

两者都不是训记官方规定,是项目内约定。训记官方只说:
- KEY 在训记 App "我的 → 设置 → 第三方接入" 生成
- 用 `Authorization: Bearer <KEY>` 传递

新建 / 永久化 KEY(Windows PowerShell,用户级):
    [Environment]::SetEnvironmentVariable('XUNJI_TRAINS_KEY', '<你的KEY>', 'User')

公开 API:
    get_key() -> Optional[str]      # 读有效 KEY(优先新名,空时 fallback 旧名)
    which() -> Optional[str]        # 返回当前用的是哪个名(用于提示)
    set_key(value, legacy=False)    # 写入(Windows 走 winreg,失败 fallback 提示 PowerShell)
    clear_key(legacy=False)         # 删除
    status() -> dict                # 状态报告
    require_key() -> str            # 硬要求有 KEY(没配抛错)
"""
from __future__ import annotations

import json
import os
import platform
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# 唯一权威名(本技能内)
PRIMARY_NAME = "XUNJI_TRAINS_KEY"
# 兼容旧名(无 PRIMARY 时 fallback 读这个;key set 时除非 --legacy 否则不写)
LEGACY_NAME = "XUNJI_API_KEY"

# 限频状态文件(供 fetch.py --respect-rate-limit 用,跨进程共享)
RATE_LIMIT_STATE_PATH = Path.home() / ".mavis" / "xunji_bridge_rate.json"

# 限频阈值(秒,来自 xunji-trains SKILL.md)
RATE_LIMIT_FULL_SECONDS = 30  # include_full_data=True
RATE_LIMIT_LIGHT_SECONDS = 15  # include_full_data=False(默认)


def get_key() -> Optional[str]:
    """返回有效 KEY(优先 PRIMARY,空时 fallback LEGACY)。两边都没配返回 None。"""
    primary = os.environ.get(PRIMARY_NAME, "").strip()
    if primary:
        return primary
    legacy = os.environ.get(LEGACY_NAME, "").strip()
    if legacy:
        return legacy
    return None


def which() -> Optional[str]:
    """返回当前有效 KEY 是从哪个环境变量名读到的(用于错误提示)。"""
    primary = os.environ.get(PRIMARY_NAME, "").strip()
    if primary:
        return PRIMARY_NAME
    legacy = os.environ.get(LEGACY_NAME, "").strip()
    if legacy:
        return LEGACY_NAME
    return None


# ── KEY 写入:Windows 走 winreg,非 Windows 走 PowerShell 提示 ──

def _set_key_windows(value: str, name: str) -> str:
    """Windows:用 winreg 写 HKEY_CURRENT_USER\\Environment(安全,无注入风险)。"""
    try:
        import winreg
    except ImportError:
        raise RuntimeError("winreg 不可用(非 Windows?)")

    try:
        with winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER) as reg:
            with winreg.OpenKey(reg, r"Environment", 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
        # 广播 WM_SETTINGCHANGE 让其他进程感知(可选,PowerShell SetEnvironmentVariable 也会做)
        try:
            import ctypes
            ctypes.windll.user32.SendMessageW(0xFFFF, 0x001A, 0, "Environment")
        except Exception:
            pass
        return name
    except OSError as e:
        raise RuntimeError(f"winreg 写入失败:{e}")


def _set_key_powershell(value: str, name: str) -> str:
    """非 Windows:用 PowerShell 写用户级环境变量(回退方案)。"""
    import subprocess
    # 用 base64 编码避免注入(KEY 含单引号也安全)
    import base64
    b64 = base64.b64encode(value.encode("utf-8")).decode("ascii")
    ps_cmd = (
        f"$v = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{b64}')); "
        f"[Environment]::SetEnvironmentVariable('{name}', $v, 'User')"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_cmd],
        check=True,
    )
    return name


def set_key(value: str, legacy: bool = False) -> str:
    """把 KEY 写入用户级环境变量(持久化)。

    Args:
        value:  KEY 字符串(非空)
        legacy: True 写 LEGACY_NAME;False 写 PRIMARY_NAME

    Returns:
        实际写入的环境变量名
    """
    value = (value or "").strip()
    if not value:
        raise ValueError("KEY 不能为空")
    if len(value) > 1024:
        raise ValueError("KEY 过长(> 1024 字符),疑似输入错误")
    name = LEGACY_NAME if legacy else PRIMARY_NAME

    if platform.system() == "Windows":
        _set_key_windows(value, name)
    else:
        _set_key_powershell(value, name)

    # 同步当前进程(让 set 完立即可调 fetch 等)
    os.environ[name] = value
    return name


def clear_key(legacy: bool = False) -> Optional[str]:
    """删除用户级环境变量(返回删除的名,没设则返回 None)。"""
    name = LEGACY_NAME if legacy else PRIMARY_NAME

    if platform.system() == "Windows":
        try:
            import winreg
            with winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER) as reg:
                with winreg.OpenKey(reg, r"Environment", 0, winreg.KEY_SET_VALUE) as key:
                    try:
                        winreg.DeleteValue(key, name)
                    except FileNotFoundError:
                        return None  # 本来就没设
            try:
                import ctypes
                ctypes.windll.user32.SendMessageW(0xFFFF, 0x001A, 0, "Environment")
            except Exception:
                pass
        except ImportError:
            pass
    else:
        import subprocess
        ps_cmd = f"[Environment]::SetEnvironmentVariable('{name}', $null, 'User')"
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], check=True)

    os.environ.pop(name, None)
    return name


def status() -> dict:
    """返回 KEY 状态报告(dict,适合 JSON 输出)。"""
    primary = os.environ.get(PRIMARY_NAME, "")
    legacy = os.environ.get(LEGACY_NAME, "")
    active = get_key()
    return {
        "primary_name": PRIMARY_NAME,
        "legacy_name": LEGACY_NAME,
        "primary_set": bool(primary),
        "legacy_set": bool(legacy),
        "active_source": which(),  # None / PRIMARY_NAME / LEGACY_NAME
        "active_key_preview": (active[:4] + "..." + active[-2:]) if active else None,
        "recommendation": (
            "OK" if primary
            else "建议把 XUNJI_API_KEY 迁移到 XUNJI_TRAINS_KEY(用 key set)"
            if legacy
            else "未配置,需用 key set <KEY> 设置"
        ),
    }


def require_key() -> str:
    """硬要求有 KEY(没配抛错)。被 fetch/push/backfill 调用。"""
    key = get_key()
    if not key:
        raise RuntimeError(
            f"未配置训记 KEY。运行 `python scripts/xunji_bridge.py key set <KEY>` 设置。\n"
            f"权威名:{PRIMARY_NAME}\n"
            f"兼容名:{LEGACY_NAME}\n"
            f"KEY 申请:训记 App → 我的 → 设置 → 第三方接入"
        )
    return key


# ── 限频状态读写(供 fetch.py --respect-rate-limit 用) ──

def read_rate_limit_state() -> dict:
    """读取限频状态(返回 {last_full_call_iso, last_light_call_iso})。

    文件不存在时返回空 dict(代表"无历史调用")。
    """
    if not RATE_LIMIT_STATE_PATH.exists():
        return {}
    try:
        with open(RATE_LIMIT_STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def write_rate_limit_state(state: dict) -> None:
    """写入限频状态(原子写:先写 .tmp 再 rename)。"""
    RATE_LIMIT_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = RATE_LIMIT_STATE_PATH.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    tmp.replace(RATE_LIMIT_STATE_PATH)


def update_last_call(full: bool) -> None:
    """更新最后一次调用时间戳(供下次限频检查)。"""
    state = read_rate_limit_state()
    now_iso = datetime.now().isoformat(timespec="seconds")
    key = "last_full_call_iso" if full else "last_light_call_iso"
    state[key] = now_iso
    write_rate_limit_state(state)


def seconds_since_last_call(full: bool) -> Optional[float]:
    """返回距上次同类调用的秒数(无历史返 None)。"""
    state = read_rate_limit_state()
    key = "last_full_call_iso" if full else "last_light_call_iso"
    iso = state.get(key)
    if not iso:
        return None
    try:
        last = datetime.fromisoformat(iso)
        return (datetime.now() - last).total_seconds()
    except ValueError:
        return None


if __name__ == "__main__":
    # 单独跑 auth.py 打印状态
    print(json.dumps(status(), ensure_ascii=False, indent=2))
