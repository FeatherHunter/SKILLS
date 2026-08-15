# -*- coding: utf-8 -*-
"""test_workout_plan_modes.py — render_workout_plan 多模式渲染测试 (ticket #6)

覆盖 9 个 mode:
  full / week / today / day / overview / vs / completion / missed / movement

验证:
- 每个 mode 生成合法 HTML,占位符恰好替换 1 次
- 数据结构含 mode 标记 + 对应字段
- JS 主入口可渲染(容器非空) — 由 Playwright 侧验证(本测试做结构断言)
"""
import json
import re
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import render_workout_plan as rwp  # noqa: E402


@pytest.fixture()
def seed_plan(temp_db):
    """写入一份 2 周测试计划 + 今日实绩(function-scope,每测试独立)

    显式依赖 temp_db(session-scope): 2026-08-11 事故教训——此前未请求
    temp_db, 单独跑本文件时 SKILLS_DB_PATH 解析到生产库, DELETE 会清空
    生产库 workout_plan_config/workout_plans(与 #257 事故同源)。
    """
    from db import get_db

    db_path = temp_db
    conn = get_db(db_path)
    c = conn.cursor()
    c.execute("DELETE FROM workout_plan_config")
    c.execute("DELETE FROM workout_plans")
    c.execute(
        "INSERT INTO workout_plan_config (title, version, description, total_weeks, start_date) "
        "VALUES (?, ?, ?, ?, ?)",
        ("测试计划", "v1", "pytest", 2, "2026-07-27"),
    )
    movements = json.dumps([
        {"name": "深蹲", "part": "腿", "sets": [{"reps": 10, "weight": 50}]},
        {"name": "卧推", "part": "胸", "sets": [{"reps": 8, "weight": 40}]},
    ], ensure_ascii=False)
    c.execute(
        "INSERT INTO workout_plans (week_number, day_of_week, session_index, session_label, "
        "time_start, time_end, is_rest_day, total_sets, movements) VALUES (?,?,?,?,?,?,?,?,?)",
        (1, 1, 1, "晨训", "07:00", "08:00", 0, 2, movements),
    )
    conn.commit()
    conn.close()
    yield db_path
    # teardown: 清空
    conn = get_db(db_path)
    conn.execute("DELETE FROM workout_plans")
    conn.execute("DELETE FROM workout_plan_config")
    conn.commit()
    conn.close()


def _extract_data(html: str) -> dict:
    m = re.search(r'<script id="payload" type="application/json">(.*?)</script>', html, re.DOTALL)
    assert m, "模板未注入 payload"
    raw = m.group(1).replace("<\\/", "</")
    return json.loads(raw)


@pytest.mark.parametrize("mode", [
    "full", "week", "today", "day", "overview", "vs", "completion", "missed", "movement", "action",
])
def test_mode_renders(seed_plan, mode):
    html = rwp.render(mode=mode, output_path=str(Path(__file__).parent / f"_plan_{mode}.html"))
    assert isinstance(html, str) and Path(html).exists()
    text = Path(html).read_text(encoding="utf-8")
    # 占位符被替换(恰好 1 次)
    assert text.count("<!--INJECT-DATA-->") == 0
    payload = _extract_data(text)
    assert payload["status"] == "ok"
    d = payload["data"]
    assert d["mode"] == mode
    assert d["config"]["title"] == "测试计划"


def test_full_mode_weeks(seed_plan):
    html = rwp.render(mode="full", output_path=str(Path(__file__).parent / "_plan_full.html"))
    d = _extract_data(Path(html).read_text(encoding="utf-8"))["data"]
    assert d["mode"] == "full"
    assert len(d["weeks"]) >= 1
    assert d["weeks"][0]["days"][0]["sessions"][0]["session_label"] == "晨训"


def test_today_mode_completion(seed_plan):
    html = rwp.render(mode="today", output_path=str(Path(__file__).parent / "_plan_today.html"))
    d = _extract_data(Path(html).read_text(encoding="utf-8"))["data"]
    assert "completion" in d
    assert "plan_sets" in d["completion"]
    assert d["date"]  # 今日


def test_overview_kpi(seed_plan):
    html = rwp.render(mode="overview", output_path=str(Path(__file__).parent / "_plan_ov.html"))
    d = _extract_data(Path(html).read_text(encoding="utf-8"))["data"]
    assert d["kpi"]["total_weeks"] == 2
    assert isinstance(d["weekly_rates"], list)


def test_vs_movement_rows(seed_plan):
    html = rwp.render(mode="vs", output_path=str(Path(__file__).parent / "_plan_vs.html"))
    d = _extract_data(Path(html).read_text(encoding="utf-8"))["data"]
    assert "movement_rows" in d
    assert "completion_rate" in d


def test_missed_and_movement(seed_plan):
    html = rwp.render(mode="missed", output_path=str(Path(__file__).parent / "_plan_missed.html"))
    d = _extract_data(Path(html).read_text(encoding="utf-8"))["data"]
    assert isinstance(d["missed"], list)
    html2 = rwp.render(mode="movement", output_path=str(Path(__file__).parent / "_plan_mv.html"))
    d2 = _extract_data(Path(html2).read_text(encoding="utf-8"))["data"]
    assert isinstance(d2["ranking"], list)


def test_plan_generator_delete_plan(seed_plan):
    """缺口②:delete_plan 删除整个计划"""
    from plan_generator import delete_plan
    from workout_plan import get_plan_config

    result = delete_plan()
    assert result["deleted_config"]["title"] == "测试计划"
    assert result["deleted_rows"] >= 1
    assert get_plan_config() is None


def test_plan_generator_copy_plan(seed_plan):
    """缺口②:copy_plan 复制整个计划"""
    from plan_generator import _get_db, copy_plan
    from workout_plan import get_plan_config

    result = copy_plan(new_title="测试副本")
    assert result["new_title"] == "测试副本"
    assert result["copied_rows"] >= 1
    cfg = get_plan_config()
    assert cfg["title"] == "测试副本"
    # 清理
    db = _get_db()
    db.execute("DELETE FROM workout_plans")
    db.execute("DELETE FROM workout_plan_config")
    db.commit()
    db.close()


def test_plan_generator_delete_day(seed_plan):
    """缺口②:delete_day 删除某天全部 session"""
    from plan_generator import delete_day

    result = delete_day(1, 1)
    assert result["deleted_sessions"] >= 1
    assert result["snapshot"][0]["session_label"] == "晨训"


def test_day_mode_specific(seed_plan):
    """#255: day 模式 4 态验证(训练日/休息日/未开始/非法日期)"""
    from datetime import date
    from db import get_db

    db = get_db(seed_plan)
    c = db.cursor()
    # 周三休息日(训练日已有 week1/day1)
    c.execute(
        "INSERT INTO workout_plans (week_number, day_of_week, session_index, session_label, is_rest_day, total_sets, movements) "
        "VALUES (?,?,?,?,?,?,?)",
        (1, 3, 1, "休息", 1, 0, "[]"),
    )
    db.commit()
    db.close()

    # 训练日(2026-07-27 周一 = 计划第 1 周)
    html = rwp.render(mode="day", day_date=date(2026, 7, 27),
                      output_path=str(Path(__file__).parent / "_plan_day1.html"))
    d = _extract_data(Path(html).read_text(encoding="utf-8"))["data"]
    assert d["mode"] == "day"
    assert d["unstarted"] is False
    assert len(d["sessions"]) >= 1
    assert d["sessions"][0]["session_label"] == "晨训"
    assert d["plan_week"] == 1

    # 休息日(2026-07-29 周三)
    html2 = rwp.render(mode="day", day_date=date(2026, 7, 29),
                       output_path=str(Path(__file__).parent / "_plan_day2.html"))
    d2 = _extract_data(Path(html2).read_text(encoding="utf-8"))["data"]
    assert d2["is_rest"] is True

    # 未开始(2026-07-01 < start 07-27)
    html3 = rwp.render(mode="day", day_date=date(2026, 7, 1),
                       output_path=str(Path(__file__).parent / "_plan_day3.html"))
    d3 = _extract_data(Path(html3).read_text(encoding="utf-8"))["data"]
    assert d3["unstarted"] is True

    # 非法日期 → 友好错误(非 traceback)
    err = rwp.render(mode="day", day_date="abc")
    assert isinstance(err, str) and "无效" in err


def test_today_mode_unchanged(seed_plan):
    """#255 重构: today 模式 mode 字段与完成度契约不变"""
    html = rwp.render(mode="today", output_path=str(Path(__file__).parent / "_plan_today2.html"))
    d = _extract_data(Path(html).read_text(encoding="utf-8"))["data"]
    assert d["mode"] == "today"
    assert "completion" in d


def test_action_mode_specific(seed_plan):
    """#256: action 模式 4 态(精确匹配/子串/无匹配+候选/空名)"""
    from db import get_db

    db = get_db(seed_plan)
    c = db.cursor()
    # seed 计划有 深蹲/卧推(week1 day1 晨训); 补一周末周验证覆盖范围
    c.execute(
        "INSERT INTO workout_plans (week_number, day_of_week, session_index, session_label, time_start, time_end, is_rest_day, total_sets, movements) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (2, 1, 1, "晨训", "07:00", "08:00", 0, 2,
         json.dumps([{"name": "深蹲", "part": "腿", "sets": [{"reps": 10, "weight": 50}]}], ensure_ascii=False)),
    )
    db.commit()
    db.close()

    # 精确匹配
    html = rwp.render(mode="action", action_name="深蹲", output_path=str(Path(__file__).parent / "_plan_act1.html"))
    d = _extract_data(Path(html).read_text(encoding="utf-8"))["data"]
    assert d["mode"] == "action"
    assert d["query"] == "深蹲"
    assert len(d["positions"]) >= 2  # 2 周都有
    assert d["summary"]["total_sets"] >= 2  # 每周 1 组 × 2 周
    assert d["next_date"]  # 循环语义下必有下次练习日

    # 子串匹配(卧推 → 杠铃卧推)
    html2 = rwp.render(mode="action", action_name="卧推", output_path=str(Path(__file__).parent / "_plan_act2.html"))
    d2 = _extract_data(Path(html2).read_text(encoding="utf-8"))["data"]
    assert len(d2["positions"]) >= 1
    assert d2["positions"][0]["name"].endswith("卧推")

    # 无匹配 → error + candidates
    html3 = rwp.render(mode="action", action_name="高翻", output_path=str(Path(__file__).parent / "_plan_act3.html"))
    d3 = _extract_data(Path(html3).read_text(encoding="utf-8"))["data"]
    assert "error" in d3 and "无" in d3["error"]
    assert "candidates" in d3

    # 空名 → 缺动作名错误
    html4 = rwp.render(mode="action", action_name="", output_path=str(Path(__file__).parent / "_plan_act4.html"))
    d4 = _extract_data(Path(html4).read_text(encoding="utf-8"))["data"]
    assert d4["error"] == "缺少动作名"


# === #323 修复验证测试(scene.snapshot 必须含真实计划内容) ===
# 旧 bug: scene.snapshot.summary=[] sections=[] 复制数据只有 3 行头部(空壳)
# 新增 4 个测试:
#   1) test_full_snapshot_has_plan_chain       — full 模式内容(周→训练段→动作→组数/重量)
#   2) test_today_snapshot_well_formed          — today 模式 structure(command_cn + summary)
#   3) test_snapshot_command_cn_per_mode        — 10 mode 各自 command_cn(防硬编码「看训练计划」回归)
#   4) test_snapshot_summary_sections_well_formed — 10 mode summary/sections 非空(防空壳回归)


def test_full_snapshot_has_plan_chain(seed_plan):
    """#323 AC: full 模式 scene.snapshot 必须含真实计划内容
    旧 doCopy 行为: 计划标题 + 总周数 + 逐周逐天逐训练段 + 动作名/部位/组数/重量
    """
    html = rwp.render(mode="full", output_path=str(Path(__file__).parent / "_plan_full_snap.html"))
    d = _extract_data(Path(html).read_text(encoding="utf-8"))["data"]
    snap = d["scene"]["snapshot"]
    # 标题(command_cn)正确
    assert snap["title"] == "看完整计划"
    # summary 含计划元信息
    summary_text = " | ".join(snap["summary"])
    assert "测试计划" in summary_text, f"summary 应含计划标题,实际: {snap['summary']!r}"
    assert "总周数 2" in summary_text, f"summary 应含总周数,实际: {snap['summary']!r}"
    assert "2026-07-27" in summary_text, f"summary 应含起始日,实际: {snap['summary']!r}"
    # sections 含周次 + 训练段 + 动作名 + 组数 + 重量(关键字段)
    headings = [s["heading"] for s in snap["sections"]]
    assert "第 1 周" in headings, f"sections 应含「第 1 周」heading,实际: {headings!r}"
    all_rows = []
    for s in snap["sections"]:
        all_rows.extend(s["rows"])
    rows_text = " | ".join(all_rows)
    assert "晨训" in rows_text, f"应含训练段「晨训」,实际: {all_rows!r}"
    assert "深蹲" in rows_text, f"应含动作「深蹲」,实际: {all_rows!r}"
    assert "卧推" in rows_text, f"应含动作「卧推」,实际: {all_rows!r}"
    assert "腿" in rows_text, f"应含部位「腿」,实际: {all_rows!r}"
    assert "50kg" in rows_text or "50" in rows_text, f"应含重量 50,实际: {all_rows!r}"
    assert "40kg" in rows_text or "40" in rows_text, f"应含重量 40,实际: {all_rows!r}"
    # scene 元数据
    assert d["scene"]["scene_id"] == "看完整计划"
    assert d["meta"]["command_cn"] == "看完整计划"
    assert d["meta"]["wake_word"] == "看完整计划"


def test_today_snapshot_well_formed(seed_plan):
    """#323 AC: today 模式 scene.snapshot 必须 well-formed(per-mode command_cn + 非空 summary)

    注: today 用「今天」实际日期,seed_plan 数据按 2026-07-27 起始;若今日不在 plan 内
    则 snapshot sections 可能为空(友好占位),但 summary 必含「计划第 N 周」/「完成度」或
    「今日无训练安排」,scene meta 必填今天专属 command_cn。
    """
    html = rwp.render(mode="today", output_path=str(Path(__file__).parent / "_plan_today_snap.html"))
    d = _extract_data(Path(html).read_text(encoding="utf-8"))["data"]
    snap = d["scene"]["snapshot"]
    # 关键字段(per-mode command_cn)必须正确(防硬编码「看训练计划」回归)
    assert snap["title"] == "看今天练什么", \
        f"today scene title 应为「看今天练什么」(per-mode),实际: {snap['title']!r}"
    assert d["scene"]["scene_id"] == "看今天练什么"
    assert d["meta"]["command_cn"] == "看今天练什么"
    assert d["meta"]["wake_word"] == "看今天练什么"
    # summary 非空(回归 bug: summary=[])
    assert isinstance(snap["summary"], list)
    assert len(snap["summary"]) > 0, \
        f"today summary 应非空(回归 bug: 空壳),实际: {snap['summary']!r}"
    # sections 是 list(数据空时为 [],有数据时为 [...]),不报错
    assert isinstance(snap["sections"], list)
    # sections 内每节有 heading + rows
    for sec in snap["sections"]:
        assert isinstance(sec.get("heading"), str) and sec["heading"], \
            f"section 缺 heading: {sec!r}"
        assert isinstance(sec.get("rows"), list), f"section 缺 rows: {sec!r}"
    # 若今日恰好有训练段(seed 起始日 2026-07-27 是周一,周数循环),则验证 content
    sessions = d.get("sessions") or []
    non_rest = [s for s in sessions if not s.get("is_rest_day")]
    if non_rest:
        all_rows = []
        for sec in snap["sections"]:
            all_rows.extend(sec["rows"])
        rows_text = " | ".join(all_rows)
        first_session = non_rest[0].get("session_label", "")
        if first_session:
            assert first_session in rows_text, \
                f"今日有训练段「{first_session}」时,snapshot 应含其名,实际: {all_rows!r}"


@pytest.mark.parametrize("mode,expected_cn", [
    ("full", "看完整计划"),
    ("week", "看周计划"),
    ("today", "看今天练什么"),
    ("day", "看某天练什么"),
    ("overview", "看计划概览"),
    ("vs", "看计划vs实际"),
    ("completion", "看计划完成率"),
    ("missed", "看未完成训练"),
    ("movement", "看动作完成率"),
    ("action", "看某动作安排"),
])
def test_snapshot_command_cn_per_mode(seed_plan, mode, expected_cn):
    """#323 AC: 10 个 mode 各自填正确的 command_cn(scene header / meta / snapshot.title)

    旧 bug: 全部硬编码「看训练计划」——任何 mode 渲染后 scene 头都是「看训练计划(看训练计划)」
    """
    html = rwp.render(
        mode=mode,
        action_name="深蹲" if mode == "action" else None,
        day_date=__import__("datetime").date(2026, 7, 27) if mode == "day" else None,
        output_path=str(Path(__file__).parent / f"_plan_{mode}_cn.html"),
    )
    d = _extract_data(Path(html).read_text(encoding="utf-8"))["data"]
    assert d["scene"]["scene_id"] == expected_cn, \
        f"{mode} scene_id 应为「{expected_cn}」,实际: {d['scene'].get('scene_id')!r}"
    assert d["meta"]["command_cn"] == expected_cn, \
        f"{mode} meta.command_cn 应为「{expected_cn}」,实际: {d['meta'].get('command_cn')!r}"
    assert d["meta"]["wake_word"] == expected_cn, \
        f"{mode} meta.wake_word 应为「{expected_cn}」,实际: {d['meta'].get('wake_word')!r}"
    assert d["scene"]["snapshot"]["title"] == expected_cn, \
        f"{mode} snapshot.title 应为「{expected_cn}」,实际: {d['scene']['snapshot'].get('title')!r}"


@pytest.mark.parametrize("mode", [
    "full", "week", "today", "day", "overview", "vs",
    "completion", "missed", "movement", "action",
])
def test_snapshot_summary_sections_well_formed(seed_plan, mode):
    """#323 AC: 10 个 mode 的 scene.snapshot.summary + sections 都 well-formed

    旧 bug: 所有 mode 都 summary=[] sections=[] → 复制数据只有 3 行头部(空壳)
    新行为: 至少 summary 非空;sections 在有数据时非空(数据空时 = [])
    """
    html = rwp.render(
        mode=mode,
        action_name="深蹲" if mode == "action" else None,
        day_date=__import__("datetime").date(2026, 7, 27) if mode == "day" else None,
        output_path=str(Path(__file__).parent / f"_plan_{mode}_well.html"),
    )
    d = _extract_data(Path(html).read_text(encoding="utf-8"))["data"]
    snap = d["scene"]["snapshot"]
    # snapshot 结构必填字段
    assert isinstance(snap.get("summary"), list), f"{mode}: summary 应为 list"
    assert isinstance(snap.get("sections"), list), f"{mode}: sections 应为 list"
    # 回归锁定: summary 不能为空(旧 bug = [])
    assert len(snap["summary"]) > 0, \
        f"{mode}: summary 必非空(回归 bug: 空壳),实际 {snap['summary']!r}"
    # sections: full/week/overview/vs/completion/missed/movement/action 有数据时必非空
    # today/day 看日期是否有 plan(可能在「今日无训练安排」fallback)
    if mode in ("full", "week", "overview", "vs", "completion", "missed", "movement", "action"):
        assert len(snap["sections"]) > 0, \
            f"{mode}: sections 应非空(有 seed plan 数据),实际 {snap['sections']!r}"
    # sections 每节结构正确(若有节)
    for sec in snap["sections"]:
        assert isinstance(sec.get("heading"), str) and sec["heading"], \
            f"{mode}: section 缺/空 heading: {sec!r}"
        assert isinstance(sec.get("rows"), list), f"{mode}: section 缺 rows: {sec!r}"
        for row in sec["rows"]:
            assert isinstance(row, str) and row, f"{mode}: row 缺/空: {row!r}"

# === #323 对抗式审查 · 双重缩进回归锁 ===
# 旧 bug: snapshot builders 加 "  " 前缀 + buildDataText 加 "  · " 前缀 →
#  动作行输出 "  ·   深蹲..."(三空格)。修复后 action 行不再含手写前缀。

def test_no_double_indent_in_snapshot_rows(seed_plan):
    """#323 对抗审查: snapshot rows 不应含手写缩进前缀(由 buildDataText 统一加)"""
    for mode in ("full", "week", "day", "action", "missed"):
        kwargs = {}
        if mode == "day":
            from datetime import date as _d
            kwargs["day_date"] = _d(2026, 7, 27)
        elif mode == "action":
            kwargs["action_name"] = "深蹲"
        html = rwp.render(
            mode=mode,
            output_path=str(Path(__file__).parent / f"_plan_{mode}_indent.html"),
            **kwargs,
        )
        d = _extract_data(Path(html).read_text(encoding="utf-8"))["data"]
        snap = d["scene"]["snapshot"]
        for sec in snap["sections"]:
            for row in sec["rows"]:
                assert "·   " not in row, (
                    f"{mode} 双重缩进残留: {row!r},section: {sec['heading']!r}"
                )
                assert not row.startswith("  "), (
                    f"{mode} 行首双重缩进残留: {row!r},section: {sec['heading']!r}"
                )


def test_full_copy_output_no_triple_space(seed_plan):
    """#323 对抗审查: 端到端验证 buildDataText 输出无三空格"""
    from playwright.sync_api import sync_playwright
    html = rwp.render(
        mode="full",
        output_path=str(Path(__file__).parent / "_plan_full_e2e_indent.html"),
    )
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(
            viewport={"width": 375, "height": 667},
            device_scale_factor=2, is_mobile=True, has_touch=True,
        )
        page = ctx.new_page()
        page.goto(f"file:///{Path(html).resolve()}")
        page.wait_for_load_state("networkidle")
        text = page.evaluate("() => window.buildDataText(window.__hmPayload)")
        browser.close()
    bad = [line for line in text.split('\n') if '  ·   ' in line]
    assert not bad, (
        f"复制数据输出含双重缩进行: {bad!r},完整输出:\n{text}"
    )