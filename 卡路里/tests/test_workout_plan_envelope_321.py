# -*- coding: utf-8 -*-
"""test_workout_plan_envelope_321.py — #321 回归锁

背景: #314 Base 重构(commit 2262fee)后, workout_plan_view.html 主入口
把 window.__P__.data(数据对象, 无 status)预取进 DATA, 又按信封结构解构
{status, data, message} → status 恒 undefined → 守卫恒真 → 页面「⚠️ 数据错误」白屏。

本测试从两个面锁住修复:
1. 结构断言: 主入口必须从信封(window.__P__ / P.status)取 status, 禁止
   从 __P__.data 预取对象上解构 status(旧 bug 模式)。
2. 信封契约断言: 渲染器注入的 payload 必为完整信封(含 status), 与模板
   消费端契约一致。
"""
import re
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "workout_plan_view.html"


def _main_entry_js() -> str:
    text = TEMPLATE.read_text(encoding="utf-8")
    m = re.search(r'/\* ====== 主入口 ====== \*/.*?\(function\(\) \{', text, re.DOTALL)
    assert m, "模板缺主入口标记"
    start = m.end()
    end = text.find("renderHeader", start)
    assert end > start, "主入口区间定位失败"
    return text[start:end]


def test_envelope_status_not_from_data_prefetch():
    """旧 bug 模式禁止: 从 window.__P__.data 预取后解构 status"""
    js = _main_entry_js()
    assert re.search(r'const\s*\{\s*status,\s*data,\s*message\s*\}\s*=\s*DATA', js) is None, (
        "从 DATA(__P__.data 预取对象)解构 status → status 恒 undefined(回归 #321)"
    )
    assert "window.__P__.data" not in js, (
        "主入口仍存在 __P__.data 预取(__P__.data 无 status 字段, 与信封解构冲突)"
    )


def test_status_reads_from_envelope():
    """新契约: status 取自信封(P.status), 守卫前必须有信封/兜底判定"""
    js = _main_entry_js()
    assert "P.status" in js, "status 未从信封(window.__P__.status)取值"
    assert re.search(r"typeof P\.status === 'string'", js), "缺信封形态判定(status 为 string 时才是信封)"
    assert re.search(r"const status = isEnvelope \? P\.status : 'ok'", js), (
        "信封 status 取 P.status, 裸数据兜底为 ok"
    )


def test_envelope_judge_not_depend_on_data():
    """信封判据必须是 status 字段, 不得依赖 P.data 存在性

    边界: 错误信封 {status:'error', data:null} 若以 P.data 存在性判信封,
    会被误判为裸数据 → status 兜底 ok → 拿信封当数据渲染垃圾页面(对抗审查实测复现)。
    """
    js = _main_entry_js()
    m = re.search(r"const isEnvelope = ([^;]+);", js)
    assert m, "缺 isEnvelope 判定"
    judge = m.group(1)
    assert "P.status" in judge, f"信封判据不含 status: {judge}"
    assert "P.data" not in judge, (
        f"信封判据依赖 P.data 存在性(error+data=null 信封会被误判): {judge}"
    )


def test_injected_payload_is_envelope():
    """渲染器注入契约: <!--INJECT-DATA--> 处注入完整信封(渲染器侧)"""
    import sys
    from pathlib import Path as _P
    sys.path.insert(0, str(_P(__file__).resolve().parent.parent / "scripts"))
    import render_workout_plan as rwp  # noqa: E402

    tmpl = TEMPLATE.read_text(encoding="utf-8")
    payload = {"status": "ok", "data": {"config": {"title": "测试"}}, "message": "m"}
    html = rwp._render_html(payload["data"])
    assert html.count("<!--INJECT-DATA-->") == 0
    m = re.search(r'<script id="payload" type="application/json">(.*?)</script>', html, re.DOTALL)
    assert m, "注入后无 payload script"
    import json
    injected = json.loads(m.group(1).replace("<\\/", "</"))
    assert injected["status"] == "ok"
    assert isinstance(injected["data"], dict)
    assert injected["message"]
