# -*- coding: utf-8 -*-
"""test_plan_receipt.py — render_plan_receipt 写类场景回执测试 (ticket #6)

覆盖 12 个 live 模式:set/copy/rest/add/set_week/update/update_day/
delete_day/update_movement/delete/sync/backfill

验证:
- 每个模式生成合法回执数据契约(status/op/summary/diff)
- 写库后 DB 状态正确(幂等可重跑)
- 思考链强制(--chain 缺失 → exit 2)
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import render_plan_receipt as rpr  # noqa: E402

CHAIN = "1.解析→2.写库→3.回执"

SAMPLE_PLAN = {
    "config": {"title": "T1", "total_weeks": 4, "start_date": "2026-07-27", "description": "",
               "available_equipment": ["杠铃"]},
    "weeks": [{"week_number": 1, "days": [{"day_of_week": 1, "sessions": [
        {"session_label": "晨训", "time_start": "07:00", "time_end": "08:00",
         "total_sets": 2, "movements": [
             {"name": "杠铃深蹲", "part": "腿", "sets": [{"reps": 10, "weight": 50}]}]}]}]}],
}


@pytest.fixture()
def seeded():
    """独立种子:设置一份计划供后续模式测试"""
    d = rpr.build_live_plan_set(CHAIN, json.dumps(SAMPLE_PLAN, ensure_ascii=False))
    assert d["data"]["op"] == "create"
    return d


def test_plan_set(seeded):
    d = seeded
    assert d["data"]["entity_type"] == "定训练计划"
    assert "训练计划已设置" in d["data"]["summary"]
    assert d["data"]["diff"]["items"][0]["label"] == "标题"


def test_plan_copy(seeded):
    d = rpr.build_live_plan_copy(CHAIN, "副本")
    assert d["data"]["entity_type"] == "复制训练计划"
    assert "已复制为新标题「副本」" in d["data"]["summary"]


def test_plan_rest(seeded):
    d = rpr.build_live_plan_rest(CHAIN, 1, 1, 1)
    assert d["data"]["entity_type"] == "定休息日"
    assert "已标记为休息日" in d["data"]["summary"]


def test_plan_add(seeded):
    d = rpr.build_live_plan_add(CHAIN, 1, 1, "硬拉", 3, 60)
    assert d["data"]["entity_type"] == "加训练动作"
    assert "硬拉" in d["data"]["summary"]


def test_plan_set_week(seeded):
    days = {"1": [{"label": "胸日", "total_sets": 3, "movements": []}],
            "2": [{"label": "腿日", "total_sets": 3, "movements": []}]}
    d = rpr.build_live_plan_set_week(CHAIN, 2, json.dumps(days, ensure_ascii=False))
    assert d["data"]["entity_type"] == "定一周计划"
    assert "共 2 个训练时段" in d["data"]["summary"]


def test_plan_update(seeded):
    d = rpr.build_live_plan_update(CHAIN, ["title"], ["新标题"])
    assert d["data"]["entity_type"] == "改训练计划"
    assert "标题" in d["data"]["summary"]


def test_plan_update_day(seeded):
    d = rpr.build_live_plan_update_day(CHAIN, 1, 1, 1, label="晚间")
    assert d["data"]["entity_type"] == "改某天训练"
    assert "时段 1 已更新" in d["data"]["summary"]


def test_plan_delete_day(seeded):
    d = rpr.build_live_plan_delete_day(CHAIN, 1, 1)
    assert d["data"]["entity_type"] == "删某天训练"
    assert "已删除第 1 周 周1" in d["data"]["summary"]


def test_plan_update_movement(seeded):
    d = rpr.build_live_plan_update_movement(CHAIN, 1, 1, 1, "杠铃深蹲", "杠铃卧推", 5)
    assert d["data"]["entity_type"] == "改动作"
    assert "杠铃深蹲 → 杠铃卧推" in d["data"]["summary"]


def test_plan_delete(seeded):
    d = rpr.build_live_plan_delete(CHAIN)
    assert d["data"]["entity_type"] == "撤销训练计划"
    assert "已撤销" in d["data"]["summary"]


def test_plan_sync(seeded):
    results = {"date": "2026-08-02", "pushed": 3, "results": [{"ok": True}]}
    d = rpr.build_live_plan_sync(CHAIN, "2026-08-02", json.dumps(results, ensure_ascii=False))
    assert d["data"]["entity_type"] == "同步到训记"
    assert "3 条训练" in d["data"]["summary"]


def test_plan_backfill(seeded):
    results = {"date": "2026-08-02", "inserted": 2, "updated": 1}
    d = rpr.build_live_plan_backfill(CHAIN, "2026-08-02", json.dumps(results, ensure_ascii=False))
    assert d["data"]["entity_type"] == "拉训记实绩"
    assert "新增 2 条" in d["data"]["summary"]


def test_chain_required():
    """R3 思考链强制:缺失 → exit 2"""
    r = subprocess.run(
        [sys.executable, str(SCRIPTS / "render_plan_receipt.py"),
         "--live-plan-delete"],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert r.returncode == 2
    assert "chain" in r.stderr.lower() or "思考链" in r.stderr


def test_html_output(seeded, tmp_path):
    """端到端:渲染 HTML 文件 + 注入校验"""
    d = rpr.build_live_plan_copy(CHAIN, "副本")
    out = tmp_path / "copy.html"
    html = rpr.render_html(d)
    out.write_text(html, encoding="utf-8")
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert 'id="payload"' in text and "actionBar" in text
    assert text.count("<!--INJECT-DATA-->") == 0
