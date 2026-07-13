#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""训记训练数据 —— overlay(用卡路里 plan 覆盖训记已有训练)。

应用层职责:
- 拉卡路里 DB plan(session 数据)
- 拉训记 list(只拿 title → localid 映射,**不取 start/end**)
- 按 title 对账
- 构造 res[]:localid 已有 + start=0, end=0
- 调底层 `upsert.upsert_trains` 一次(训记 API 单次最多 4 条)

**start/end 永远传 0**(等同 push-plan 新建语义):
- "覆盖 = 新建" —— localid 决定新建/更新,start/end 不参与
- 不从 fetch 拿训记原 start/end(应用层不该替训记猜时间)
- 训记那边的"开始/结束时间"显示会变 0(等同"未开始"),用户接受

公开 API:
    overlay_day_plan(date_str, dry_run=False, missing="fail") -> dict
        覆盖某天的训练
        missing: "fail"(默认,缺 title 报错退出) / "skip"(缺 title 跳过,继续推有的)

返回 dict 结构:
    {
        "date": str,
        "session_count": int,             # 卡路里当天 session 数
        "trains_count": int,              # 训记当天已有训练数
        "matched": [                      # 成功匹配的
            {"session_label": str, "localid": int, "ok": bool, "client_request_id": str, "resp": dict}
        ],
        "missing_in_xunji": [str],        # 卡路里有但训记没,按 missing 策略处理
        "extra_in_xunji": [str],          # 训记有但卡路里没(不删,只是报告)
        "ok_count": int,
        "fail_count": int,
    }
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path
from typing import Literal

# 路径 hack:从 xunji_bridge/ 调到上层的 workout_plan
_BRIDGE_DIR = Path(__file__).parent
_SCRIPTS_DIR = _BRIDGE_DIR.parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


def overlay_day_plan(
    date_str: str,
    dry_run: bool = False,
    missing: Literal["fail", "skip"] = "fail",
) -> dict:
    """用卡路里 plan 覆盖训记某天的训练。

    Args:
        date_str: YYYY-MM-DD
        dry_run: 只构造 payload 不发请求
        missing: 卡路里有但训记没的 title 处理策略
                 - "fail"(默认):报错退出,不写脏数据
                 - "skip":跳过这些 session,只推有 localid 的
    """
    # 1. 拉训记 list(只拿 localid)
    from xunji_bridge import fetch
    trains_raw = fetch.fetch_trains(date_str, full_data=True, respect_rate_limit=False)
    if trains_raw.get("err"):
        return {
            "date": date_str,
            "session_count": 0,
            "trains_count": 0,
            "matched": [],
            "missing_in_xunji": [],
            "extra_in_xunji": [],
            "ok_count": 0,
            "fail_count": 1,
            "err": trains_raw.get("err", "fetch failed"),
        }
    raw_trains = (trains_raw.get("res", {}) or {}).get("trains", []) or []
    title_to_localid = {t["title"]: t["localid"] for t in raw_trains}

    # 2. 拉卡路里 plan
    from datetime import date as _date
    from workout_plan import get_day_plan
    target_date = _date.fromisoformat(date_str)
    day = get_day_plan(target_date)
    sessions = day.get("sessions", [])

    if not sessions:
        return {
            "date": date_str,
            "session_count": 0,
            "trains_count": len(raw_trains),
            "matched": [],
            "missing_in_xunji": [],
            "extra_in_xunji": list(title_to_localid.keys()),
            "ok_count": 0,
            "fail_count": 0,
            "note": "卡路里当天无 session(可能休息日或计划未配置)",
        }

    # 3. 对账
    from xunji_bridge.push import _session_to_res
    res_list = []
    matched = []
    missing_in_xunji = []

    for s in sessions:
        label = s.get("session_label", "")
        localid = title_to_localid.get(label)

        if localid is None:
            missing_in_xunji.append(label)
            continue

        # 构造 res[]:localid 已有, start/end = 0(覆盖=新建语义)
        res_item = _session_to_res(date_str, s)
        res_item["localid"] = localid
        res_item["start"] = 0
        res_item["end"] = 0
        res_list.append(res_item)

    if missing_in_xunji:
        if missing == "fail":
            return {
                "date": date_str,
                "session_count": len(sessions),
                "trains_count": len(raw_trains),
                "matched": [],
                "missing_in_xunji": missing_in_xunji,
                "extra_in_xunji": [
                    t for t in title_to_localid.keys()
                    if t not in {s.get("session_label", "") for s in sessions}
                ],
                "ok_count": 0,
                "fail_count": 0,
                "err": f"卡路里有但训记没:{missing_in_xunji}(missing=fail 报错退出)",
            }
        # missing == "skip":只推匹配的
        print(
            f"  ⚠ 跳过(训记无 localid):{missing_in_xunji}",
            file=sys.stderr, flush=True,
        )

    if not res_list:
        return {
            "date": date_str,
            "session_count": len(sessions),
            "trains_count": len(raw_trains),
            "matched": [],
            "missing_in_xunji": missing_in_xunji,
            "extra_in_xunji": [
                t for t in title_to_localid.keys()
                if t not in {s.get("session_label", "") for s in sessions}
            ],
            "ok_count": 0,
            "fail_count": 0,
            "note": "无可推送的 session(全部 missing 或空)",
        }

    # 4. 调底层 upsert(单次调用,训记 API 单次最多 4 条)
    from xunji_bridge import upsert
    # client_request_id 一次性,所有 session 共用(底层用 res 数组 1 次调用)
    client_request_id = f"overlay_{date_str}_{uuid.uuid4().hex[:8]}"
    print(
        f"  → 调 upsert:res_count={len(res_list)}, "
        f"client_request_id={client_request_id}",
        file=sys.stderr, flush=True,
    )
    resp = upsert.upsert_trains(
        res_list,
        client_request_id=client_request_id,
        dry_run=dry_run,
    )

    is_ok = not resp.get("err")
    matched_entry = {
        "session_labels": [s.get("session_label", "") for s in sessions if s.get("session_label", "") in title_to_localid],
        "client_request_id": client_request_id,
        "ok": is_ok,
        "resp": resp,
    }

    return {
        "date": date_str,
        "session_count": len(sessions),
        "trains_count": len(raw_trains),
        "matched": [matched_entry],
        "missing_in_xunji": missing_in_xunji,
        "extra_in_xunji": [
            t for t in title_to_localid.keys()
            if t not in {s.get("session_label", "") for s in sessions}
        ],
        "ok_count": 1 if is_ok else 0,
        "fail_count": 0 if is_ok else 1,
    }
