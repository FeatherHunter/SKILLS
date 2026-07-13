#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""训记训练数据 —— upsert(增/改原子封装)。

API:POST https://trains.xunjiapp.cn/api_upsert_trains_for_llm_v2

请求体:
    {
        "schema_version": "train_open_api_v2",
        "client_request_id": "<unique-id-from-agent>",
        "dry_run": false,
        "include_full_data": false,   # 可选,改 RPE/difficulty/note 时建议 true
        "res": [
            {
                "datestr": "2026-07-13",
                "localid": 0,        # 0=新建;有值=更新
                "title": "...",
                "start": 1744010000000,  # 调用方控制,本层透传
                "end": 1744013600000,
                "movements": [...]
            }
        ]
    }

行为约定(从第一性原理):
- 透传语义:`res` 内所有字段(movements / start / end / title / note 等)调用方传什么就推什么
- 唯一性兜底:`client_request_id` 缺省时自动 uuid4.hex(满足训记"unique-id-from-agent"硬约束)
- 不读本地 DB / 不做 plan 转换 / 不做对账 —— 这些是应用层职责

⚠ 响应 truncated 字段不可信(2026-07-13 实测踩过):
- upsert 响应里 `res.trains[].movements[]` 经常**只回最后一个 movement**(其他 movements 在响应里"消失")
- 同时 `truncated: false` —— 服务端自己说没截
- 跟训记官方语义不符,**这是训记 API 的响应缺陷**
- 验证训记数据是否真的写对:用 `xunji_bridge.py fetch --date X --full`(fetch 才是真实状态)
- 本层不修这个,仅记录;训记 API 升级后再观察

公开 API:
    upsert_trains(res_list, client_request_id=None, dry_run=False,
                  include_full_data=False, timeout=30) -> dict
        调训记 upsert API;失败返 dict 带 err 标记(走 errors.classify_error)
"""
from __future__ import annotations

import gzip
import json
import urllib.error
import urllib.request
import uuid
from typing import Optional

from . import auth

BASE_URL = "https://trains.xunjiapp.cn"
ENDPOINT = f"{BASE_URL}/api_upsert_trains_for_llm_v2"


def upsert_trains(
    res_list: list[dict],
    client_request_id: Optional[str] = None,
    dry_run: bool = False,
    include_full_data: bool = False,
    timeout: int = 30,
) -> dict:
    """调训记 upsert API(原子层,无业务)。

    Args:
        res_list: 训记 res[] 数组(完整数据结构由调用方构造)
        client_request_id: 幂等键。None 时自动 uuid4.hex(满足训记 unique 要求)
        dry_run: True 时只构造 payload 不发请求,返回 payload 摘要
        include_full_data: True 时训记返回完整标准化数据(改 RPE/difficulty/note 时建议)
        timeout: HTTP 超时(秒)

    Returns:
        成功:训记原始响应(透传)
        失败:{"err": True, "error_type": ..., "message": ..., ...}
    """
    # client_request_id 唯一性兜底
    if not client_request_id:
        client_request_id = uuid.uuid4().hex

    if dry_run:
        return {
            "dry_run": True,
            "client_request_id": client_request_id,
            "include_full_data": include_full_data,
            "res_count": len(res_list),
        }

    key = auth.require_key()
    payload = {
        "schema_version": "train_open_api_v2",
        "client_request_id": client_request_id,
        "dry_run": False,
        "include_full_data": bool(include_full_data),
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
                # 训记响应常带 Content-Encoding: gzip(0x1f 0x8b 开头),必须先解压
                if resp.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                result = json.loads(raw.decode("utf-8"))
                # 软错误检测:HTTP 200 但业务错(success:false / error 字段 / res 字符串限频)
                from .errors import classify_error
                err = classify_error(result)
                if err.get("error_type"):
                    # classify_error 判定为错误 → 转成 err dict
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
