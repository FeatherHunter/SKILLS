"""B3+B4 重构测试 · _build_record_copy_prompt 单 map + CopyPromptContext(2026-07-29)

锁住:
- `_COPY_PROMPT_PARTS` 单 map 替代原 SCENE/EXPECT/SOURCE 三平行 dict
- `CopyPromptContext` dataclass 把 date/total_minutes/summary_items/extra_data 打包
- 调用方不再往 meta 塞 date/total_minutes 仅为喂 _build_record_copy_prompt
- 行为不变:返回 4 部分 prompt 字符串(场景/数据/期望/来源)

第一性(code-review 发现):
- B3: 三平行 dict 在同一函数里查同一个 mode key 三次 → Repeated Switches smell
- B4: meta dict 污染(date/total_minutes 仅为喂 _build_record_copy_prompt 加)→ Divergent Change smell
"""
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import schedule_html_render as _render


def test_copy_prompt_parts_map_exists():
    """_COPY_PROMPT_PARTS 单 map 存在(B3 替代三平行 dict)"""
    assert hasattr(_render, "_COPY_PROMPT_PARTS"), (
        "_COPY_PROMPT_PARTS 缺失(B3 契约:单 map 替代 SCENE/EXPECT/SOURCE 三平行 dict)"
    )
    parts = _render._COPY_PROMPT_PARTS
    # 6 个 record mode 全覆盖
    expected_modes = {"record-day", "record-range", "record-compare",
                      "record-category", "record-anomaly", "record-detail"}
    assert expected_modes.issubset(set(parts.keys())), (
        f"_COPY_PROMPT_PARTS 缺 mode,实际 keys: {set(parts.keys())}"
    )
    # 每个 mode 含 scene/expect/source 3 个字段(替代三平行 dict)
    for mode, part in parts.items():
        assert "scene" in part, f"{mode}: 缺 scene 字段"
        assert "expect" in part, f"{mode}: 缺 expect 字段"
        assert "source" in part, f"{mode}: 缺 source 字段"


def test_copy_prompt_context_dataclass_exists():
    """CopyPromptContext dataclass 存在(B4 替代 meta 污染)"""
    assert hasattr(_render, "CopyPromptContext"), (
        "CopyPromptContext 缺失(B4 契约:替代 meta dict 污染)"
    )
    ctx = _render.CopyPromptContext(
        mode="record-day",
        date="2026-07-15",
        total_minutes=120,
        records=[],
        summary_items=[],
        extra_data={},
    )
    assert ctx.mode == "record-day"
    assert ctx.date == "2026-07-15"
    assert ctx.total_minutes == 120


def test_build_record_copy_prompt_accepts_context():
    """_build_record_copy_prompt 接受 CopyPromptContext(B4 新签名)"""
    ctx = _render.CopyPromptContext(
        mode="record-day",
        date="2026-07-15",
        total_minutes=120,
        records=[{"activity": "测试", "category": "工作.AI调优"}],
        summary_items=[{"category": "工作.AI调优", "emoji": "🤖",
                        "total_minutes": 120, "pct": 100.0}],
        extra_data={"health": {"score": 85, "label": "充足"}},
    )
    prompt = _render._build_record_copy_prompt(ctx)
    assert "① 场景" in prompt
    assert "② 数据" in prompt
    assert "③ 期望" in prompt
    assert "④ 来源" in prompt
    assert "2026-07-15" in prompt
    assert "工作.AI调优" in prompt


def test_meta_no_longer_polluted_with_date_for_copy_prompt():
    """render_record_range 的 meta 不再仅为 copy_prompt 加 date(B4 修复)

    第一性:meta 是用户面向 payload,不应有为内部 helper 服务的字段。
    原 B4 发现:render_record_range/compare/category 为喂
    _build_record_copy_prompt 往 meta 加 date(原本 start/end 已含日期信息)。
    重构后:_build_record_copy_prompt 从 CopyPromptContext 拿 date,
    meta 保持原样(start/end/days 等用户面向字段),不再额外塞 date。

    注意:total_minutes 在 record-detail 是原 detail 模板的用户面向字段,
    不视为 B4 污染。date 在 record-range/category 是 B4 真正引入的污染,
    (start + end 已含同样信息,date 是冗余键)。
    """
    import schedule_db as _db
    _db.add_record_full(
        date="2026-07-15", time_start="10:00", time_end="11:00",
        duration_minutes=60, activity="测试", category="工作.AI调优",
        source_contents="x", source_timestamps="10:00",
        analysis_reasoning="y",
    )
    _db.add_record_full(
        date="2026-07-16", time_start="10:00", time_end="11:00",
        duration_minutes=60, activity="测试2", category="工作.AI调优",
        source_contents="x", source_timestamps="10:00",
        analysis_reasoning="y",
    )
    # record-range:不应有冗余 date(meta.start + meta.end 已含日期)
    payload = _render.render_record_range("2026-07-15", "2026-07-16")
    meta = payload["data"]["meta"]
    assert "date" not in meta, (
        f"record-range meta.date 应被移除(B4 修复:start/end 已冗余):{list(meta.keys())}"
    )
    assert "start" in meta and "end" in meta, "record-range 仍应保留 start/end"

    # record-category:不应有冗余 date(start + end 已含日期)
    payload = _render.render_record_category("工作", "2026-07-15", "2026-07-16")
    meta = payload["data"]["meta"]
    assert "date" not in meta, (
        f"record-category meta.date 应被移除(B4 修复:start/end 已冗余):{list(meta.keys())}"
    )

    # record-compare:不应有冗余 date(start_a + end_a 已含日期)
    payload = _render.render_record_compare(
        "A", "2026-07-15", "2026-07-15", "B", "2026-07-16", "2026-07-16")
    meta = payload["data"]["meta"]
    assert "date" not in meta, (
        f"record-compare meta.date 应被移除(B4 修复:start_a 已含日期):{list(meta.keys())}"
    )

    # copy_prompt 仍存在(行为不变)
    assert "copy_prompt" in payload["data"]
    assert "① 场景" in payload["data"]["copy_prompt"]


def test_behavior_unchanged_all_6_modes():
    """重构后 6 mode 仍生成 4 部分 prompt(行为回归)"""
    import schedule_db as _db
    for d in ["2026-07-13", "2026-07-14", "2026-07-15", "2026-07-16"]:
        _db.add_record_full(
            date=d, time_start="10:00", time_end="11:00",
            duration_minutes=60, activity=f"测试{d}", category="工作.AI调优",
            source_contents="x", source_timestamps="10:00",
            analysis_reasoning="y",
        )
    cases = [
        ("record-day",      _render.render_record_day("2026-07-15")),
        ("record-range",    _render.render_record_range("2026-07-15", "2026-07-16")),
        ("record-compare",  _render.render_record_compare(
            "A", "2026-07-15", "2026-07-15", "B", "2026-07-16", "2026-07-16")),
        ("record-category", _render.render_record_category("工作", "2026-07-15", "2026-07-16")),
        ("record-anomaly",  _render.render_record_anomaly(window_days=3)),
        ("record-detail",   _render.render_records_detail("2026-07-15")),
    ]
    for mode, payload in cases:
        assert payload["status"] == "ok", f"{mode} 渲染失败: {payload.get('message')}"
        cp = payload["data"].get("copy_prompt", "")
        assert "① 场景" in cp, f"{mode}: 缺 ① 场景"
        assert "② 数据" in cp, f"{mode}: 缺 ② 数据"
        assert "③ 期望" in cp, f"{mode}: 缺 ③ 期望"
        assert "④ 来源" in cp, f"{mode}: 缺 ④ 来源"
