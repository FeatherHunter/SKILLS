"""validators.py 单元测试 — §02 第 ③ 规则层

覆盖 4 类异常 + 2 类正常 + 错误信息四要素（字段名 + 当前值 + 期望值 + 怎么修）。

依据 spec.md §02 §Testing Decisions #2:
  - validate_amount(-35) 通过 / validate_amount(0) 拒绝 /
    validate_amount(float('nan')) 拒绝
  - validate_category("餐饮/外卖/午餐") 通过 / validate_category("不存在") 拒绝
  - validate_record 综合校验：金额 0 + 分类合法 + 时间格式错等组合
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


# ── 1. validate_amount ──────────────────────────────────────────────────────

class TestValidateAmount:
    """金额校验：非零 + 有限数（NaN / Inf 拒绝）"""

    def test_negative_expense_passes(self):
        from validators import validate_amount
        assert validate_amount(-35.0) == -35.0

    def test_positive_income_passes(self):
        from validators import validate_amount
        assert validate_amount(8000.0) == 8000.0

    def test_decimal_passes(self):
        from validators import validate_amount
        assert validate_amount(35.55) == 35.55

    def test_zero_rejected(self):
        from validators import ValidationError, validate_amount
        with pytest.raises(ValidationError) as ei:
            validate_amount(0.0)
        msg = str(ei.value)
        # 四要素
        assert "amount" in msg.lower() or "金额" in msg
        assert "0" in msg
        assert "非零" in msg or "不能为零" in msg or "!= 0" in msg

    def test_nan_rejected(self):
        from validators import ValidationError, validate_amount
        with pytest.raises(ValidationError) as ei:
            validate_amount(float("nan"))
        msg = str(ei.value)
        assert "amount" in msg.lower() or "金额" in msg
        assert "nan" in msg.lower()

    def test_inf_rejected(self):
        from validators import ValidationError, validate_amount
        with pytest.raises(ValidationError):
            validate_amount(float("inf"))
        with pytest.raises(ValidationError):
            validate_amount(float("-inf"))

    def test_error_message_contains_four_elements(self):
        """错误信息含「字段名 + 当前值 + 期望值 + 怎么修」四要素"""
        from validators import ValidationError, validate_amount
        with pytest.raises(ValidationError) as ei:
            validate_amount(0.0)
        msg = str(ei.value)
        # 字段名
        assert "amount" in msg.lower() or "金额" in msg
        # 当前值
        assert "0" in msg
        # 期望值（非零 / 非零有限数）
        assert "非零" in msg or "不能为零" in msg or "!= 0" in msg
        # 怎么修（提示用非零金额 / 输入有效金额）
        assert "改" in msg or "输入" in msg or "提供" in msg or "建议" in msg


# ── 2. validate_category ────────────────────────────────────────────────────

class TestValidateCategory:
    """分类校验：L1 在白名单 + 多级（L1/L2/L3）合法"""

    def test_l1_expense_passes(self):
        from validators import validate_category
        assert validate_category("餐饮") == "餐饮"
        assert validate_category("其他") == "其他"

    def test_multilevel_passes(self):
        from validators import validate_category
        assert validate_category("餐饮/外卖/午餐") == "餐饮/外卖/午餐"
        assert validate_category("出行/网约车") == "出行/网约车"

    def test_all_10_expense_l1_pass(self):
        """10 个支出 L1 全部通过"""
        from validators import validate_category
        for c in ["餐饮", "居家", "穿着", "出行", "玩乐",
                  "学习", "健康", "社交", "宠物", "其他"]:
            assert validate_category(c) == c

    def test_all_5_income_l1_pass(self):
        """5 个收入 L1 全部通过"""
        from validators import validate_category
        for c in ["工资", "奖金", "兼职", "投资", "其他收入"]:
            assert validate_category(c) == c

    def test_unknown_category_rejected(self):
        from validators import ValidationError, validate_category
        with pytest.raises(ValidationError) as ei:
            validate_category("不存在")
        msg = str(ei.value)
        assert "category" in msg.lower() or "分类" in msg
        assert "不存在" in msg
        # 期望值：在白名单中
        assert "餐饮" in msg  # 白名单示例出现在错误信息

    def test_empty_category_rejected(self):
        from validators import ValidationError, validate_category
        with pytest.raises(ValidationError):
            validate_category("")
        with pytest.raises(ValidationError):
            validate_category(None)

    def test_legacy_short_category_passes(self):
        """旧数据 '交通' 这种历史短名（不在当前白名单）的兼容性边界

        按 categories.md §数据兼容：旧数据不带 / 的视为 L1。
        但 '交通' 在 v3.1 已改为 '出行'，所以应当拒绝。
        本测试 pin 住：旧名（交通/购物/娱乐/医疗/住房/教育/通讯）都应拒绝，
        因为它们不在当前 categories.md 白名单中。
        """
        from validators import ValidationError, validate_category
        for legacy in ["交通", "购物", "娱乐", "医疗", "住房", "教育", "通讯"]:
            with pytest.raises(ValidationError):
                validate_category(legacy)


# ── 3. validate_record（综合） ──────────────────────────────────────────────

class TestValidateRecord:
    """完整记录校验：amount + category + time + 可选字段类型"""

    def test_valid_expense_record_passes(self):
        from validators import validate_record
        rec = {
            "category": "餐饮/外卖/午餐",
            "amount": -35.0,
            "time": "2026-07-28 12:00:00",
            "account": "支付宝",
            "ledger": "生活",
            "currency": "人民币",
            "note": "午饭",
        }
        validated = validate_record(rec)
        assert validated["amount"] == -35.0
        assert validated["category"] == "餐饮/外卖/午餐"

    def test_valid_income_record_passes(self):
        from validators import validate_record
        rec = {
            "category": "工资/基本工资",
            "amount": 8000.0,
            "time": "2026-07-28 09:00:00",
        }
        validated = validate_record(rec)
        assert validated["amount"] == 8000.0

    def test_zero_amount_rejected(self):
        from validators import ValidationError, validate_record
        rec = {
            "category": "餐饮",
            "amount": 0.0,
            "time": "2026-07-28 12:00:00",
        }
        with pytest.raises(ValidationError):
            validate_record(rec)

    def test_bad_time_format_rejected(self):
        """时间格式非 YYYY-MM-DD HH:MM:SS 拒绝"""
        from validators import ValidationError, validate_record
        rec = {
            "category": "餐饮",
            "amount": -35.0,
            "time": "2026/07/28 12:00",  # 错误格式
        }
        with pytest.raises(ValidationError) as ei:
            validate_record(rec)
        msg = str(ei.value)
        assert "time" in msg.lower() or "时间" in msg
        assert "2026/07/28" in msg or "格式" in msg

    def test_bad_category_rejected(self):
        from validators import ValidationError, validate_record
        rec = {
            "category": "不存在分类",
            "amount": -35.0,
            "time": "2026-07-28 12:00:00",
        }
        with pytest.raises(ValidationError):
            validate_record(rec)

    def test_nan_amount_rejected(self):
        from validators import ValidationError, validate_record
        rec = {
            "category": "餐饮",
            "amount": float("nan"),
            "time": "2026-07-28 12:00:00",
        }
        with pytest.raises(ValidationError):
            validate_record(rec)

    def test_defaults_applied(self):
        """未提供 account/ledger/currency/note 时填默认值"""
        from validators import validate_record
        rec = {
            "category": "餐饮/外卖/午餐",
            "amount": -35.0,
            "time": "2026-07-28 12:00:00",
        }
        validated = validate_record(rec)
        assert validated.get("account") == ""
        assert validated.get("ledger") == "生活"
        assert validated.get("currency") == "人民币"
        assert validated.get("note") == ""

    def test_immutable_input(self):
        """validate_record 不应修改入参 dict"""
        from validators import validate_record
        rec = {
            "category": "餐饮/外卖/午餐",
            "amount": -35.0,
            "time": "2026-07-28 12:00:00",
        }
        original_keys = set(rec.keys())
        validate_record(rec)
        assert set(rec.keys()) == original_keys
        assert rec["amount"] == -35.0
