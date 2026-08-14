# -*- coding: utf-8 -*-
"""商量计划预览 · 交互测试(#324 收尾 A 项 · 2026-08-13)

用 node DOM-stub 驱动**真实渲染产物**,模拟用户交互:
- 页面初始状态(标题 / 徽章与动作状态不重复 / 统计卡 / 冲突卡 / 泳道)
- 点「复制计划给 AI」→ 校验剪贴板内容(3 段式 / 无脚本调用 / 冲突重叠明细)
- 冲突卡改时段 → 校验复制内容带上调整 + 页面提示

node 不可用时自动跳过(测试不引入 node 硬依赖)。
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

NODE = shutil.which("node")
JS = Path(__file__).parent / "_plan_preview_interaction.js"

pytestmark = pytest.mark.skipif(NODE is None, reason="node 不可用,跳过交互测试")


def test_plan_preview_copy_and_adjust_interaction(tmp_path, monkeypatch):
    """渲染真实产物 → node DOM-stub 交互断言"""
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))

    import schedule_db as _db
    from schedule_html_render import render_and_write, render_plans_preview

    # 1 条锁定 + 2 条候选(第 1 条与锁定重叠 09:00–09:30)
    _db.ensure_plan_event(
        date="2026-08-15", time_start="09:00", time_end="10:00",
        title="晨会", category="工作.会议",
    )
    candidates = [
        {"time_start": "08:00", "time_end": "09:30", "title": "通勤 + 晨读", "category": "日常.通勤"},
        {"time_start": "20:00", "time_end": "21:30", "title": "今日复盘", "category": "维持.睡眠"},
    ]
    # 与 CLI 同路径: 先拉当日锁定事件,再传给 preview(render 本身不读 DB)
    locked = _db.list_plan_events("2026-08-15", include_inactive=False)
    payload = render_plans_preview("2026-08-15", plan_events=candidates, locked_events=locked)
    assert payload["status"] in ("ok", "conflict", "incomplete"), payload
    assert payload.get("data")
    assert len(payload["data"]["conflicts"]) == 1
    c = payload["data"]["conflicts"][0]
    assert c["overlap"] == "09:00–09:30" and c["overlap_minutes"] == 30

    result = render_and_write(payload, tmp_path / "preview.html")
    assert result["status"] == "ok"

    out = subprocess.run(
        [NODE, str(JS), result["data"]["file_path"]],
        capture_output=True, text=True, encoding="utf-8",
    )
    report = json.loads(out.stdout) if out.stdout.strip() else {}
    assert out.returncode == 0, f"node 交互断言失败:\n{out.stdout}\n{out.stderr}"
    assert report.get("all_ok"), f"交互断言未全过: {report}"
