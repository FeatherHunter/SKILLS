"""
私家大厨 · pytest 共享 fixture
- 路径: scripts/ 自动入 sys.path
- 提供: 临时 DB / 临时 CHEF_OUTPUT_DIR
"""
import sys
import os
import pytest
from pathlib import Path

# 把 scripts/ 加入 sys.path(让 import 简洁)
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """临时数据库 + 临时 CHEF_OUTPUT_DIR(测试隔离)"""
    db_path = tmp_path / "test_chef.db"
    chef_out = tmp_path / "chef_output"
    chef_out.mkdir()
    monkeypatch.setenv("CHEF_OUTPUT_DIR", str(chef_out))
    # 设 SKILLS_DB_PATH(如果该 skill 用了)
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    return {
        "db_path": db_path,
        "chef_output": chef_out,
        "tmp_path": tmp_path,
    }


@pytest.fixture
def sample_recipe_yaml():
    """最小可用菜谱 YAML(测试用)"""
    return {
        "name": "测试菜",
        "difficulty": "简单",
        "servings": 2,
        "total_time_minutes": 15,
        "status": "未做",
        "description": "测试用菜谱",
        "ingredients": [
            {"name": "测试食材A", "quantity": 100, "unit": "g", "category": "蔬菜", "quantity_text": "100g", "is_optional": 0, "substitute": "无", "sequence": 1}
        ],
        "steps": [
            {"action": "洗菜切配", "sequence": 1, "duration": 5, "heat_level": "中火", "temperature": "常温", "expected_result": "切好"}
        ],
    }
