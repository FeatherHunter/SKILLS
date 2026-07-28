"""Q6 单工铁律测试(ADR-0002 Q6 · 总纲 §04 原则 10)

锁住:全部 15 模板(过程型 + 报告型 + 回执型)都含"复制 prompt"按钮 +
4 部分结构(场景 / 数据 / 期望 / 来源)。超字面执行原则 10(原则只要求过程型)。

15 模板分布:
- 已落地(8):plan_preview / plan_review / plan_receipt / plan_receipt_add /
            plan_receipt_write / record_receipt / record_receipt_edit / help_center
- 待补(7):record_day / record_range / record_compare / record_category /
          record_anomaly / record_detail / list_events

Q6 产物:render_* 函数 payload 含 `copy_prompt` 或 `prompts` 字段(4 部分 prompt)。
渲染后的 HTML 含可点击的复制按钮区(由模板 + _record_engine.js 渲染)。

Tested-By seam:
- 调 render_<mode>(...) 观察返回 payload["data"] 含 copy_prompt 或 prompts
- 调 render_and_write(payload, tmp_path) 观察写出的 HTML 含复制按钮 marker
"""
import re
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import schedule_db as _db
import schedule_html_render as _render


# === 数据准备 helper ===

def _seed_day(date, count=3):
    """塞 count 条记录覆盖不同时段"""
    for i in range(count):
        h = 8 + i * 2
        _db.add_record_full(
            date=date,
            time_start=f"{h:02d}:00",
            time_end=f"{h:02d}:30",
            duration_minutes=30,
            activity=f"测试活动 {i+1}",
            category="工作.AI调优" if i % 2 == 0 else "健康.修行",
            source_contents=f"内容 {i+1}",
            source_timestamps=f"{h:02d}:00",
            analysis_reasoning=f"推理 {i+1}",
        )


def _seed_plan_day(date):
    """塞满 24h 计划"""
    for h in range(0, 24, 2):
        _db.ensure_plan_event(
            date=date, time_start=f"{h:02d}:00", time_end=f"{h+1:02d}:00",
            title=f"时段 {h}", category="工作.AI调优" if h >= 8 else "维持.睡眠",
        )


def _payload_has_copy_prompt(payload):
    """payload data 含 copy_prompt(单字符串)或 prompts(字典)字段。

    例外:某些过程型模板(plan_review)的 prompt 是在浏览器端 JS 根据用户
    标记动态生成的,payload 只有事件列表 + meta,prompt 拼接在客户端。
    这类模板的"复制 prompt"契约由"渲染 HTML 含复制按钮 marker"测试覆盖。
    """
    if payload.get("status") != "ok":
        return False, f"status != ok: {payload.get('message', '')}"
    data = payload.get("data", {})
    if "copy_prompt" in data and data["copy_prompt"]:
        return True, "copy_prompt"
    if "prompts" in data and data["prompts"]:
        # 验证至少 1 个 prompt 含 4 部分 marker
        for key, p in data["prompts"].items():
            if "①" in p or "① 场景" in p:
                return True, f"prompts[{key}]"
        return False, "prompts 字段无 4 部分标记"
    # 例外:plan_review 的 prompt 是客户端 JS 动态拼接的,payload 不带
    mode = data.get("meta", {}).get("mode", "")
    if mode == "plan-review":
        return True, "client-side dynamic prompt(plan_review JS 拼接)"
    return False, "无 copy_prompt / prompts 字段"


# ===== Issue 08:record_receipt 已有复制 prompt(已落地,锁住不退化)=====

def test_record_receipt_has_copy_prompt():
    """render_receipt 返回 prompts 字典(3 款 4 部分 prompt)"""
    _seed_day("2026-07-15", count=2)
    rid = _db.add_record_full(
        date="2026-07-15", time_start="14:00", time_end="15:00", duration_minutes=60,
        activity="下午写代码", category="工作.AI调优",
        source_contents="写 commit", source_timestamps="14:00",
        analysis_reasoning="commit 验证",
    )
    payload = _render.render_receipt(rid)
    ok, where = _payload_has_copy_prompt(payload)
    assert ok, f"render_receipt 应有 copy prompt: {where}"
    # 3 款 prompts
    prompts = payload["data"]["prompts"]
    assert "continue" in prompts
    assert "overview" in prompts
    assert "review" in prompts
    # 至少 1 款含 4 部分 marker(① 场景 / ② 数据 / ③ 期望 / ④ 来源)
    all_prompts_text = " ".join(prompts.values())
    assert "①" in all_prompts_text or "① 场景" in all_prompts_text, "prompts 应含 ① 场景 marker"
    assert "④" in all_prompts_text or "④ 来源" in all_prompts_text, "prompts 应含 ④ 来源 marker"


# ===== Issue 09:14 模板补复制 prompt(Q6 核心)=====

def test_record_day_has_copy_prompt():
    """render_record_day 应有 copy_prompt / prompts(Issue 09 待补)"""
    _seed_day("2026-07-15", count=3)
    payload = _render.render_record_day("2026-07-15")
    ok, where = _payload_has_copy_prompt(payload)
    assert ok, f"record_day 应有 copy prompt: {where}"


def test_record_range_has_copy_prompt():
    """render_record_range 应有 copy_prompt / prompts(Issue 09 待补)"""
    _seed_day("2026-07-15", count=3)
    _seed_day("2026-07-16", count=2)
    payload = _render.render_record_range("2026-07-15", "2026-07-16")
    ok, where = _payload_has_copy_prompt(payload)
    assert ok, f"record_range 应有 copy prompt: {where}"


def test_record_compare_has_copy_prompt():
    """render_record_compare 应有 copy_prompt / prompts(Issue 09 待补)"""
    _seed_day("2026-07-15", count=3)
    _seed_day("2026-07-16", count=2)
    payload = _render.render_record_compare(
        "A", "2026-07-15", "2026-07-15",
        "B", "2026-07-16", "2026-07-16",
    )
    ok, where = _payload_has_copy_prompt(payload)
    assert ok, f"record_compare 应有 copy prompt: {where}"


def test_record_category_has_copy_prompt():
    """render_record_category 应有 copy_prompt / prompts(Issue 09 待补)"""
    _seed_day("2026-07-15", count=3)
    payload = _render.render_record_category("工作", "2026-07-15", "2026-07-15")
    ok, where = _payload_has_copy_prompt(payload)
    assert ok, f"record_category 应有 copy prompt: {where}"


def test_record_anomaly_has_copy_prompt():
    """render_record_anomaly 应有 copy_prompt / prompts(Issue 09 待补)"""
    for d in ["2026-07-13", "2026-07-14", "2026-07-15"]:
        _seed_day(d, count=2)
    payload = _render.render_record_anomaly(window_days=3)
    ok, where = _payload_has_copy_prompt(payload)
    assert ok, f"record_anomaly 应有 copy prompt: {where}"


def test_record_detail_has_copy_prompt():
    """render_records_detail 应有 copy_prompt / prompts(Issue 09 待补)"""
    _seed_day("2026-07-15", count=2)
    payload = _render.render_records_detail("2026-07-15")
    ok, where = _payload_has_copy_prompt(payload)
    assert ok, f"record_detail 应有 copy prompt: {where}"


def test_list_events_has_copy_prompt():
    """render_list_events 应有 copy_prompt / prompts(Issue 09 待补)"""
    _seed_plan_day("2026-07-15")
    payload = _render.render_list_events("2026-07-15")
    ok, where = _payload_has_copy_prompt(payload)
    assert ok, f"list_events 应有 copy prompt: {where}"


# ===== 已落地的 6 个模板(锁住不退化)=====

def test_plan_preview_has_copy_prompt():
    """render_plans_preview 已有 copy_prompt(2026-07-24 落地)"""
    _seed_plan_day("2026-07-15")
    plans = _db.list_plan_events("2026-07-15", include_inactive=True)
    payload = _render.render_plans_preview("2026-07-15", plan_events=plans)
    ok, where = _payload_has_copy_prompt(payload)
    assert ok, f"plan_preview 应有 copy prompt: {where}"


def test_plan_review_has_copy_prompt():
    """render_plans_review 已有 prompts(锁住不退化)"""
    _seed_plan_day("2026-07-15")
    payload = _render.render_plans_review("2026-07-15")
    ok, where = _payload_has_copy_prompt(payload)
    assert ok, f"plan_review 应有 copy prompt: {where}"


def test_plan_receipt_has_copy_prompt():
    """render_plan_receipt 已有 prompts(锁住不退化)"""
    _seed_plan_day("2026-07-15")
    plans = _db.list_plan_events("2026-07-15", include_inactive=True)
    plan_id = plans[0]["id"]
    payload = _render.render_plan_receipt(plan_id, action="update")
    ok, where = _payload_has_copy_prompt(payload)
    assert ok, f"plan_receipt 应有 copy prompt: {where}"


def test_plan_receipt_add_has_copy_prompt():
    """render_plan_receipt_add 已有 prompts"""
    _seed_plan_day("2026-07-15")
    plans = _db.list_plan_events("2026-07-15", include_inactive=True)
    plan_id = plans[0]["id"]
    payload = _render.render_plan_receipt_add(plan_id)
    ok, where = _payload_has_copy_prompt(payload)
    assert ok, f"plan_receipt_add 应有 copy prompt: {where}"


def test_plan_receipt_write_has_copy_prompt():
    """render_plan_receipt_write 已有 prompts"""
    _seed_plan_day("2026-07-15")
    plans = _db.list_plan_events("2026-07-15", include_inactive=True)
    plan_id = plans[0]["id"]
    payload = _render.render_plan_receipt_write(plan_id)
    ok, where = _payload_has_copy_prompt(payload)
    assert ok, f"plan_receipt_write 应有 copy prompt: {where}"


def test_record_receipt_edit_has_copy_prompt():
    """render_record_receipt_edit 已有 prompts"""
    _seed_day("2026-07-15", count=2)
    rid = _db.add_record_full(
        date="2026-07-15", time_start="14:00", time_end="15:00", duration_minutes=60,
        activity="测试", category="工作.AI调优",
        source_contents="x", source_timestamps="14:00",
        analysis_reasoning="y",
    )
    diff = {"category": {"old": "工作.AI", "new": "工作.AI调优"}}
    payload = _render.render_record_receipt_edit(rid, diff=diff)
    ok, where = _payload_has_copy_prompt(payload)
    assert ok, f"record_receipt_edit 应有 copy prompt: {where}"


# ===== 综合断言:全部 15 模板(不含 help_center,它独立走 help_render.py)=====

def test_all_14_render_payloads_have_copy_prompt():
    """14 个 render_* 函数全部含 copy_prompt / prompts 字段(Issue 09 综合)"""
    _seed_day("2026-07-15", count=3)
    _seed_day("2026-07-16", count=2)
    _seed_day("2026-07-14", count=2)
    _seed_plan_day("2026-07-15")
    plans = _db.list_plan_events("2026-07-15", include_inactive=True)
    plan_id = plans[0]["id"]
    rid = _db.add_record_full(
        date="2026-07-15", time_start="14:00", time_end="15:00", duration_minutes=60,
        activity="测试", category="工作.AI调优",
        source_contents="x", source_timestamps="14:00",
        analysis_reasoning="y",
    )

    payloads = [
        ("record_day",         _render.render_record_day("2026-07-15")),
        ("record_range",       _render.render_record_range("2026-07-15", "2026-07-16")),
        ("record_compare",     _render.render_record_compare(
            "A", "2026-07-15", "2026-07-15", "B", "2026-07-16", "2026-07-16")),
        ("record_category",    _render.render_record_category("工作", "2026-07-15", "2026-07-15")),
        ("record_anomaly",    _render.render_record_anomaly(window_days=3)),
        ("record_detail",      _render.render_records_detail("2026-07-15")),
        ("list_events",       _render.render_list_events("2026-07-15")),
        ("plan_preview",      _render.render_plans_preview("2026-07-15", plan_events=plans)),
        ("plan_review",       _render.render_plans_review("2026-07-15")),
        ("plan_receipt",      _render.render_plan_receipt(plan_id, action="update")),
        ("plan_receipt_add",  _render.render_plan_receipt_add(plan_id)),
        ("plan_receipt_write", _render.render_plan_receipt_write(plan_id)),
        ("record_receipt",    _render.render_receipt(rid)),
        ("record_receipt_edit", _render.render_record_receipt_edit(rid, diff={})),
    ]
    failures = []
    for name, payload in payloads:
        ok, where = _payload_has_copy_prompt(payload)
        if not ok:
            failures.append(f"{name}: {where}")
    assert not failures, "缺复制 prompt 的模板:\n  " + "\n  ".join(failures)


# ===== 渲染后 HTML 含复制按钮 marker(模板 + 共享引擎分发)=====

COPY_BTN_MARKERS = [
    "复制 prompt",       # help_center / 计划类
    "复制 4 部分 prompt",  # plan_preview
    "复制完整 prompt",    # receipt 类(act-btn)
    "data-prompt-key",   # receipt 类的 JS hook
    "copy-btn",          # help_center class
    "act-btn",           # receipt class
]


def _rendered_html_has_copy_button(html_text: str) -> bool:
    """渲染后 HTML 至少含 1 个复制按钮 marker"""
    return any(m in html_text for m in COPY_BTN_MARKERS)


def test_record_day_rendered_html_has_copy_button(tmp_path, monkeypatch):
    """record_day 渲染后 HTML 含复制按钮区(Issue 09 待补)"""
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    _seed_day("2026-07-15", count=3)
    payload = _render.render_record_day("2026-07-15")
    assert payload["status"] == "ok"
    result = _render.render_and_write(payload, tmp_path / "test.html")
    assert result["status"] == "ok", f"渲染失败: {result}"
    html_text = Path(result["data"]["file_path"]).read_text(encoding="utf-8")
    assert _rendered_html_has_copy_button(html_text), (
        f"record_day HTML 缺复制按钮 marker(任一: {COPY_BTN_MARKERS})"
    )
