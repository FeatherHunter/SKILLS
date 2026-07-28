"""HTML 输出文件命名合规测试(手册 §4.1)

锁住 <command>_<YYYYMMDD>_<HHMMSS>[_<N>].html 格式 + 冲突保护。
注意:schedule_db 函数不接 conn 参数,靠 conftest.py monkeypatch 路由。
"""
import os
import re
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import schedule_html_render as _render


# 命名合规正则(ADR-0002 Q5 · 总纲 §04 原则 12.A)
# 支持中文 / 字母 / 下划线 command 名 + _YYYYMMDD_HHMMSS[_N].html
NAMING_RE = re.compile(r"^[\u4e00-\u9fffa-zA-Z_]+_\d{8}_\d{6}(_\d+)?\.html$")


def test_naming_basic_format(tmp_path, monkeypatch):
    """_naming_path 生成 <中文 command>_<YYYYMMDD>_<HHMMSS>.html(ADR-0002 Q5)"""
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    p = _render._naming_path("查作息记录", "record/day")
    assert NAMING_RE.match(p.name), f"格式不合法:{p.name}"
    assert p.name.startswith("查作息记录_")
    # 父目录自动创建
    assert p.parent.exists()
    assert p.parent.name == "day"


def test_naming_no_subdir(tmp_path, monkeypatch):
    """_naming_path 不传 subdir → 直接放在 _html_base_dir 下(自定义 command)"""
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    p = _render._naming_path("custom_test_cmd")
    assert NAMING_RE.match(p.name)
    # 父目录是 schedule_html(顶层)
    assert p.parent.name == "schedule_html"


def test_naming_collision_protection(tmp_path, monkeypatch):
    """同秒第二次 → 文件名追加 _2(中文 command 也要冲突保护)"""
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    p1 = _render._naming_path("记作息回执", "record/receipt")
    p1.write_text("first", encoding="utf-8")
    p2 = _render._naming_path("记作息回执", "record/receipt")
    assert p2 != p1
    assert p2.name.endswith("_2.html"), f"应追加 _2,实际:{p2.name}"
    # 二次写入 p2 不影响 p1
    p2.write_text("second", encoding="utf-8")
    assert p1.read_text() == "first"


def test_naming_three_collision(tmp_path, monkeypatch):
    """同秒第三次 → _3(连续递增 · 中文 command 也要冲突保护)"""
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    paths = []
    for _ in range(3):
        p = _render._naming_path("改日程回执", "plan/receipt")
        p.write_text("x", encoding="utf-8")
        paths.append(p.name)
    assert paths[0].endswith(".html")
    assert paths[1].endswith("_2.html")
    assert paths[2].endswith("_3.html")


def test_record_output_path_all_modes(tmp_path, monkeypatch):
    """record_output_path 9 个 mode 全部生成合规命名(ADR-0002 Q5 · 中文 command)"""
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    # (mode, subdir, 中文 command 名)
    modes = [
        ("record-day", "record/day", "查作息记录"),
        ("record-range", "record/range", "查作息区间"),
        ("record-compare", "record/compare", "查作息对比"),
        ("record-category", "record/category", "查作息类别"),
        ("record-anomaly", "record/anomaly", "查作息异常"),
        ("record-report", "record/day", "查作息记录"),  # 兼容旧 CLI,等价 record-day
        ("record-receipt", "record/receipt", "记作息回执"),
        ("plan-receipt", "plan/receipt", "改日程回执"),
        ("record-detail", "record/detail", "作息详情"),
    ]
    for mode, subdir, command in modes:
        p = _render.record_output_path(mode, {"date": "2026-07-15"})
        assert p.parent.name == subdir.split("/")[-1], f"{mode}: subdir 错"
        assert NAMING_RE.match(p.name), f"{mode}: 命名错 {p.name}"
        assert p.name.startswith(command + "_"), f"{mode}: command 错 {p.name}"


def test_default_output_path_plan_modes(tmp_path, monkeypatch):
    """default_output_path 7 个 plan-* mode 全部生成合规命名(ADR-0002 Q5 · 中文 command)"""
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    # (mode, meta, 中文 command 名, subdir)
    modes_meta = [
        ("list-events", {"date": "2026-07-15"}, "查日程", "plan/list"),
        ("query-plans", {"dates": ["2026-07-15", "2026-07-16"]}, "查日程", "plan/query"),
        ("plan-preview", {"date": "2026-07-15"}, "商量计划预览", "plan/list"),
        ("plan-review", {"date": "2026-07-15"}, "复盘", "plan/list"),
        ("plan-receipt", {"plan_id": 5, "action": "update"}, "改日程回执", "plan/receipt"),
        ("plan-receipt-add", {"plan_id": 5}, "补日程回执", "plan/receipt"),
        ("plan-receipt-write", {"plan_id": 5}, "写日程回执", "plan/receipt"),
    ]
    for mode, meta, command, subdir in modes_meta:
        meta_with_mode = {"mode": mode, **meta}
        p = _render.default_output_path(meta_with_mode)
        assert NAMING_RE.match(p.name), f"{mode}: 命名错 {p.name}"
        assert p.name.startswith(command + "_"), f"{mode}: command 错 {p.name}"
        assert subdir.replace("/", "").endswith(p.parent.name) or \
            p.parent.parent.name + "/" + p.parent.name == subdir, \
            f"{mode}: subdir 错 {p.parent}"


def test_filename_no_pid_rid_leak(tmp_path, monkeypatch):
    """filename 不再携带 pid/rid/action/date(语义信息保留在 payload meta 里)"""
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    # record-receipt: 不再含 rid
    p = _render.record_output_path("record-receipt", {"record_id": 99999})
    assert "99999" not in p.name, f"rid 应不在 filename 里:{p.name}"
    # plan-receipt: 不再含 pid
    p = _render.default_output_path({
        "mode": "plan-receipt", "plan_id": 99999, "action": "deactivate"
    })
    assert "99999" not in p.name, f"pid 应不在 filename 里:{p.name}"
    assert "deactivate" not in p.name, f"action 应不在 filename 里:{p.name}"