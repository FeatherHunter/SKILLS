#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""训记训练数据 —— 写(push / upsert)。

API:POST https://trains.xunjiapp.cn/api_upsert_trains_for_llm_v2

请求体:
    {
        "schema_version": "train_open_api_v2",
        "client_request_id": "<unique-id>",
        "dry_run": false,
        "res": [
            {
                "datestr": "2026-07-01",
                "localid": 0,                 # 新建时传 0;更新已有训练时传实际 localid
                "title": "胸部训练",
                "start": 0,                    # 按卡路里 SKILL.md 约定传 0(避免训记 BUG)
                "end": 0,
                "movements": [
                    {"name": "悍马机卧推", "sets": [
                        {"done": false, "weight": "42", "unit": "kg", "reps": "12"}
                    ]}
                ]
            }
        ]
    }

限频:45s/次。脚本内置 sleep,多 session 自动等。

公开 API:
    plan_session_to_xunji(date_str, week, dow, session_index) -> dict
        从卡路里 DB workout_plans 取某个 session,转成训记 res[] 的一项

    upsert_trains(res_list, client_request_id, dry_run=False, timeout=30) -> dict
        调 API;失败返回 {"err": True, ...}

    push_day_plan(date_str, dry_run=False) -> dict
        取一整天所有 session,逐个 upsert,自动 45s 限频
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

import urllib.error
import urllib.request

from . import auth

BASE_URL = "https://trains.xunjiapp.cn"
ENDPOINT = f"{BASE_URL}/api_upsert_trains_for_llm_v2"
RATE_LIMIT_SECONDS = 45  # 训记写 API 限频要求


def _safe_str(v, default: str = "0") -> str:
    """把任意值安全转 str(防 None / 非标量污染训记 API payload)。

    None / 缺失 → default
    int / float / str / bool → str(...)
    list / dict / 其他 → default(防止 JSON 序列化异常)
    """
    if v is None:
        return default
    if isinstance(v, (str, int, float, bool)):
        return str(v)
    return default


# 路径 hack:从 xunji_bridge/ 调到上层的 workout_plan
_BRIDGE_DIR = Path(__file__).parent
_SCRIPTS_DIR = _BRIDGE_DIR.parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


def plan_session_to_xunji(date_str: str, week: int, dow: int, session_index: int) -> dict:
    """从卡路里 DB 取某天某个 session,转成训记 res[] 项。

    Args:
        date_str:  YYYY-MM-DD(用于 client_request_id)
        week:      计划周次
        dow:       周几(1=Mon..7=Sun)
        session_index: session 序号

    Returns:
        dict: 训记 res[] 的一项

    Raises:
        LookupError: 找不到该 session
    """
    from workout_plan import get_day_plan

    # 复用 get_day_plan,但它只按日期取,需要再过滤 session_index
    target_date = __import__("datetime").date.fromisoformat(date_str)
    day = get_day_plan(target_date)
    for s in day.get("sessions", []):
        if s["session_index"] == session_index and s["week_number"] == week and s["day_of_week"] == dow:
            return _session_to_res(date_str, s)
    raise LookupError(
        f"找不到 session: date={date_str} week={week} dow={dow} session_index={session_index}"
    )


def _session_to_res(date_str: str, session: dict) -> dict:
    """workout_plans session → 训记 res[] 一项。

    转换规则(按卡路里 SKILL.md 训记步骤约定):
      1. 不跳过任何动作(含爬楼梯等有氧)
      2. 只保留 name + sets 两个字段
      3. 每条 set 加 "done": false
      4. start/end = 0(避免训记 BUG)
    """
    converted_movements = []
    for m in session.get("movements", []) or []:
        name = _safe_str(m.get("name", ""), default="")
        converted_sets = []
        for s in m.get("sets", []) or []:
            converted_sets.append({
                "done": False,
                "weight": _safe_str(s.get("weight", s.get("load", "0")), default="0"),
                "unit": _safe_str(s.get("unit", "kg"), default="kg"),
                "reps": _safe_str(s.get("reps", "0"), default="0"),
            })
        converted_movements.append({"name": name, "sets": converted_sets})

    return {
        "datestr": date_str,
        "localid": 0,  # 新建(已有训练时由调用方覆盖)
        "title": session.get("session_label", ""),
        "start": 0,
        "end": 0,
        "movements": converted_movements,
    }


def upsert_trains(
    res_list: list[dict],
    client_request_id: str,
    dry_run: bool = False,
    timeout: int = 30,
) -> dict:
    """调训记 upsert API。失败返回 dict 带 err 标记。"""
    if dry_run:
        return {"dry_run": True, "client_request_id": client_request_id, "res_count": len(res_list)}

    key = auth.require_key()
    payload = {
        "schema_version": "train_open_api_v2",
        "client_request_id": client_request_id,
        "dry_run": False,
        "res": res_list,
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        method="POST",
    )

    def _do_call() -> dict:
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                return json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as e:
            from .errors import classify_error
            err = classify_error(e)
            return {"err": True, **err}
        except Exception as e:
            from .errors import classify_error
            err = classify_error(e)
            return {"err": True, **err}

    from .errors import retry_with_backoff
    response, attempts = retry_with_backoff(_do_call, max_retries=2, sleep_base=5)
    if attempts > 1:
        response = {**response, "attempts": attempts}
    return response


def push_day_plan(date_str: str, dry_run: bool = False, sleep_seconds: int = RATE_LIMIT_SECONDS) -> dict:
    """推送一整天的所有 session 到训记,自动 45s 限频。

    Returns:
        {
            "date": date_str,
            "session_count": int,
            "results": [
                {"session_label": str, "client_request_id": str, "ok": bool, "resp": dict},
                ...
            ],
            "ok_count": int,
            "fail_count": int,
        }
    """
    from datetime import date as _date
    from workout_plan import get_day_plan

    target_date = _date.fromisoformat(date_str)
    day = get_day_plan(target_date)
    sessions = day.get("sessions", [])

    if not sessions:
        return {
            "date": date_str,
            "session_count": 0,
            "results": [],
            "ok_count": 0,
            "fail_count": 0,
            "note": "无 session(可能休息日或计划未配置)",
        }

    results = []
    ok = 0
    fail = 0

    for i, s in enumerate(sessions):
        session_label = s.get("session_label", "")
        client_request_id = f"{date_str}_{session_label}"  # 按卡路里 SKILL.md 约定

        # 非首个 session 需要等限频
        if i > 0 and not dry_run:
            print(f"  ⏳ 等待 {sleep_seconds}s 限频...", file=sys.stderr, flush=True)
            time.sleep(sleep_seconds)

        res_item = _session_to_res(date_str, s)
        resp = upsert_trains([res_item], client_request_id=client_request_id, dry_run=dry_run)

        is_ok = not resp.get("err")
        if is_ok:
            ok += 1
        else:
            fail += 1
        results.append({
            "session_label": session_label,
            "client_request_id": client_request_id,
            "ok": is_ok,
            "resp": resp,
        })

    return {
        "date": date_str,
        "session_count": len(sessions),
        "results": results,
        "ok_count": ok,
        "fail_count": fail,
    }
