"""pytest 配置

添加 scripts/ 到 sys.path, 让测试可以 import home_manager / render 等
"""
import importlib
import os
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import pytest


# 8 顶级分类种子(SKILL 分类命名规范 · 无数字前缀/无 emoji)
_TOP_CATEGORIES = [
    "食物与饮品", "衣物与穿戴", "家居与陈设", "工具与器材",
    "数码与电子", "健康与医药", "文体与娱乐", "资产与凭证",
]


@pytest.fixture(scope="session")
def conn(tmp_path_factory):
    """共享临时 DB 连接, session 级 scope 加快速度。

    issue #125 修复: 不再直连生产库 —— monkeypatch SKILLS_DB_PATH 指向
    pytest 临时目录 + reload home_manager.db, 全量 pytest 与生产库物理隔离,
    消除跨进程竞态(TEST_ 残留 / 并行 session 互踩)。
    teardown 恢复 env 并 reload, 不残留对后续测试的影响。
    """
    from home_manager import db as hm_db

    data_dir = tmp_path_factory.mktemp("pytest_db")
    prev_env = os.environ.get("SKILLS_DB_PATH")
    os.environ["SKILLS_DB_PATH"] = str(data_dir)
    importlib.reload(hm_db)
    hm_db.init_db()
    c = hm_db.get_conn()
    # 种 8 顶级分类(CLI 写操作硬校验依赖 L1 分类存在)
    for name in _TOP_CATEGORIES:
        c.execute("INSERT OR IGNORE INTO categories (name, parent_id) VALUES (?, NULL)", (name,))
    c.commit()
    yield c
    c.close()
    # teardown: 恢复 env(与 reload 配对, 保证模块级 DB_PATH 回到原状)
    if prev_env is None:
        os.environ.pop("SKILLS_DB_PATH", None)
    else:
        os.environ["SKILLS_DB_PATH"] = prev_env
    importlib.reload(hm_db)


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


@pytest.fixture(autouse=True)
def _tx_probe(request, conn):
    yield
    if conn.in_transaction:
        print(f"\n[TX-OPEN] after {request.node.name}")
        conn.rollback()
