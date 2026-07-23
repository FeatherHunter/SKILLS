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
