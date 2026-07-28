"""Q5 路径对齐 · 中文 command 名测试(ADR-0002 · 总纲 §04 原则 12.A)

锁住:
- _naming_path 接受中文 command 名(查作息记录 / 查日程 / 复盘 等)
- 输出文件名格式:`<中文 command>_<YYYYMMDD>_<HHMMSS>[_<N>].html`
- 中文 command 名与英文 command 名都能工作(Issue 02 expand 阶段保留英文 fallback)
- 子目录结构(record/day, plan/list 等)保持不变

Tested-By seam:
- 调 _naming_path("查作息记录", "record/day") 观察返回 Path
- 文件名 / 父目录 / 冲突保护 _2/_3

中文 command 名映射(15 模板 · ADR-0002 Q5):
    record 域:
      record_day → 查作息记录
      record_range → 查作息区间
      record_compare → 查作息对比
      record_category → 查作息类别
      record_anomaly → 查作息异常
      record_detail → 作息详情
      record_receipt → 记作息回执
      record_receipt_edit → 修正作息回执
    plan 域:
      plan_list → 查日程
      plan_receipt → 改日程回执
      plan_receipt_add → 补日程回执
      plan_receipt_write → 写日程回执
      plan_preview → 商量计划预览
      plan_review → 复盘
"""
import re
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import schedule_html_render as _render


# 中文 command 名命名合规正则(总纲 §04 原则 12.A)
# 允许:中文 / 字母 / 下划线 + _YYYYMMDD_HHMMSS[_N].html
CN_NAMING_RE = re.compile(r"^[\u4e00-\u9fffa-zA-Z_]+_\d{8}_\d{6}(_\d+)?\.html$")


def test_naming_path_accepts_chinese_command(tmp_path, monkeypatch):
    """_naming_path 接受中文 command 名,生成 `<中文>_<TS>.html`"""
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    p = _render._naming_path("查作息记录", "record/day")
    assert CN_NAMING_RE.match(p.name), f"中文命名不合法:{p.name}"
    assert p.name.startswith("查作息记录_"), f"应以中文 command 开头:{p.name}"
    assert p.parent.name == "day"
    assert p.parent.parent.name == "record"


def test_naming_path_chinese_collision_protection(tmp_path, monkeypatch):
    """中文 command 同秒冲突 _2/_3 保护"""
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    p1 = _render._naming_path("复盘", "plan/list")
    p1.write_text("first", encoding="utf-8")
    p2 = _render._naming_path("复盘", "plan/list")
    assert p2 != p1
    assert p2.name.endswith("_2.html"), f"应追加 _2,实际:{p2.name}"


def test_naming_path_english_still_works(tmp_path, monkeypatch):
    """Issue 07 contract:在 CN_COMMAND_MAP 里的英文 command 名应抛 ValueError,
    提示改用中文;不在映射里的自定义 command 仍允许(测试场景 / unknown 兜底)。

    Issue 02 阶段曾允许英文 fallback,Issue 07 contract 之后强制删 fallback,
    防止 caller 忘记映射产生旧英文命名残留。
    """
    import pytest
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    # 在 CN_COMMAND_MAP 里的英文 command → 现在应抛 ValueError
    with pytest.raises(ValueError, match="record_day"):
        _render._naming_path("record_day", "record/day")
    # 不在映射里的自定义 command 仍允许(测试场景 / unknown 兜底)
    p = _render._naming_path("custom_test_cmd", "test/sub")
    legacy_re = re.compile(r"^[a-z_]+_\d{8}_\d{6}(_\d+)?\.html$")
    assert legacy_re.match(p.name)
    assert p.name.startswith("custom_test_cmd_")


# ===== 15 模板中文 command 映射契约(ADR-0002 Q5)=====

EXPECTED_CN_COMMANDS = {
    # record 域(8)
    "查作息记录", "查作息区间", "查作息对比", "查作息类别",
    "查作息异常", "作息详情", "记作息回执", "修正作息回执",
    # plan 域(6)
    "查日程", "改日程回执", "补日程回执", "写日程回执",
    "商量计划预览", "复盘",
}


def test_naming_path_all_15_chinese_commands(tmp_path, monkeypatch):
    """全部 15 个中文 command 名都能被 _naming_path 接受并生成合规路径"""
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    subdirs = {
        "查作息记录": "record/day",
        "查作息区间": "record/range",
        "查作息对比": "record/compare",
        "查作息类别": "record/category",
        "查作息异常": "record/anomaly",
        "作息详情": "record/detail",
        "记作息回执": "record/receipt",
        "修正作息回执": "record/receipt",
        "查日程": "plan/list",
        "改日程回执": "plan/receipt",
        "补日程回执": "plan/receipt",
        "写日程回执": "plan/receipt",
        "商量计划预览": "plan/list",
        "复盘": "plan/list",
    }
    for cn_cmd, subdir in subdirs.items():
        p = _render._naming_path(cn_cmd, subdir)
        assert CN_NAMING_RE.match(p.name), f"{cn_cmd}: 命名不合规 {p.name}"
        assert p.name.startswith(cn_cmd + "_"), f"{cn_cmd}: 不以中文 command 开头"
        assert p.parent.exists(), f"{cn_cmd}: 父目录未创建"


# ===== 中文 command 映射表存在性测试(Issue 02 expand 关键产物)=====

def test_chinese_command_map_exists():
    """schedule_html_render 暴露 CN_COMMAND_MAP 字典(英文 → 中文映射)"""
    assert hasattr(_render, "CN_COMMAND_MAP"), (
        "schedule_html_render.CN_COMMAND_MAP 缺失(Issue 02 契约)"
    )
    m = _render.CN_COMMAND_MAP
    # 至少覆盖 14 个 record/plan 域 command(help 域已对齐,不需在此映射)
    assert len(m) >= 14, f"CN_COMMAND_MAP 至少 14 项,实际 {len(m)}"
    # 关键映射存在
    assert m.get("record_day") == "查作息记录"
    assert m.get("plan_list") == "查日程"
    assert m.get("plan_review") == "复盘"
    assert m.get("record_receipt_edit") == "修正作息回执"
