"""Q5 路径对齐迁移测试(ADR-0002 · Issue 03/04/05/06)

锁住:
- default_output_path / record_output_path 输出文件名使用中文 command 名
- record 域 6 模板、plan 域 5 模板、receipt 域 2 模板、list-events 1 模板
- 子目录结构不变(record/day, plan/list, record/receipt 等)
- 命名格式:`<中文 command>_<YYYYMMDD>_<HHMMSS>[_<N>].html`

中文 command 映射(15 模板):
    record 域(8):
      record_day → 查作息记录      record_range → 查作息区间
      record_compare → 查作息对比   record_category → 查作息类别
      record_anomaly → 查作息异常    record_detail → 作息详情
      record_receipt → 记作息回执    record_receipt_edit → 修正作息回执
    plan 域(6):
      plan_list → 查日程           plan_receipt → 改日程回执
      plan_receipt_add → 补日程回执 plan_receipt_write → 写日程回执
      plan_preview → 商量计划预览   plan_review → 复盘
"""
import re
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import schedule_html_render as _render


CN_NAMING_RE = re.compile(r"^[\u4e00-\u9fffa-zA-Z_]+_\d{8}_\d{6}(_\d+)?\.html$")


# ===== Issue 03 · record 域 6 模板(报告型)=====

def test_record_day_uses_chinese_command(tmp_path, monkeypatch):
    """record-day 模式 → 文件名 查作息记录_<TS>.html"""
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    p = _render.record_output_path("record-day", {"date": "2026-07-15"})
    assert p.name.startswith("查作息记录_"), f"应中文 command,实际:{p.name}"
    assert CN_NAMING_RE.match(p.name)
    assert p.parent.name == "day"
    assert p.parent.parent.name == "record"


def test_record_range_uses_chinese_command(tmp_path, monkeypatch):
    """record-range → 查作息区间_<TS>.html"""
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    p = _render.record_output_path("record-range", {"date": "2026-07-15"})
    assert p.name.startswith("查作息区间_"), f"应中文 command,实际:{p.name}"
    assert CN_NAMING_RE.match(p.name)
    assert p.parent.name == "range"


def test_record_compare_uses_chinese_command(tmp_path, monkeypatch):
    """record-compare → 查作息对比_<TS>.html"""
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    p = _render.record_output_path("record-compare")
    assert p.name.startswith("查作息对比_"), f"应中文 command,实际:{p.name}"
    assert CN_NAMING_RE.match(p.name)
    assert p.parent.name == "compare"


def test_record_category_uses_chinese_command(tmp_path, monkeypatch):
    """record-category → 查作息类别_<TS>.html"""
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    p = _render.record_output_path("record-category")
    assert p.name.startswith("查作息类别_"), f"应中文 command,实际:{p.name}"
    assert CN_NAMING_RE.match(p.name)
    assert p.parent.name == "category"


def test_record_anomaly_uses_chinese_command(tmp_path, monkeypatch):
    """record-anomaly → 查作息异常_<TS>.html"""
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    p = _render.record_output_path("record-anomaly")
    assert p.name.startswith("查作息异常_"), f"应中文 command,实际:{p.name}"
    assert CN_NAMING_RE.match(p.name)
    assert p.parent.name == "anomaly"


def test_record_report_alias_uses_chinese_command(tmp_path, monkeypatch):
    """record-report(兼容旧 CLI)→ 查作息记录_<TS>.html(等价 record-day)"""
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    p = _render.record_output_path("record-report")
    assert p.name.startswith("查作息记录_"), f"应中文 command,实际:{p.name}"
    assert CN_NAMING_RE.match(p.name)


def test_record_detail_uses_chinese_command(tmp_path, monkeypatch):
    """record-detail → 作息详情_<TS>.html"""
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    p = _render.record_output_path("record-detail")
    assert p.name.startswith("作息详情_"), f"应中文 command,实际:{p.name}"
    assert CN_NAMING_RE.match(p.name)
    assert p.parent.name == "detail"


# ===== Issue 04 · plan 域 5 模板(过程型 / 回执型)=====

def test_plan_list_uses_chinese_command(tmp_path, monkeypatch):
    """list-events mode → 查日程_<TS>.html(对应"查日程"/"看日程"唤醒词)"""
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    p = _render.default_output_path({"mode": "list-events", "date": "2026-07-15"})
    assert p.name.startswith("查日程_"), f"应中文 command,实际:{p.name}"
    assert CN_NAMING_RE.match(p.name)
    assert p.parent.name == "list"


def test_plan_preview_uses_chinese_command(tmp_path, monkeypatch):
    """plan-preview → 商量计划预览_<TS>.html"""
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    p = _render.default_output_path({"mode": "plan-preview", "date": "2026-07-15"})
    assert p.name.startswith("商量计划预览_"), f"应中文 command,实际:{p.name}"
    assert CN_NAMING_RE.match(p.name)
    assert p.parent.name == "list"


def test_plan_review_uses_chinese_command(tmp_path, monkeypatch):
    """plan-review → 复盘_<TS>.html"""
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    p = _render.default_output_path({"mode": "plan-review", "date": "2026-07-15"})
    assert p.name.startswith("复盘_"), f"应中文 command,实际:{p.name}"
    assert CN_NAMING_RE.match(p.name)
    assert p.parent.name == "list"


def test_plan_receipt_uses_chinese_command(tmp_path, monkeypatch):
    """plan-receipt → 改日程回执_<TS>.html"""
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    p = _render.default_output_path({"mode": "plan-receipt", "plan_id": 5, "action": "update"})
    assert p.name.startswith("改日程回执_"), f"应中文 command,实际:{p.name}"
    assert CN_NAMING_RE.match(p.name)
    assert p.parent.name == "receipt"
    assert p.parent.parent.name == "plan"


def test_plan_receipt_add_uses_chinese_command(tmp_path, monkeypatch):
    """plan-receipt-add → 补日程回执_<TS>.html"""
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    p = _render.default_output_path({"mode": "plan-receipt-add", "plan_id": 5})
    assert p.name.startswith("补日程回执_"), f"应中文 command,实际:{p.name}"
    assert CN_NAMING_RE.match(p.name)


def test_plan_receipt_write_uses_chinese_command(tmp_path, monkeypatch):
    """plan-receipt-write → 写日程回执_<TS>.html"""
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    p = _render.default_output_path({"mode": "plan-receipt-write", "plan_id": 5})
    assert p.name.startswith("写日程回执_"), f"应中文 command,实际:{p.name}"
    assert CN_NAMING_RE.match(p.name)


# ===== Issue 05 · receipt 域 2 模板(record_receipt / record_receipt_edit)=====

def test_record_receipt_uses_chinese_command(tmp_path, monkeypatch):
    """record-receipt → 记作息回执_<TS>.html"""
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    p = _render.record_output_path("record-receipt", {"record_id": 42})
    assert p.name.startswith("记作息回执_"), f"应中文 command,实际:{p.name}"
    assert CN_NAMING_RE.match(p.name)
    assert p.parent.name == "receipt"
    assert p.parent.parent.name == "record"


def test_record_receipt_edit_uses_chinese_command(tmp_path, monkeypatch):
    """record-receipt-edit → 修正作息回执_<TS>.html"""
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    p = _render.record_output_path("record-receipt-edit", {"record_id": 42})
    assert p.name.startswith("修正作息回执_"), f"应中文 command,实际:{p.name}"
    assert CN_NAMING_RE.match(p.name)


# ===== Issue 06 · list-events 走 查日程 命名(同 Issue 04 第 1 测试,这里独立断言)=====
# 已在 test_plan_list_uses_chinese_command 中覆盖


# ===== 综合:14 模板全部中文 command(不含 help 域)=====

def test_all_14_modes_use_chinese_command(tmp_path, monkeypatch):
    """全部 14 个 mode 都生成中文 command 文件名(Issue 03-06 综合)"""
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    record_modes = [
        ("record-day", "查作息记录"),
        ("record-range", "查作息区间"),
        ("record-compare", "查作息对比"),
        ("record-category", "查作息类别"),
        ("record-anomaly", "查作息异常"),
        ("record-report", "查作息记录"),   # 兼容旧 CLI
        ("record-detail", "作息详情"),
        ("record-receipt", "记作息回执"),
        ("record-receipt-edit", "修正作息回执"),
        ("plan-receipt", "改日程回执"),
    ]
    for mode, expected_cn in record_modes:
        p = _render.record_output_path(mode)
        assert p.name.startswith(expected_cn + "_"), (
            f"{mode}: 应以 {expected_cn}_ 开头,实际 {p.name}"
        )

    plan_modes = [
        ("list-events", "查日程"),
        ("plan-preview", "商量计划预览"),
        ("plan-review", "复盘"),
        ("plan-receipt", "改日程回执"),
        ("plan-receipt-add", "补日程回执"),
        ("plan-receipt-write", "写日程回执"),
    ]
    for mode, expected_cn in plan_modes:
        p = _render.default_output_path({"mode": mode})
        assert p.name.startswith(expected_cn + "_"), (
            f"{mode}: 应以 {expected_cn}_ 开头,实际 {p.name}"
        )


# ===== 隐私信息不进 filename(回归)=====

def test_filename_still_no_pid_rid_leak(tmp_path, monkeypatch):
    """迁移后仍保持:filename 不携带 pid/rid/action/date"""
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    p = _render.record_output_path("record-receipt", {"record_id": 99999})
    assert "99999" not in p.name
    p = _render.default_output_path({
        "mode": "plan-receipt", "plan_id": 99999, "action": "deactivate"
    })
    assert "99999" not in p.name
    assert "deactivate" not in p.name
