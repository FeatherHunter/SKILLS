"""validators 单元测试"""
import pytest

from home_manager.validators import validate_hard_rules


def test_all_pass():
    draft = {
        "name": "测试物品",
        "category_id": 1,
        "location": "客厅/沙发",
        "tags": ",".join(["t"] * 10),
        "remark": "备注",
    }
    checks, missing = validate_hard_rules(draft)
    assert not missing
    assert checks["has_name"] is True
    assert checks["has_category_id"] is True
    assert checks["location_depth_ok"] is True
    assert checks["tags_ok"] is True
    assert checks["remark_ok"] is True
    assert checks["ready_score"] == 1.0


@pytest.mark.parametrize("field", ["name", "category_id", "location", "remark"])
def test_missing_required(field):
    draft = {
        "name": "X" if field != "name" else "",
        "category_id": 1 if field != "category_id" else None,
        "location": "客厅/沙发" if field != "location" else "",
        "tags": ",".join(["t"] * 10),
        "remark": "r" if field != "remark" else "",
    }
    if field == "tags":
        draft["tags"] = ",".join(["t"] * 5)
    if field == "location":
        draft["location"] = "客厅"  # 单级
    checks, missing = validate_hard_rules(draft)
    assert missing, f"应检测到 {field} 缺失, 但 missing 为空"
    if field == "name":
        assert "缺少物品名称" in missing
    elif field == "category_id":
        assert "缺少 category_id" in missing
    elif field == "location":
        assert "位置必须至少两级" in missing
    elif field == "remark":
        assert "备注不能为空" in missing


def test_short_tags():
    draft = {
        "name": "X", "category_id": 1,
        "location": "客厅/沙发",
        "tags": ",".join(["t"] * 9),  # 9 个不足 10
        "remark": "r",
    }
    checks, missing = validate_hard_rules(draft)
    assert "tag 数量 9 < 10" in missing
    assert checks["tags_ok"] is False


def test_tags_as_list():
    draft = {
        "name": "X", "category_id": 1,
        "location": "客厅/沙发",
        "tags": ["t"] * 10,
        "remark": "r",
    }
    checks, missing = validate_hard_rules(draft)
    assert checks["tags_ok"] is True


def test_ready_score_partial():
    draft = {
        "name": "X", "category_id": None,
        "location": "客厅/沙发",
        "tags": ",".join(["t"] * 10),
        "remark": "r",
    }
    checks, missing = validate_hard_rules(draft)
    assert checks["ready_score"] < 1.0
    assert 0.6 <= checks["ready_score"] <= 0.8
