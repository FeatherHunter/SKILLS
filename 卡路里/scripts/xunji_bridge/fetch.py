#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""训记训练数据 —— 读(fetch)。

API:POST https://trains.xunjiapp.cn/api_trains_for_llm_v2

请求体:
    {
        "schema_version": "train_open_api_v2",
        "datestr": "2026-07-01",
        "include_full_data": false  # true 时返回未完成组/RPE/备注等
    }

限频:
    include_full_data=false → 15s/次
    include_full_data=true  → 30s/次
    too frequent → API 报错,需等待 retry_after 再试

⚠ fetch 是训记数据的**真实状态源**(2026-07-13 实测确认):
- upsert 响应的 truncated 字段不可信(经常只回最后一个 movement,truncated 仍为 false)
- 训记 upsert 后要看真实数据,**用 fetch --full** 而不是信 upsert 响应
- 应用层脚本(overlay-plan 等)依赖 fetch 拿 localid + 验证写入正确性

公开 API:
    fetch_trains(datestr, full_data=False, timeout=30) -> dict
        调 API 返回完整 JSON;失败返回 {"err": True, ...}

    parse_trains(resp) -> list[dict]
        提取 res.trains[] 中关键字段为可读 dict 列表
        (供人查看;回写 exercise_log 用 xunji_adapter,不要用这个)
"""
from __future__ import annotations

import gzip
import json
from typing import Any

import urllib.error
import urllib.request

from . import auth

BASE_URL = "https://trains.xunjiapp.cn"
ENDPOINT = f"{BASE_URL}/api_trains_for_llm_v2"


def fetch_trains(datestr: str, full_data: bool = False, timeout: int = 30, respect_rate_limit: bool = False) -> dict:
    """调训记查训练 API。失败返回 dict 带 err 标记,不抛异常。

    Args:
        datestr: YYYY-MM-DD
        full_data: 是否 include_full_data=True
        timeout: HTTP 超时(秒)
        respect_rate_limit: True 时,30s 内二次 full_data 调用自动 sleep
                          (跨进程也有效,状态写到 ~/.mavis/xunji_bridge_rate.json)
    """
    if respect_rate_limit:
        threshold = auth.RATE_LIMIT_FULL_SECONDS if full_data else auth.RATE_LIMIT_LIGHT_SECONDS
        since = auth.seconds_since_last_call(full=full_data)
        if since is not None and since < threshold:
            import time as _time
            wait = threshold - since
            print(f"  [WAIT] 限频:距上次 {full_data and 'full' or 'light'} 调用 {since:.1f}s,睡 {wait:.1f}s",
                  file=__import__('sys').stderr, flush=True)
            _time.sleep(wait)
    key = auth.require_key()  # 无 KEY 直接抛

    payload = {
        "schema_version": "train_open_api_v2",
        "datestr": datestr,
        "include_full_data": bool(full_data),
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
        """实际 HTTP 调用(给 retry_with_backoff 包装)。"""
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                if resp.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                result = json.loads(raw.decode("utf-8"))
                if respect_rate_limit:
                    auth.update_last_call(full=full_data)
                # 软错误检测:HTTP 200 但业务错(success:false / error 字段 / res 字符串限频)
                # 全部交给 classify_error 统一归类
                from .errors import classify_error
                err = classify_error(result)
                if err.get("error_type"):
                    if "raw_body" not in err:
                        err["raw_body"] = result
                    return {"err": True, **err}
                return result
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


def parse_trains(resp: dict) -> list[dict]:
    """把训记 API 响应整理成可读 list(每条 session 一个 dict)。

    回写 exercise_log 不要用这个函数,用 xunji_adapter.xunji_response_to_rows。
    """
    out = []
    for train in (resp.get("res", {}) or {}).get("trains", []) or []:
        movements = []
        for m in train.get("movements", []) or []:
            sets_info = []
            for s in m.get("sets", []) or []:
                sets_info.append({
                    "index": s.get("index"),
                    "done": s.get("done"),
                    "weight": s.get("weight"),
                    "unit": s.get("unit"),
                    "reps": s.get("reps"),
                })
            movements.append({
                "name": m.get("name"),
                "sets": sets_info,
            })
        out.append({
            "localid": train.get("localid"),
            "title": train.get("title"),
            "datestr": train.get("datestr"),
            "difficulty": train.get("difficulty"),
            "movements": movements,
        })
    return out
