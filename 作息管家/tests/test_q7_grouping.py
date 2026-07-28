"""Q7 · ADR-0003 内部分组测试(Issue 10)

锁住:`_naming_path` 路径解析层有 4 域注释分组(record / plan / receipt / help),
为将来拆 schedule_cli.py 为 record_cli / plan_cli / receipt_cli / help_render 打基础。

触发重新评估拆模块的条件(ADR-0003):
1. schedule_cli.py 突破 150KB / 4000 行
2. _naming_path 内部逻辑已 100% 按域分组清晰
3. 用户明确要求拆分

Tested-By seam:
- 读 schedule_html_render.py 源码,检查 CN_COMMAND_MAP / default_output_path /
  record_output_path 都有 4 域注释分组
- schedule_cli.py 字节数 < 150KB / 行数 < 4000(避免触发拆模块条件)
"""
import sys
from pathlib import Path

# conftest.py 已经把 scripts/ 加入 sys.path,这里复用
SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import schedule_html_render as _render


def test_cn_command_map_has_4_domain_grouping():
    """CN_COMMAND_MAP 含 4 域注释分组(record / plan / receipt / help)"""
    src = (SCRIPTS_DIR / "schedule_html_render.py").read_text(encoding="utf-8")
    # CN_COMMAND_MAP 段:含 record / plan / receipt 3 域分组注释(help 域独立)
    cn_section = src[src.index("CN_COMMAND_MAP = {"):src.index("CN_COMMAND_MAP = {") + 1200]
    assert "# === record 域" in cn_section, "CN_COMMAND_MAP 缺 record 域分组注释"
    assert "# === plan 域" in cn_section, "CN_COMMAND_MAP 缺 plan 域分组注释"
    assert "# === receipt 域" in cn_section, "CN_COMMAND_MAP 缺 receipt 域分组注释"


def test_default_output_path_has_domain_grouping():
    """default_output_path 函数体含 plan / receipt 域分组注释(ADR-0003 Q7)"""
    src = (SCRIPTS_DIR / "schedule_html_render.py").read_text(encoding="utf-8")
    fn_start = src.index("def default_output_path(")
    fn_end = src.index("def record_output_path(", fn_start)
    fn_body = src[fn_start:fn_end]
    assert "# === plan 域" in fn_body or "# === plan 域(" in fn_body, (
        "default_output_path 缺 plan 域分组注释(ADR-0003 Q7)"
    )
    assert "# === receipt 域" in fn_body or "# === receipt 域(" in fn_body, (
        "default_output_path 缺 receipt 域分组注释(ADR-0003 Q7)"
    )


def test_record_output_path_has_domain_grouping():
    """record_output_path 函数体含 record / receipt 域分组注释(ADR-0003 Q7)"""
    src = (SCRIPTS_DIR / "schedule_html_render.py").read_text(encoding="utf-8")
    fn_start = src.index("def record_output_path(")
    fn_end = src.index("def title_for_mode(", fn_start)
    fn_body = src[fn_start:fn_end]
    assert "# === record 域" in fn_body or "# === record 域(" in fn_body, (
        "record_output_path 缺 record 域分组注释(ADR-0003 Q7)"
    )
    assert "# === receipt 域" in fn_body or "# === receipt 域(" in fn_body, (
        "record_output_path 缺 receipt 域分组注释(ADR-0003 Q7)"
    )


def test_schedule_cli_below_split_threshold():
    """schedule_cli.py 字节数 < 150KB / 行数 < 4000(ADR-0003 触发条件未满足)"""
    cli_path = SCRIPTS_DIR / "schedule_cli.py"
    size_bytes = cli_path.stat().st_size
    line_count = len(cli_path.read_text(encoding="utf-8").splitlines())
    assert size_bytes < 150 * 1024, (
        f"schedule_cli.py 已达 {size_bytes // 1024} KB ≥ 150 KB,"
        f"ADR-0003 触发条件满足,应重新评估拆模块"
    )
    assert line_count < 4000, (
        f"schedule_cli.py 已达 {line_count} 行 ≥ 4000 行,"
        f"ADR-0003 触发条件满足,应重新评估拆模块"
    )


def test_4_domains_documented_in_cn_command_map_docstring():
    """CN_COMMAND_MAP 顶部注释含 4 域声明(为拆模块做准备)"""
    src = (SCRIPTS_DIR / "schedule_html_render.py").read_text(encoding="utf-8")
    # 找 CN_COMMAND_MAP 前 800 字符的注释块
    idx = src.index("CN_COMMAND_MAP = {")
    comment_block = src[max(0, idx - 800):idx]
    assert "record 域" in comment_block, "CN_COMMAND_MAP 顶部缺 record 域声明"
    assert "plan 域" in comment_block, "CN_COMMAND_MAP 顶部缺 plan 域声明"
    assert "receipt 域" in comment_block, "CN_COMMAND_MAP 顶部缺 receipt 域声明"
    assert "help 域" in comment_block, "CN_COMMAND_MAP 顶部缺 help 域声明"
