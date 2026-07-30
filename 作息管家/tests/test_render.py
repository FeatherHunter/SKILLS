"""HTML 渲染函数测试(锁住 DRY 行为,2026-07-24)

为 11 个 render 函数提供基本 smoke test,验证:
- status=ok
- payload 关键字段存在
- 4 卡摘要 stats 派生正确
- 3 款 plan_receipt 函数行为一致(stats / plan_json / base_prompt)

回归保护:
- 改 helper 后立即测试(0.1s)
- 改 render 函数后回归(0.1s)

注意:schedule_db 函数不接 conn 参数,靠 conftest.py monkeypatch 路由
schedule_db.get_connection → in-memory conn(每次新 conn + 重建 schema)。
"""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import schedule_db as _db


# ---- helpers ----
def insert_test_records(date, count=3):
    """插入 count 条测试记录覆盖不同时段"""
    records = []
    for i in range(count):
        h = 8 + i * 2
        rid = _db.add_record_full(
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
        records.append(rid)
    return records


def insert_test_plan(date, time_start, time_end, title, category):
    """插入一条 24h 内分段测试用计划"""
    return _db.ensure_plan_event(
        date=date, time_start=time_start, time_end=time_end,
        title=title, category=category,
    )


# ---- 记录域 render 测试 ----
def test_render_record_day():
    """render_record_day 必含 5 字段:meta/summary_items/timeline/sleep_data/health/ai_questions"""
    insert_test_records("2026-07-15", count=3)
    from schedule_html_render import render_record_day
    result = render_record_day("2026-07-15")
    assert result["status"] == "ok"
    d = result["data"]
    assert d["meta"]["mode"] == "record-day"
    assert d["meta"]["date"] == "2026-07-15"
    assert "summary_items" in d
    assert "timeline" in d
    assert "sleep_data" in d
    assert "health" in d
    assert "ai_questions" in d


def test_render_records_detail():
    """render_records_detail 默认空 records → selected_record=None,records=[]"""
    from schedule_html_render import render_records_detail
    result = render_records_detail("2026-07-15")
    assert result["status"] == "ok"
    assert result["data"]["selected_record"] is None
    assert result["data"]["records"] == []


def test_render_receipt_default_state():
    """render_receipt 单条 CRUD 后漂亮回执(回执型首款)"""
    insert_test_records("2026-07-15", count=2)
    rid = _db.add_record_full(
        date="2026-07-15", time_start="14:00", time_end="15:00", duration_minutes=60,
        activity="下午写代码", category="工作.AI调优",
        source_contents="写 commit", source_timestamps="14:00",
        analysis_reasoning="commit 验证",
    )
    from schedule_html_render import render_receipt
    result = render_receipt(rid)
    assert result["status"] == "ok"
    assert result["data"]["record"]["id"] == rid
    assert result["data"]["record"]["activity"] == "下午写代码"
    assert result["data"]["record"]["category"] == "工作.AI调优"
    assert "today_count" in result["data"]["stats"]
    # 3 款 prompts 存在
    assert "continue" in result["data"]["prompts"]
    assert "overview" in result["data"]["prompts"]
    assert "review" in result["data"]["prompts"]


# ---- 计划域 render 测试 ----
def test_render_plans_preview():
    """render_plans_preview:status=ok,mode=plan-preview,copy_prompt 存在"""
    for h in range(0, 24, 2):
        insert_test_plan("2026-07-15", f"{h:02d}:00", f"{h+1:02d}:00",
                          f"时段 {h}", "维持.睡眠" if h < 6 else "工作.AI调优")
    from schedule_html_render import render_plans_preview
    plans = _db.list_plan_events("2026-07-15", include_inactive=True)
    result = render_plans_preview("2026-07-15", plan_events=plans)
    assert result["status"] == "ok"
    d = result["data"]
    assert d["meta"]["mode"] == "plan-preview"
    assert d["meta"]["date"] == "2026-07-15"
    assert "copy_prompt" in d
    assert d["status"] in ("ok", "conflict", "incomplete")


def test_render_plans_review():
    """render_plans_review:status=ok,mode=plan-review,events list 完整"""
    for h in range(0, 24, 3):
        insert_test_plan("2026-07-15", f"{h:02d}:00", f"{h+2:02d}:00",
                          f"计划 {h}", "工作.AI调优")
    from schedule_html_render import render_plans_review
    result = render_plans_review("2026-07-15")
    assert result["status"] == "ok"
    d = result["data"]
    assert d["meta"]["mode"] == "plan-review"
    assert "reviewed_count" in d["meta"]
    assert d["meta"]["total_count"] == 8
    assert d["meta"]["progress_pct"] == 0


# ---- plan_receipt 3 款 DRY 行为一致性测试(commit 083688f 锁住) ----
def test_plan_receipt_three_modes_consistency():
    """render_plan_receipt / add / write 三种模式,stats / plan_json / 4 部分 prompt 关键内容一致"""
    for h in range(0, 24, 2):
        insert_test_plan("2026-07-15", f"{h:02d}:00", f"{h+1:02d}:00",
                          f"计划 {h}", "工作.AI调优")
    from schedule_html_render import (
        render_plan_receipt, render_plan_receipt_add, render_plan_receipt_write
    )
    _db.ensure_plan_event(date="2026-07-15", time_start="11:00", time_end="12:00",
                           title="测试", category="工作.AI调优")
    plans = _db.list_plan_events("2026-07-15", include_inactive=True)
    plan_id = [p["id"] for p in plans if p["time_start"] == "11:00"][0]

    r_update = render_plan_receipt(plan_id, action="update")
    r_add = render_plan_receipt_add(plan_id)
    r_write = render_plan_receipt_write(plan_id)

    s_u = r_update["data"]["stats"]
    s_a = r_add["data"]["stats"]
    s_w = r_write["data"]["stats"]
    assert s_u["today_count"] == s_a["today_count"] == s_w["today_count"]
    assert s_u["completion_rate"] == s_a["completion_rate"] == s_w["completion_rate"]
    assert s_u["feishu_synced"] == s_a["feishu_synced"] == s_w["feishu_synced"]
    assert s_u["coverage_hours"] == s_a["coverage_hours"] == s_w["coverage_hours"]

    p_u = r_update["data"]["plan"]
    p_a = r_add["data"]["plan"]
    p_w = r_write["data"]["plan"]
    assert p_u["id"] == p_a["id"] == p_w["id"] == plan_id
    assert p_u["title"] == p_a["title"] == p_w["title"]

    for r, mode in [(r_update, "update"), (r_add, "add"), (r_write, "write")]:
        prompts = r["data"]["prompts"]
        # 3 款都有 overview + review/look_all
        assert "overview" in prompts
        # 每款至少有一个操作 prompt
        first_key = next(iter(prompts.keys()))
        first_prompt = prompts[first_key]
        assert "① 场景" in first_prompt or "①" in first_prompt or len(first_prompt) > 50
        # 至少含 id=plan_id 标识
        all_text = " ".join(prompts.values())
        assert f"id={plan_id}" in all_text

    assert r_update["data"]["meta"]["action"] == "update"
    # 3 款 mode 不同(标识用途)
    assert r_update["data"]["meta"]["mode"] == "plan-receipt"
    assert r_add["data"]["meta"]["mode"] == "plan-receipt-add"
    assert r_write["data"]["meta"]["mode"] == "plan-receipt-write"


def test_plan_receipt_action_label_difference():
    """3 款 plan_receipt 的 action_verb_zh(场景里"我刚X了一条")不同"""
    for h in range(0, 24, 2):
        insert_test_plan("2026-07-15", f"{h:02d}:00", f"{h+1:02d}:00",
                          f"p{h}", "工作.AI调优")
    _db.ensure_plan_event(date="2026-07-15", time_start="12:00", time_end="13:00",
                           title="测试", category="工作.AI调优")
    plans = _db.list_plan_events("2026-07-15", include_inactive=True)
    plan_id = [p["id"] for p in plans if p["time_start"] == "12:00"][0]

    from schedule_html_render import (
        render_plan_receipt, render_plan_receipt_add, render_plan_receipt_write
    )
    # 取各自操作 prompt 验证动词不同
    prompts_u = render_plan_receipt(plan_id, action="update")["data"]["prompts"]
    prompts_a = render_plan_receipt_add(plan_id)["data"]["prompts"]
    prompts_w = render_plan_receipt_write(plan_id)["data"]["prompts"]

    cp_u = prompts_u.get("adjust", "")
    cp_a = prompts_a.get("continue", "")
    cp_w = prompts_w.get("continue", "")

    assert "修改" in cp_u
    assert "补" in cp_a
    assert "写摘要" in cp_w


def test_helpers_directly():
    """3 个 helper 函数(commit 083688f 提取)直接测试"""
    for h in range(0, 24, 4):
        insert_test_plan("2026-07-15", f"{h:02d}:00", f"{h+1:02d}:00",
                          f"p{h}", "工作.AI调优")
    plans = _db.list_plan_events("2026-07-15", include_inactive=True)
    target = plans[0]

    from schedule_html_render import (
        _calc_plan_receipt_stats, _build_plan_json, _build_plan_receipt_base_prompt
    )

    stats = _calc_plan_receipt_stats(target, plans)
    assert stats["today_count"] == 6
    assert stats["completion_rate"] == 0
    assert "coverage_hours" in stats

    plan_json = _build_plan_json(target)
    assert str(target["id"]) in plan_json
    assert target["title"] in plan_json

    base = _build_plan_receipt_base_prompt(target["id"], target, stats, plan_json,
                                          "测试动作", "测试动作", "test")
    assert "① 场景" in base
    assert "测试动作" in base
    assert "② 数据" in base
    assert f"id={target['id']}" in base
    assert "④ 来源" in base


# ---- 复盘 start-end (跨域 dual-domain · Phase E) ----
# Spec: .scratch/replay-start-end/spec.md
# Issue: .scratch/replay-start-end/issues/01-skeleton.md (T01)

def test_render_replay_empty():
    """T01 · 区间无数据 → status='empty' + payload meta 正确"""
    from schedule_html_render import render_replay
    result = render_replay("2026-07-15", "2026-07-17")
    assert result["status"] == "empty", f"期望 empty, 实际 {result['status']}"
    d = result["data"]
    assert d["meta"]["mode"] == "replay"
    assert d["meta"]["start"] == "2026-07-15"
    assert d["meta"]["end"] == "2026-07-17"
    assert d["meta"]["days"] == 3
    assert d["meta"]["total_records"] == 0
    assert d["meta"]["total_minutes"] == 0
    # errors 字段必须存在(便于 5 状态 fallback 统一契约)
    assert "errors" in d
    assert d["errors"] == []


def test_render_replay_basic_ok():
    """T01 · 1 条 record + 1 条 plan → status='ok' + 4 段叙事字段骨架存在"""
    insert_test_records("2026-07-15", count=1)
    insert_test_plan("2026-07-15", "14:00", "15:00", "测试", "工作.AI调优")

    from schedule_html_render import render_replay
    result = render_replay("2026-07-15", "2026-07-15")
    assert result["status"] == "ok"
    d = result["data"]
    assert d["meta"]["mode"] == "replay"
    assert d["meta"]["total_records"] == 1
    # 4 段叙事字段骨架(T03-T06 各自填充实数据,T01 仅骨架)
    assert "record_aggregate" in d
    assert "plan_aggregate" in d
    assert "cross_domain" in d
    assert "ai_insights" in d
    assert "copy_prompt" in d


def test_render_replay_filename_default():
    """T01 · default_output_path({mode:replay}) → 路径含 '区间复盘_' 前缀 + subdir"""
    from schedule_html_render import default_output_path
    p = default_output_path({"mode": "replay"})
    name = p.name
    # 中文 command 名 + 时间戳 (永不覆盖在 _naming_path 内已保护)
    assert name.startswith("区间复盘_"), f"filename 应以'区间复盘_'开头,实际 {name}"
    # 时间戳格式 YYYYMMDD_HHMMSS
    assert len(name) == len("区间复盘_20260730_120000.html")
    # subdir 隔离(replay/)
    assert "replay" in str(p.parent).replace("\\", "/").split("schedule_html/")[-1]


def test_render_replay_filename_overwrite_protect():
    """T01 · 同秒两次调 _naming_path → 第二个加 _2 后缀(永不覆盖)"""
    from schedule_html_render import _naming_path, CN_COMMAND_MAP
    cmd = CN_COMMAND_MAP["replay"]
    # 用 monkeypatch 锁住 datetime.now,确保同秒
    import datetime as _dt
    class FrozenDateTime(_dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 7, 30, 12, 0, 0)
    import schedule_html_render
    original_dt = schedule_html_render.datetime
    schedule_html_render.datetime = FrozenDateTime
    try:
        p1 = _naming_path(cmd, "replay")
        p2 = _naming_path(cmd, "replay")
        # 确保父目录存在(以便 _2 路径可创建)
        p1.parent.mkdir(parents=True, exist_ok=True)
        p1.touch()
        try:
            p3 = _naming_path(cmd, "replay")
            assert p3 != p1, "第二次应生成不同路径"
            assert "_2." in p3.name or p3.name.endswith("_2.html"), \
                f"第三次应加 _2 后缀,实际 {p3.name}"
        finally:
            p1.unlink()
    finally:
        schedule_html_render.datetime = original_dt