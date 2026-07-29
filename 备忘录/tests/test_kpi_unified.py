"""T12 · 6 模板 KPI 字号统一 钉死测试。

spec C7:6 模板统一 KPI 字号比(数字 / label ≤ 1.8)
- 数字:22px(从 sync_report 28px / wish_* 26px 降至 22px)
- label:≥13px(wish_* / change_category 当前 13px,合规)
- 视觉权重平衡(US18 一致性)
"""
import re
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"

# 支持的 KPI 选择器形态:
#  .stat b{font-size:NNpx}
#  .kpi-num{font-size:NNpx}
#  .kpi b{font-size:NNpx}
#  .kpi .stat b{font-size:NNpx}
#  .stat span{font-size:NNpx} (label)
KPI_NUM_PATTERNS = [
    re.compile(r"\.stat\s+b\s*\{[^}]*font-size:\s*(\d+)px", re.DOTALL),
    re.compile(r"\.kpi-num\s*\{[^}]*font-size:\s*(\d+)px", re.DOTALL),
    re.compile(r"\.kpi\s+b\s*\{[^}]*font-size:\s*(\d+)px", re.DOTALL),
]
KPI_LABEL_PATTERNS = [
    re.compile(r"\.stat\s+span\s*\{[^}]*font-size:\s*(\d+)px", re.DOTALL),
    re.compile(r"\.kpi-label\s*\{[^}]*font-size:\s*(\d+)px", re.DOTALL),
    re.compile(r"\.kpi\s+span\s*\{[^}]*font-size:\s*(\d+)px", re.DOTALL),
]


def _kpi_num_px(template_text):
    for p in KPI_NUM_PATTERNS:
        m = p.search(template_text)
        if m:
            return int(m.group(1))
    return None


def _kpi_label_px(template_text):
    for p in KPI_LABEL_PATTERNS:
        m = p.search(template_text)
        if m:
            return int(m.group(1))
    return None


# ============================================================
# KPI 数字 ≤ 22px
# ============================================================

class TestKpiNumericUnified:
    """所有 KPI 数字字号 ≤ 22px(spec C7·US18·总纲原则 8 克制)"""

    FILES_WITH_KPI = [
        "memo_query.html",
        "sync_report.html",
        "wish_plan.html",
        "wish_complete.html",
        "change_category.html",
    ]

    def test_memo_query_kpi_num_22(self):
        text = (TEMPLATES_DIR / "memo_query.html").read_text(encoding="utf-8")
        size = _kpi_num_px(text)
        assert size is not None, "memo_query 应有 .stat b 字号定义"
        assert size <= 22, f"memo_query KPI 数字 {size}px 超 22 上限"

    def test_sync_report_kpi_num_22(self):
        text = (TEMPLATES_DIR / "sync_report.html").read_text(encoding="utf-8")
        size = _kpi_num_px(text)
        assert size is not None, "sync_report 应有 .kpi-num 字号定义"
        assert size <= 22, f"sync_report KPI 数字 {size}px 超 22 上限(原 28)"

    def test_wish_plan_kpi_num_22(self):
        text = (TEMPLATES_DIR / "wish_plan.html").read_text(encoding="utf-8")
        size = _kpi_num_px(text)
        assert size is not None, "wish_plan 应有 .kpi b / .stat b 字号定义"
        assert size <= 22, f"wish_plan KPI 数字 {size}px 超 22 上限(原 26)"

    def test_wish_complete_kpi_num_22(self):
        text = (TEMPLATES_DIR / "wish_complete.html").read_text(encoding="utf-8")
        size = _kpi_num_px(text)
        assert size is not None, "wish_complete 应有 .kpi b / .stat b 字号定义"
        assert size <= 22, f"wish_complete KPI 数字 {size}px 超 22 上限(原 26)"

    def test_change_category_kpi_num_22(self):
        text = (TEMPLATES_DIR / "change_category.html").read_text(encoding="utf-8")
        size = _kpi_num_px(text)
        assert size is not None, "change_category 应有 .kpi b / .stat b 字号定义"
        assert size <= 22, f"change_category KPI 数字 {size}px 超 22 上限(原 26)"


# ============================================================
# KPI label ≥ 13px
# ============================================================

class TestKpiLabelUnified:
    FILES_WITH_KPI = [
        "memo_query.html",
        "sync_report.html",
        "wish_plan.html",
        "wish_complete.html",
        "change_category.html",
    ]

    def test_memo_query_kpi_label_geq_13(self):
        text = (TEMPLATES_DIR / "memo_query.html").read_text(encoding="utf-8")
        size = _kpi_label_px(text)
        assert size is not None
        assert size >= 13, f"memo_query KPI label {size}px 不足 13 下限"

    def test_sync_report_kpi_label_geq_13(self):
        text = (TEMPLATES_DIR / "sync_report.html").read_text(encoding="utf-8")
        size = _kpi_label_px(text)
        assert size is not None, "sync_report 应有 .kpi-label"
        assert size >= 13, f"sync_report KPI label {size}px 不足 13 下限"

    def test_wish_plan_kpi_label_geq_13(self):
        text = (TEMPLATES_DIR / "wish_plan.html").read_text(encoding="utf-8")
        size = _kpi_label_px(text)
        assert size is not None, "wish_plan 应有 .kpi span"
        assert size >= 13, f"wish_plan KPI label {size}px 不足 13 下限"

    def test_wish_complete_kpi_label_geq_13(self):
        text = (TEMPLATES_DIR / "wish_complete.html").read_text(encoding="utf-8")
        size = _kpi_label_px(text)
        assert size is not None, "wish_complete 应有 .kpi span"
        assert size >= 13, f"wish_complete KPI label {size}px 不足 13 下限"

    def test_change_category_kpi_label_geq_13(self):
        text = (TEMPLATES_DIR / "change_category.html").read_text(encoding="utf-8")
        size = _kpi_label_px(text)
        assert size is not None, "change_category 应有 .kpi span"
        assert size >= 13, f"change_category KPI label {size}px 不足 13 下限"


# ============================================================
# 数字 / label 比例 ≤ 1.8(视觉权重平衡)
# ============================================================

class TestKpiVisualRatio:
    def test_ratios_all_within_1_8(self):
        """所有模板数字 / label ≤ 1.8(spec C7)"""
        files = TestKpiNumericUnified.FILES_WITH_KPI
        bad = []
        for name in files:
            text = (TEMPLATES_DIR / name).read_text(encoding="utf-8")
            num = _kpi_num_px(text)
            lbl = _kpi_label_px(text)
            if num is None or lbl is None or lbl == 0:
                continue
            ratio = num / lbl
            if ratio > 1.8:
                bad.append(f"{name}: {num}px / {lbl}px = {ratio:.2f}")
        assert not bad, f"KPI 数字/label 比例超过 1.8:\n  " + "\n  ".join(bad)
