"""T14 · 代码风格清理钉死测试。

剩余 sub-agent 命中 judgment call 项清理:
- cnCmd → commandToChinese(去缩写)
- MAX_DEFAULT 提顶层 const(脱离 appState)
- CMD_CN 映射 1-of-1 删除,改 inline (sync-from-feishu → 同步飞书)
- 新增测试文件末尾换行(PEP 8)
"""
import os
from pathlib import Path

import pytest

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


# ============================================================
# Mysterious Name cleanup
# ============================================================

class TestMysteriousNameCleanup:
    def test_sync_report_no_cnCmd_abbreviation(self):
        """cnCmd 缩写已重命名为 commandToChinese"""
        text = (TEMPLATES_DIR / "sync_report.html").read_text(encoding="utf-8")
        assert "cnCmd" not in text, (
            "cnCmd 缩写已弃用 · 改 commandToChinese"
        )

    def test_sync_report_has_commandToChinese(self):
        """commandToChinese 函数存在"""
        text = (TEMPLATES_DIR / "sync_report.html").read_text(encoding="utf-8")
        assert "commandToChinese" in text, (
            "commandToChinese 应存在 · 替 cnCmd"
        )

    def test_memo_query_no_MAX_DEFAULT_in_appState(self):
        """appState 不再含 MAX_DEFAULT · 提为顶层 const"""
        text = (TEMPLATES_DIR / "memo_query.html").read_text(encoding="utf-8")
        assert "MAX_DEFAULT:" not in text, (
            "appState.MAX_DEFAULT:50 应提为顶层 const MAX_DEFAULT"
        )

    def test_memo_query_has_top_level_const(self):
        """顶层 const MAX_DEFAULT = 50 存在"""
        import re
        text = (TEMPLATES_DIR / "memo_query.html").read_text(encoding="utf-8")
        m = re.search(r"const\s+MAX_DEFAULT\s*=\s*50", text)
        assert m, "顶层 const MAX_DEFAULT = 50 必须存在"


# ============================================================
# Speculative Generality cleanup
# ============================================================

class TestSpeculativeGeneralityCleanup:
    def test_sync_report_no_CMD_CN_object(self):
        """CMD_CN 单键对象已删除(避免 1-of-1 映射)"""
        text = (TEMPLATES_DIR / "sync_report.html").read_text(encoding="utf-8")
        assert "CMD_CN =" not in text, (
            "CMD_CN 单键映射对象已删除 · 改 inline 三元"
        )

    def test_sync_report_inline_chinese_alias(self):
        """inline 三元: sync-from-feishu → 同步飞书"""
        text = (TEMPLATES_DIR / "sync_report.html").read_text(encoding="utf-8")
        # 接受 inline 三元(命令字段直接条件映射)
        assert ("sync-from-feishu" in text
                and "同步飞书" in text), (
            "inline 映射: sync-from-feishu → 同步飞书"
        )


# ============================================================
# PEP 8 trailing newline
# ============================================================

class TestPEP8TrailingNewline:
    """新测试文件末尾应有单个换行符"""

    NEW_TEST_FILES = [
        "test_template_lint.py",
        "test_memo_query_decision4.py",
        "test_memo_query_visual.py",
        "test_wish_shared_fixes.py",
        "test_wish_visual_reverse.py",
        "test_wish_plan_fixes.py",
        "test_change_category_neutral.py",
        "test_sync_report_ui.py",
        "test_kpi_unified.py",
        "test_lint_zero_false_positive.py",
    ]

    @pytest.mark.parametrize("fname", NEW_TEST_FILES)
    def test_file_ends_with_single_newline(self, fname):
        path = Path(__file__).parent / fname
        assert path.exists(), f"{fname} 不存在"
        with open(path, "rb") as f:
            content = f.read()
        # 必须以 \n 结尾
        assert content.endswith(b"\n"), (
            f"{fname} 末尾必须以 \\n 结尾(PEP 8)"
        )
        # 不能以 \\n\\n 结尾(避免双重换行)
        assert not content.endswith(b"\n\n\n"), (
            f"{fname} 末尾不应超过 2 个连续换行"
        )