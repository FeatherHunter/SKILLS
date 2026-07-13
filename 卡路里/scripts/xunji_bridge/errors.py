#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""训记 API 错误处理:分类 + 智能重试 + 字段化。

设计原则(2026-07-13 用户确认):
- 全部错误默认重试 2 次(防网络抖动)
- 但不同类型有不同处理策略(给 AI 路由看 error_type 走对应预案)
- 错误字段完整(error_type / message / retry_after / raw_body)
- 集中管理:不分散到各 fetch/push/backfill 模块

训记的两种错误模式(关键事实,所有调训记 API 的代码必须处理):
    1. 硬错误:HTTPError(HTTP 4xx/5xx,带 code + body)
       → classify_error(urllib.error.HTTPError) 走标准路径
    2. 软错误:HTTP 200 但业务错(连接成功但操作失败)
       → classify_error({"success": false, "error": "..."}) / 含 error 字段
       → 也覆盖老 fetch 的 "res": "too frequent..." 字符串限频
       → 走 _classify_by_code_and_body(200, body, body_raw) 跟硬错误同一套分类

所有调训记 API 的代码必须走 classify_error 处理响应,不要自己 if 字段判断
(否则会漏判软错误,导致误报"成功"—— 2026-07-13 实推踩过这个坑)。

公开 API:
    classify_error(err_input) -> dict
        把 HTTPError / API 错误响应 / 网络异常 → 结构化错误 dict

    retry_with_backoff(call_fn, max_retries=2, sleep_base=5) -> tuple[dict, int]
        包装一个 HTTP 调用,失败自动重试。
        返 (响应, 实际调用次数)

    ErrorType 常量(7 种)
"""
from __future__ import annotations

import json
import time
from typing import Any, Callable, Optional

# 错误类型常量
class ErrorType:
    AUTH = "auth"                # apikey missing/invalid(401/403)
    RATE_LIMIT = "rate_limit"    # too frequent(429,含 retry_after)
    VIP_REQUIRED = "vip_required"  # 仅VIP可用
    VALIDATION = "validation"    # 400 字段错
    SERVER = "server"            # 5xx
    NETWORK = "network"          # 超时/连接错
    UNKNOWN = "unknown"          # 其他


# 训记限频默认(秒)—— 写 45s,读 light 15s/full 30s
DEFAULT_RATE_LIMIT_SECONDS = 45


def classify_error(err_input: Any) -> dict:
    """把异常/响应 → 结构化错误 dict。

    支持的输入:
        - urllib.error.HTTPError 实例(有 .code / .read())
        - dict(API 错误响应,如 fetch.py 内部构造的 {"err": True, "code": ..., "body": ...})
        - Exception 实例(网络/超时/解析)
        - str(简单消息)

    Returns:
        {
            "error_type": str,         # ErrorType 常量之一
            "message": str,            # 人类可读
            "retry_after": Optional[int],  # 服务端要求等待秒数(适用 rate_limit)
            "raw_body": Any,           # 原始 body(调试)
            "code": Optional[int],     # HTTP code
        }
    """
    # 输入 1:HTTPError 实例
    import urllib.error
    if isinstance(err_input, urllib.error.HTTPError):
        body_raw = _safe_read(err_input)
        body = _try_parse_json(body_raw)
        code = err_input.code
        return _classify_by_code_and_body(code, body, body_raw)

    # 输入 2:dict(API 内部错误 / 软错误)
    if isinstance(err_input, dict):
        # 软错误检测:HTTP 200 但 success:false / 含 error 字段 / 老格式 res 字符串限频
        # 命中后走 _classify_by_code_and_body 走完正常错误分类流程
        if "err" not in err_input and (
            err_input.get("success") is False
            or "error" in err_input
            or (
                isinstance(err_input.get("res"), str)
                and "too frequent" in err_input["res"].lower()
            )
        ):
            body = err_input
            body_raw = json.dumps(body, ensure_ascii=False) if body is not None else ""
            return _classify_by_code_and_body(200, body, body_raw)  # code=200:HTTP 200 业务错

        if not err_input.get("err"):
            # 正常的 dict 不是错误
            return {"error_type": None, "message": "", "retry_after": None,
                    "raw_body": err_input, "code": None}

        code = err_input.get("code")
        body = err_input.get("body")
        body_raw = json.dumps(body, ensure_ascii=False) if body is not None else ""
        return _classify_by_code_and_body(code, body, body_raw)

    # 输入 3:Exception
    if isinstance(err_input, Exception):
        msg = str(err_input)
        # 已知异常类型
        if isinstance(err_input, (urllib.error.URLError, TimeoutError, ConnectionError)):
            return {"error_type": ErrorType.NETWORK, "message": f"网络错误:{msg}",
                    "retry_after": None, "raw_body": msg, "code": None}
        # JSON 解析
        if isinstance(err_input, json.JSONDecodeError):
            return {"error_type": ErrorType.VALIDATION, "message": f"响应 JSON 解析失败:{msg}",
                    "retry_after": None, "raw_body": msg, "code": None}
        return {"error_type": ErrorType.UNKNOWN, "message": f"未知错误:{msg}",
                "retry_after": None, "raw_body": str(err_input), "code": None}

    # 输入 4:str
    if isinstance(err_input, str):
        return {"error_type": ErrorType.UNKNOWN, "message": err_input,
                "retry_after": None, "raw_body": err_input, "code": None}

    return {"error_type": ErrorType.UNKNOWN, "message": "unknown",
            "retry_after": None, "raw_body": str(err_input), "code": None}


def _classify_by_code_and_body(code, body, body_raw) -> dict:
    """根据 HTTP code + 响应 body 分类。"""
    body_str = (body_raw or "").lower() if isinstance(body_raw, str) else ""
    if isinstance(body, dict):
        body_str += " " + json.dumps(body, ensure_ascii=False).lower()

    # VIP 专用
    if "仅vip" in body_str or "vip required" in body_str or "仅 vip" in body_str:
        return {"error_type": ErrorType.VIP_REQUIRED,
                "message": "训记仅 VIP 可用,需要会员权限",
                "retry_after": None,
                "raw_body": body_raw,
                "code": code}

    # 鉴权失败
    if code in (401, 403) or "apikey" in body_str and ("missing" in body_str or "invalid" in body_str):
        return {"error_type": ErrorType.AUTH,
                "message": "训记 API KEY 缺失或无效",
                "retry_after": None,
                "raw_body": body_raw,
                "code": code}

    # 限频
    if code == 429 or "too frequent" in body_str or "frequent" in body_str:
        retry_after = _parse_retry_after(body) or DEFAULT_RATE_LIMIT_SECONDS
        return {"error_type": ErrorType.RATE_LIMIT,
                "message": f"训记限频(需等 {retry_after}s)",
                "retry_after": retry_after,
                "raw_body": body_raw,
                "code": code}

    # 校验错
    if code == 400:
        return {"error_type": ErrorType.VALIDATION,
                "message": f"请求字段错(400):{_extract_msg(body)}",
                "retry_after": None,
                "raw_body": body_raw,
                "code": code}

    # 服务端错
    if code and 500 <= code < 600:
        return {"error_type": ErrorType.SERVER,
                "message": f"训记服务端错({code}):{_extract_msg(body)}",
                "retry_after": None,
                "raw_body": body_raw,
                "code": code}

    # 其他
    return {"error_type": ErrorType.UNKNOWN,
            "message": f"未分类错误(code={code}):{_extract_msg(body)}",
            "retry_after": None,
            "raw_body": body_raw,
            "code": code}


def _safe_read(http_err) -> str:
    """从 HTTPError 安全读 body。"""
    try:
        raw = http_err.read()
        if http_err.headers.get("Content-Encoding") == "gzip":
            import gzip
            raw = gzip.decompress(raw)
        return raw.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _try_parse_json(s: str):
    try:
        return json.loads(s)
    except Exception:
        return None


def _parse_retry_after(body) -> Optional[int]:
    """从 body 解析 retry_after(秒)。

    训记 API 不一定返标准 header。常见格式:
    - body.retry_after: 45
    - body.retryAfter: 45
    - body.message 含 "45s"
    - body.error 含 "retry after 45s"(2026-07-13 实推踩到,upsert 软错误格式)
    - body.res 是字符串(如 "too frequent, retry after 10s",老 fetch 限频格式)
    """
    if not isinstance(body, dict):
        return None
    val = body.get("retry_after") or body.get("retryAfter")
    if isinstance(val, (int, float)):
        return int(val)
    if isinstance(val, str) and val.isdigit():
        return int(val)
    # 尝试从 message / error / res(字符串)提取
    candidates = [
        body.get("message") or "",
        body.get("msg") or "",
        body.get("error") or "",
    ]
    res = body.get("res")
    if isinstance(res, str):
        candidates.append(res)
    msg = " ".join(candidates)
    import re
    m = re.search(r"(\d+)\s*s", str(msg))
    if m:
        return int(m.group(1))
    return None


def _extract_msg(body) -> str:
    if isinstance(body, dict):
        return str(body.get("message") or body.get("msg") or body.get("reason") or body)
    return str(body)[:200] if body else ""


def retry_with_backoff(
    call_fn: Callable[[], dict],
    max_retries: int = 2,
    sleep_base: float = 5.0,
) -> tuple[dict, int]:
    """包装 HTTP 调用,失败自动重试。

    Args:
        call_fn: 无参调用,返 dict(成功时 {"ok": True, "data": ...},失败时 {"err": True, ...})
        max_retries: 失败重试次数(默认 2)
        sleep_base: 限频/服务端错的基础 sleep 秒数(指数退避:base, 2*base, 4*base...)

    Returns:
        (响应_dict, 实际调用次数)
    """
    last_resp: dict = {}
    attempts = 0
    for i in range(max_retries + 1):
        attempts = i + 1
        try:
            resp = call_fn()
            last_resp = resp
            # 成功(无 err 字段)
            if not resp.get("err"):
                return resp, attempts
            # 错误 —— 决定是否重试
            err_type = resp.get("error_type", ErrorType.UNKNOWN)
            # auth/vip_required 不重试(无意义,马上告诉人)
            if err_type in (ErrorType.AUTH, ErrorType.VIP_REQUIRED):
                return resp, attempts
            # validation 不重试(字段错,重试也没用)
            if err_type == ErrorType.VALIDATION:
                return resp, attempts
            # 其他(rate_limit/server/network/unknown)重试
            if i < max_retries:
                retry_after = resp.get("retry_after")
                if retry_after:
                    wait = retry_after
                else:
                    wait = sleep_base * (2 ** i)  # 5, 10, 20
                time.sleep(wait)
        except Exception as e:
            # call_fn 自己抛异常(网络/JSON 等)
            err = classify_error(e)
            err["attempts"] = i + 1
            last_resp = {"err": True, **err}
            err_type = err.get("error_type", ErrorType.UNKNOWN)
            if err_type in (ErrorType.AUTH, ErrorType.VIP_REQUIRED, ErrorType.VALIDATION):
                return last_resp, attempts
            if i < max_retries:
                wait = sleep_base * (2 ** i)
                time.sleep(wait)

    return last_resp, attempts


if __name__ == "__main__":
    # 自检:几个典型错误分类
    print(json.dumps(classify_error({"err": True, "code": 429, "body": {"message": "too frequent"}}), ensure_ascii=False, indent=2))
    print("---")
    print(json.dumps(classify_error({"err": True, "code": 401, "body": {}}), ensure_ascii=False, indent=2))
    print("---")
    print(json.dumps(classify_error({"err": True, "code": 500, "body": {"message": "internal"}}), ensure_ascii=False, indent=2))
