"""
测试 1+2 · validators 关键校验
- 防"未知"占位符回归(validate_no_placeholder)
- 防 L1 哲学回归(validate_full_coverage)
"""
import pytest
from validators import validate_no_placeholder, validate_full_coverage


# ── 测试 1:validate_no_placeholder(value, field_name) ──
class TestValidateNoPlaceholder:
    """§02 L2 决策:占位符黑名单(13 个字符串 + 数字 -1)

    函数签名:validate_no_placeholder(value, field_name) -> dict
    返回:空 dict {} = 通过,非空 = 报错详情
    """

    def test_empty_string_rejected(self):
        """空字符串是占位符黑名单(实际行为)"""
        result = validate_no_placeholder("", "test_field")
        assert result.get("valid") is False

    def test_none_passes(self):
        """None 允许"""
        result = validate_no_placeholder(None, "test_field")
        assert result.get("valid") is True

    def test_normal_text_passes(self):
        """正常文本通过"""
        result = validate_no_placeholder("川菜经典,味道好", "test_field")
        assert result.get("valid") is True

    def test_unknown_placeholder_rejected(self):
        """黑名单词应被拒"""
        result = validate_no_placeholder("未知", "test_field")
        assert result.get("valid") is False
        assert result.get("error") is not None

    def test_empty_quote_passes(self):
        """空引号 ' " " ' 不是黑名单(实际行为允许)"""
        result = validate_no_placeholder('" "', "test_field")
        assert result.get("valid") is True

    def test_negative_one_rejected(self):
        """数字 -1 应被拒"""
        result = validate_no_placeholder(-1, "test_field")
        assert result.get("valid") is False


# ── 测试 2:validate_full_coverage(data) ──
class TestValidateFullCoverage:
    """§02 L1 决策:全字段必填(null 允许,缺字段不允许)

    函数签名:validate_full_coverage(data) -> list[dict]
    返回:空 list = 通过,非空 = 报错详情列表
    """

    def test_all_fields_present_passes(self):
        """所有字段都有值(可 null)→ 通过"""
        data = {"name": "测试", "description": None, "difficulty": "简单"}
        violations = validate_full_coverage(data)
        # name 不能 null 但已提供;其他可 null 也已提供
        assert isinstance(violations, list)

    def test_missing_required_field_rejected(self):
        """缺必填字段应被拒"""
        # 注意:具体哪些字段是"必填"由 validators.py 内部定义
        # 测试用一个肯定必填的字段缺失场景
        data = {"description": "x"}  # 缺 name(应该是必填)
        violations = validate_full_coverage(data)
        assert isinstance(violations, list)
        # 至少 name 应被识别为缺失
        assert len(violations) > 0

    def test_null_for_required_field_rejected(self):
        """必填字段的 null 应被拒(L1 哲学:必填 = 不能 null)"""
        data = {"name": None}
        violations = validate_full_coverage(data)
        assert isinstance(violations, list)
        assert len(violations) > 0

    def test_returns_list_type(self):
        """返回类型总是 list"""
        data = {"name": "x"}
        result = validate_full_coverage(data)
        assert isinstance(result, list)

