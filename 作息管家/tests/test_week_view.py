"""周视图测试(实施 T6 · G1-A6 · 真新增自包含)

锁定契约:
- render-record-week 域命令注册进 COMMANDS 通道(discover 自动发现)
- 周视图 = 日历周(周一~周日)7×24 全分类总览,无数据的天也占位
- heatmap 数据形态与 record_category 同款:7×24,cell={cat, mins, color}
  (格 = 该小时覆盖分钟最多的 L1 分类)
- summary_items 按 L1 聚合(全分类总览)
- 空周不报错(5 状态 fallback 契约),锚点缺省 = 本周
- 输出走 _naming_path(中文 command 名)· record/week 子目录
"""
import json
import sys
from datetime import date as _d, timedelta as _td
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import schedule_db as _db
import week_view
import schedule_cli

ANCHOR = "2026-07-15"


def _monday_of(anchor: str) -> str:
    a = _d.fromisoformat(anchor)
    return (a - _td(days=a.weekday())).isoformat()


def _seed_record(date, time_start, time_end, category="工作.AI调优",
                 activity="测试活动", duration_minutes=None):
    if duration_minutes is None:
        s = time_start.split(":")
        e = time_end.split(":")
        duration_minutes = int(e[0]) * 60 + int(e[1]) - (int(s[0]) * 60 + int(s[1]))
    return _db.add_record_full(
        date=date, time_start=time_start, time_end=time_end,
        duration_minutes=duration_minutes, activity=activity, category=category,
        source_contents="测试来源", source_timestamps=time_start,
        analysis_reasoning="测试推理",
    )


def test_week_payload_shape():
    """payload 骨架:7 天日历周 + 7×24 热力图 + 标签齐全"""
    _seed_record("2026-07-15", "09:00", "11:00")
    r = week_view.render_record_week(ANCHOR)
    assert r["status"] == "ok"
    data = r["data"]
    meta = data["meta"]
    assert meta["mode"] == "record-week"
    monday = _monday_of(ANCHOR)
    assert meta["start"] == monday
    assert meta["end"] == ( _d.fromisoformat(monday) + _td(days=6)).isoformat()
    assert len(data["days"]) == 7
    assert data["days"][0] == monday
    assert len(data["weekday_labels"]) == 7
    assert data["weekday_labels"][0].startswith("周一")
    assert len(data["heatmap"]) == 7
    assert all(len(row) == 24 for row in data["heatmap"])
    assert len(data["day_totals"]) == 7
    assert meta["total_minutes"] == 120


def test_heatmap_dominant_cell():
    """周三 09:00-11:00 工作 → 该日 9/10 点格主导分类=工作(record_category 同形态)"""
    _seed_record("2026-07-15", "09:00", "11:00", category="工作.AI调优")
    r = week_view.render_record_week(ANCHOR)
    data = r["data"]
    wd_idx = _d.fromisoformat(ANCHOR).weekday()  # 周三 → 2
    assert data["heatmap"][wd_idx][9]["cat"] == "工作"
    assert data["heatmap"][wd_idx][9]["mins"] == 60
    assert data["heatmap"][wd_idx][10]["cat"] == "工作"
    assert data["heatmap"][wd_idx][8]["cat"] is None
    assert data["day_totals"][wd_idx] == 120


def test_heatmap_l1_mapping():
    """二级词 L1 聚合:健康.运动 → L1=健康;老一级词别名映射由 l1_of 纯函数保证"""
    from calculations import l1_of
    _seed_record("2026-07-15", "07:00", "08:00", category="健康.运动")
    r = week_view.render_record_week(ANCHOR)
    data = r["data"]
    wd_idx = _d.fromisoformat(ANCHOR).weekday()
    assert data["heatmap"][wd_idx][7]["cat"] == "健康"
    cats = {s["category"] for s in data["summary_items"]}
    assert "健康" in cats
    assert "运动" not in cats
    assert l1_of("运动.跑步") == "健康"  # 老一级词别名映射(calculations 纯函数)


def test_summary_by_l1():
    """summary_items 按 L1 聚合:两条同 L1 记录合并分钟数 + pct 计算"""
    _seed_record("2026-07-15", "22:00", "23:00", category="维持.睡眠")
    _seed_record("2026-07-16", "23:00", "23:30", category="维持.睡眠")
    r = week_view.render_record_week(ANCHOR)
    items = {s["category"]: s for s in r["data"]["summary_items"]}
    assert items["维持"]["total_minutes"] == 90
    assert items["维持"]["pct"] == 100.0
    assert items["维持"]["emoji"]


def test_empty_week_fallback():
    """空周:status ok + 全空格 + AI 钩子提示无记录(不 pretend 成功)"""
    r = week_view.render_record_week(ANCHOR)
    assert r["status"] == "ok"
    data = r["data"]
    assert data["records"] == []
    assert all(c["cat"] is None for row in data["heatmap"] for c in row)
    assert "无记录" in data["ai_questions"][0]
    assert data["meta"]["active_days"] == 0


def test_anchor_defaults_to_current_week():
    """无 anchor → 本周(今天所在周一~周日)"""
    r = week_view.render_record_week()
    today = _d.today()
    monday = (today - _td(days=today.weekday())).isoformat()
    assert r["data"]["meta"]["start"] == monday


def test_bad_anchor_returns_error_json(capsys):
    """非法日期 → status error JSON,不写文件"""
    week_view.week_view_main(["2026-99-99"])
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "error"
    assert "格式非法" in out["message"]


def test_week_view_main_writes_html(tmp_path, capsys, monkeypatch):
    """端到端:渲染写盘 → record/week/查作息周视图_*.html,payload 含周视图数据"""
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    _seed_record("2026-07-15", "09:00", "11:00")
    week_view.week_view_main([ANCHOR])
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "ok"
    fp = Path(out["data"]["file_path"])
    assert fp.exists()
    assert fp.name.startswith("查作息周视图_")
    assert fp.name.endswith(".html")
    assert out["data"]["start"] == _monday_of(ANCHOR)
    assert out["data"]["days"] == 7
    content = fp.read_text(encoding="utf-8")
    assert "record-week" in content
    assert "7×24" in content
    assert "2026-07-15" in content


def test_cli_domain_dispatch_e2e(tmp_path, capsys, monkeypatch):
    """渐进式注册通道 E2E:schedule_cli main() 走 else 钩子 dispatch 周视图

    注意:本测试文件顶部已 import week_view → discover 会跳过 sys.modules 已存在
    的模块(零副作用约定),故先弹出再恢复,模拟 CLI 冷启动场景。
    """
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    _seed_record("2026-07-15", "09:00", "11:00")
    old = sys.modules.pop("week_view", None)
    try:
        schedule_cli.main(["render-record-week", ANCHOR])
    finally:
        if old is not None:
            sys.modules["week_view"] = old
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "ok"
    assert out["data"]["mode"] == "record-week"
    assert Path(out["data"]["file_path"]).exists()


def test_domain_registry_contains_week_view():
    """COMMANDS 注册表含 render-record-week(discover 契约)"""
    old = sys.modules.pop("week_view", None)
    try:
        registry = schedule_cli.discover_domain_commands(SCRIPTS_DIR)
    finally:
        if old is not None:
            sys.modules["week_view"] = old
    assert "render-record-week" in registry
    assert callable(registry["render-record-week"])
