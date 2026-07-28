"""CLI 写操作 smoke test - 真实调 subprocess, 真实写 DB

隔离: 所有测试物品用 TEST_<uuid>_ 前缀, fixture 自动清理
"""
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

# 跨平台:Windows 用 python,Unix 用 python3(若 python3 不在则降级到 python)
_PY = "python3" if sys.platform != "win32" else "python"
if not shutil.which(_PY):
    _PY = "python"  # 兜底

CLI = [_PY, "home_manager.py"]
# 跨平台:用 Path 推导 scripts/ 目录(本测试文件在 tests/,scripts 在同级)
CWD = str(Path(__file__).parent.parent / "scripts")


def _run(*args):
    return subprocess.run(
        [*CLI, *args],
        capture_output=True, text=True, timeout=30,
        cwd=CWD,
        encoding="utf-8", errors="replace",
    )


def _test_name(prefix):
    return f"TEST_{prefix}_{uuid.uuid4().hex[:8]}"


def _real_category_id(conn):
    """找任意一个 L1 顶级分类 ID (确保 add 校验通过)"""
    row = conn.execute(
        "SELECT id FROM categories WHERE parent_id IS NULL LIMIT 1"
    ).fetchone()
    assert row is not None, "无 L1 分类, 请先 init DB"
    return row[0]


def test_add_item_writes_to_db(conn, cleanup_test_items):
    """add CLI 成功应写入 DB"""
    name = _test_name("add")
    cat_id = _real_category_id(conn)
    result = _run(
        "add",
        "--name", name,
        "--category-id", str(cat_id),
        "--location", "客厅/沙发",
        "--tags", "a,b,c,d,e,f,g,h,i,j",
        "--remark", "test_remark",
    )
    assert result.returncode == 0, f"add 失败: stdout={result.stdout}"
    row = conn.execute("SELECT id FROM items WHERE name = ?", (name,)).fetchone()
    assert row is not None, "add 退出 0 但 DB 无记录"
    cleanup_test_items.append(row[0])


def test_add_item_rejects_short_tags(conn, cleanup_test_items):
    """硬规则: tag 数量 < 10 应被拒"""
    name = _test_name("short_tags")
    cat_id = _real_category_id(conn)
    result = _run(
        "add",
        "--name", name,
        "--category-id", str(cat_id),
        "--location", "客厅/沙发",
        "--tags", "a,b,c",
        "--remark", "r",
    )
    assert result.returncode != 0, f"硬规则被绕过: stdout={result.stdout}"
    row = conn.execute("SELECT id FROM items WHERE name = ?", (name,)).fetchone()
    assert row is None, "被拒绝但 DB 仍有记录"


def test_add_item_rejects_single_location(conn, cleanup_test_items):
    """硬规则: 单级位置应被拒 (location_depth_ok=False)"""
    name = _test_name("single_loc")
    cat_id = _real_category_id(conn)
    result = _run(
        "add",
        "--name", name,
        "--category-id", str(cat_id),
        "--location", "客厅",
        "--tags", "a,b,c,d,e,f,g,h,i,j",
        "--remark", "r",
    )
    assert result.returncode != 0, "单级位置被允许"
    row = conn.execute("SELECT id FROM items WHERE name = ?", (name,)).fetchone()
    assert row is None


def test_add_item_rejects_empty_remark(conn, cleanup_test_items):
    """硬规则: 备注为空应被拒"""
    name = _test_name("no_remark")
    cat_id = _real_category_id(conn)
    result = _run(
        "add",
        "--name", name,
        "--category-id", str(cat_id),
        "--location", "客厅/沙发",
        "--tags", "a,b,c,d,e,f,g,h,i,j",
        "--remark", "",
    )
    assert result.returncode != 0
    row = conn.execute("SELECT id FROM items WHERE name = ?", (name,)).fetchone()
    assert row is None