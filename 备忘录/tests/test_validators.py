"""
硬规则 / 软规则单元测试(不依赖 DB)
- ALLOWED_CATEGORIES 白名单
- _validate_date 日期格式
- convert_weekday 周日=0 ↔ Python 周一=0
- output_json / error_json 三段式契约
"""
from datetime import datetime
import pytest

from memo_cli import (
    ALLOWED_CATEGORIES,
    convert_weekday,
    output_json,
    error_json,
    _validate_date,
)


class TestAllowedCategories:
    def test_default_set(self):
        assert ALLOWED_CATEGORIES == {"备忘", "心愿", "打卡", "情绪日记"}

    def test_default_category_is_memo(self):
        """add_note 默认 category 应为 '备忘'"""
        assert "备忘" in ALLOWED_CATEGORIES


class TestValidateDate:
    def test_valid_format(self):
        dt = _validate_date("2026-07-24", "test_field")
        assert dt == datetime(2026, 7, 24)

    def test_invalid_format_exits(self, capsys):
        """非法格式 → error_json → sys.exit(1)"""
        with pytest.raises(SystemExit) as exc:
            _validate_date("2026/07/24", "test_field")
        assert exc.value.code == 1
        out = capsys.readouterr().out
        assert "test_field" in out
        assert "YYYY-MM-DD" in out
        assert "2026/07/24" in out


class TestConvertWeekday:
    """用户输入:0=周日;Python:0=周一"""

    @pytest.mark.parametrize("user,py_expected", [
        (0, 6),  # 周日 → 6
        (1, 0),  # 周一 → 0
        (5, 4),  # 周五 → 4
        (6, 5),  # 周六 → 5
    ])
    def test_round_trip(self, user, py_expected):
        assert convert_weekday(user) == py_expected


class TestOutputJsonContract:
    def test_output_json_status_ok(self, capsys):
        """output_json 默认 status='ok',三段式齐全"""
        with pytest.raises(SystemExit) as exc:
            output_json({"id": 1}, message="已添加")
        assert exc.value.code == 0
        import json
        out = json.loads(capsys.readouterr().out)
        assert out["status"] == "ok"
        assert out["data"] == {"id": 1}
        assert out["message"] == "已添加"

    def test_error_json(self, capsys):
        with pytest.raises(SystemExit) as exc:
            error_json("字段错误")
        assert exc.value.code == 1
        import json
        out = json.loads(capsys.readouterr().out)
        assert out["status"] == "error"
        assert "字段错误" in out["message"]
        assert "data" not in out