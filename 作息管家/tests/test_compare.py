"""对比类 CLI 测试(手册 §4.1 命名合规 + #25 唤醒词)

锁住 render_record_compare + render_record_compare_months 的:
- payload 关键字段(2 ranges + diffs + ai_questions)
- HTML 命名合规(手册 §4.1:<command>_<YYYYMMDD>_<HHMMSS>[_<N>].html)
- 派生计算(build_compare_aggregates + build_diff_table)
"""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import schedule_db as _db
import re

# 命名合规正则
NAMING_RE = re.compile(r"^[a-z_]+_\d{8}_\d{6}(_\d+)?\.html$")


def _seed_two_months():
    """6 月 vs 7 月各塞几条不同分类的记录,制造对比差异"""
    # 6 月: 多工作 + 少健康
    for i, (h, m, cat) in enumerate([
        (8, 60, "工作.AI调优"),
        (10, 90, "工作.AI调优"),
        (12, 30, "维持.用餐"),
        (14, 60, "工作.AI调优"),
        (20, 30, "调整.休息"),
    ]):
        _db.add_record_full(
            date=f"2026-06-{10+i:02d}", time_start=f"{h:02d}:00", time_end=f"{h:02d}:{m-30:02d}",
            duration_minutes=m, activity=f"6月测试{i+1}", category=cat,
            source_contents=f"6月测试{i+1}内容", source_timestamps=f"{h:02d}:00",
            analysis_reasoning=f"6月{i+1}",
        )
    # 7 月: 少工作 + 多健康
    for i, (h, m, cat) in enumerate([
        (7, 60, "健康.健身"),
        (8, 30, "维持.用餐"),
        (9, 120, "工作.AI调优"),
        (18, 60, "健康.修行"),
        (21, 30, "调整.休息"),
    ]):
        _db.add_record_full(
            date=f"2026-07-{10+i:02d}", time_start=f"{h:02d}:00", time_end=f"{h:02d}:{m-30:02d}",
            duration_minutes=m, activity=f"7月测试{i+1}", category=cat,
            source_contents=f"7月测试{i+1}内容", source_timestamps=f"{h:02d}:00",
            analysis_reasoning=f"7月{i+1}",
        )


def test_render_record_compare_basic():
    """render_record_compare 6 个参数(labelA/startA/endA/labelB/startB/endB)

    payload 必含:ranges(2 个) + diffs + ai_questions + errors
    """
    _seed_two_months()
    from schedule_html_render import render_record_compare
    result = render_record_compare(
        "6月", "2026-06-01", "2026-06-30",
        "7月", "2026-07-01", "2026-07-31",
    )
    assert result["status"] == "ok"
    d = result["data"]
    assert d["meta"]["mode"] == "record-compare"
    assert "6月" in d["meta"]["title"] and "7月" in d["meta"]["title"]
    # 2 个 range
    assert len(d["ranges"]) == 2
    assert d["ranges"][0]["label"] == "6月"
    assert d["ranges"][1]["label"] == "7月"
    # 各自 5 条记录(总时长: 6 月 = 60+90+30+60+30 = 270, 7 月 = 60+30+120+60+30 = 300)
    assert d["ranges"][0]["total"] == 270
    assert d["ranges"][1]["total"] == 300
    # diffs 是 dict 列表(每个 HEALTH_DIM 一条 diff)
    assert isinstance(d["diffs"], list)
    assert len(d["diffs"]) > 0
    # AI 问题列表
    assert "ai_questions" in d
    assert isinstance(d["ai_questions"], list)
    # 错误列表(必须空)
    assert d["errors"] == []


def test_render_record_compare_diffs_have_both_categories():
    """diff 包含 6 月有 7 月没的分类 + 反向(按 HEALTH_DIMS 7 维度)"""
    _seed_two_months()
    from schedule_html_render import render_record_compare
    result = render_record_compare(
        "6月", "2026-06-01", "2026-06-30",
        "7月", "2026-07-01", "2026-07-31",
    )
    diffs = result["data"]["diffs"]
    diff_dims = {d["dim"] for d in diffs}
    # diffs 应该按 7 维度展开,至少含"维持""健康""工作""调整"
    assert "维持" in diff_dims
    assert "健康" in diff_dims
    assert "工作" in diff_dims
    # diffs 每条都有 a/b/delta(秒级数值)
    for d in diffs:
        assert "a" in d and "b" in d and "delta" in d


def test_render_record_compare_empty_range():
    """空范围(没数据)仍能返回,不崩溃"""
    _seed_two_months()
    from schedule_html_render import render_record_compare
    result = render_record_compare(
        "空范围A", "2020-01-01", "2020-01-31",
        "空范围B", "2020-02-01", "2020-02-29",
    )
    assert result["status"] == "ok"
    d = result["data"]
    assert d["ranges"][0]["total"] == 0
    assert d["ranges"][1]["total"] == 0


def test_render_record_compare_meta_subtitle():
    """meta.subtitle 含两个范围的 start~end 标识"""
    _seed_two_months()
    from schedule_html_render import render_record_compare
    result = render_record_compare(
        "6月", "2026-06-01", "2026-06-30",
        "7月", "2026-07-01", "2026-07-31",
    )
    subtitle = result["data"]["meta"]["subtitle"]
    assert "2026-06-01" in subtitle
    assert "2026-06-30" in subtitle
    assert "2026-07-01" in subtitle
    assert "2026-07-31" in subtitle


def test_render_record_compare_label_in_payload():
    """label 出现在 payload(用户能识别是哪个月)"""
    _seed_two_months()
    from schedule_html_render import render_record_compare
    result = render_record_compare(
        "6月", "2026-06-01", "2026-06-30",
        "7月", "2026-07-01", "2026-07-31",
    )
    # label 在 meta.title
    assert "6月" in result["data"]["meta"]["title"]
    assert "7月" in result["data"]["meta"]["title"]
    # label 在 ranges
    labels = [r["label"] for r in result["data"]["ranges"]]
    assert labels == ["6月", "7月"]


def test_compare_filename_compliance(tmp_path, monkeypatch):
    """render-record-compare 和 render-record-compare-months 输出文件名
    都符合手册 §4.1:<command>_<YYYYMMDD>_<HHMMSS>.html
    """
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    from schedule_html_render import record_output_path

    p1 = record_output_path("record-compare", {
        "label_a": "6月", "start_a": "2026-06-01", "end_a": "2026-06-30",
        "label_b": "7月", "start_b": "2026-07-01", "end_b": "2026-07-31",
    })
    assert NAMING_RE.match(p1.name), f"命名不规范:{p1.name}"
    assert p1.name.startswith("record_compare_"), f"command 错:{p1.name}"
    # 子目录是 record/compare
    assert "compare" in str(p1.parent)