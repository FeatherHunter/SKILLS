"""
db.py 测试
"""
import sys
import os
import tempfile
from pathlib import Path
from datetime import date

# 设置临时数据库环境
_TEST_DB_DIR = tempfile.mkdtemp()
os.environ['SKILLS_DB_PATH'] = _TEST_DB_DIR

_SCRIPT_DIR = Path(__file__).parent.resolve()
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))


def test_find_db_path_env():
    """测试环境变量路径查找"""
    from db import _find_db_path
    result = _find_db_path(Path("/fake/skill"), "test.db")
    assert result == Path(_TEST_DB_DIR) / "test.db"


def test_find_db_path_parent():
    """测试父目录路径查找"""
    import tempfile
    from db import _find_db_path
    parent = Path(tempfile.mkdtemp())
    db_dir = parent / ".db"
    db_dir.mkdir()
    skill_dir = parent / "skills" / "test_skill"
    skill_dir.mkdir(parents=True)
    old_env = os.environ.pop('SKILLS_DB_PATH', None)
    try:
        result = _find_db_path(skill_dir, "test.db")
        assert result == db_dir / "test.db"
    finally:
        if old_env:
            os.environ['SKILLS_DB_PATH'] = old_env


def test_find_db_path_fallback():
    """测试 fallback 到技能目录 .db 子目录"""
    import tempfile
    from db import _find_db_path
    skill_dir = Path(tempfile.mkdtemp())
    old_env = os.environ.pop('SKILLS_DB_PATH', None)
    try:
        result = _find_db_path(skill_dir, "test.db")
        assert result == skill_dir / ".db" / "test.db"
    finally:
        if old_env is not None:
            os.environ['SKILLS_DB_PATH'] = old_env


def test_init_db_creates_table():
    """测试数据库初始化创建表"""
    from db import init_db
    conn = init_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bills'")
    assert cursor.fetchone() is not None
    conn.close()


def test_insert_and_fetch():
    """测试插入和查询"""
    from db import insert_record, fetch_all
    result = insert_record("餐饮", -35.0, "2026-05-23 12:00:00", note="午饭")
    assert result['id'] > 0
    assert result['category'] == "餐饮"
    assert result['amount'] == -35.0
    records = fetch_all(from_time="2026-05-23 00:00:00", to_time="2026-05-23 23:59:59")
    assert len(records) >= 1


def test_add_bill():
    """测试 add_bill（只写 SQLite，不写文件）"""
    from db import add_bill
    result = add_bill("交通", -4.0, "2026-05-23 08:00:00", note="地铁")
    assert result['success'] is True
    assert result['id'] > 0
    assert 'file' not in result


def test_list_today():
    """测试 list_today"""
    from db import list_today
    records = list_today()
    assert isinstance(records, list)


def test_list_date():
    """测试 list_date"""
    from db import list_date
    records = list_date("2026-05-23")
    assert isinstance(records, list)


def test_list_date_range():
    """测试 list_date_range"""
    from db import list_date_range
    records = list_date_range("2026-05-01", "2026-05-31")
    assert isinstance(records, list)


def test_list_date_range_missing_param():
    """测试 list_date_range 缺少参数"""
    from db import list_date_range
    try:
        list_date_range("2026-05-01", None)
        assert False, "应该抛出 ValueError"
    except ValueError:
        pass


def test_list_by_category():
    """测试 list_by_category"""
    from db import list_by_category
    records = list_by_category("餐饮")
    assert isinstance(records, list)


def test_search_keyword():
    """测试 search_keyword"""
    from db import search_keyword
    records = search_keyword("午")
    assert isinstance(records, list)


def test_list_recent():
    """测试 list_recent"""
    from db import list_recent
    records = list_recent(5)
    assert isinstance(records, list)
    assert len(records) <= 5


def test_get_by_id():
    """测试 get_by_id"""
    from db import insert_record, get_by_id
    result = insert_record("购物", -100.0, "2026-05-23 15:00:00", note="测试")
    record = get_by_id(result['id'])
    assert record is not None
    assert record['category'] == "购物"


def test_get_by_id_not_found():
    """测试 get_by_id 不存在的 ID"""
    from db import get_by_id
    record = get_by_id(999999)
    assert record is None


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
