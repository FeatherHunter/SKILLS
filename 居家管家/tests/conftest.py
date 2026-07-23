"""pytest 配置

添加 scripts/ 到 sys.path, 让测试可以 import home_manager / render 等
"""
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import pytest


@pytest.fixture(scope="session")
def conn():
    """共享 DB 连接, session 级 scope 加快速度"""
    from home_manager.db import get_conn
    c = get_conn()
    yield c
    c.close()


@pytest.fixture
def sample_ok_payload():
    """最小可用的 ok payload 样本"""
    return {
        "status": "ok",
        "data": {
            "summary": {"title": "测试", "metrics": []},
            "items": [],
        },
        "message": "测试",
    }


@pytest.fixture
def cleanup_test_items(conn):
    """自动清理本次测试新增的所有 TEST_ 前缀物品

    用法:
        def test_xxx(conn, cleanup_test_items):
            # 测试逻辑
            cleanup_test_items.append(item_id)  # 测试结束后自动 DELETE

    同时也会清理本次可能漏 append 的 TEST_ 前缀物品（双重防护）
    """
    test_ids: list[int] = []
    yield test_ids
    if test_ids:
        for item_id in test_ids:
            try:
                conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
            except Exception:
                pass
    # 兜底: 清理所有 TEST_ 前缀物品 (防漏)
    conn.execute("DELETE FROM items WHERE name LIKE 'TEST\\_%' ESCAPE '\\'")
    conn.commit()
