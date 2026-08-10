"""SM2 空间与位置域测试(G6: fixture 模拟库,不碰生产库)

fixture 库模式(同 test_sm4):
  - 每个测试用独立临时库(SKILLS_DB_PATH → tmp_path)+ reload home_manager.db
  - 种子:顶级分类 + 二级;物品 TEST_ 前缀
每场景 ≥1 端到端(CLI 级)+ 核心操作边界用例。
"""
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"

PY = sys.executable
CLI = [PY, str(SCRIPTS_DIR / "home_manager.py")]


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """独立临时库 fixture(种子分类;每测试独立,不碰生产库)"""
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    import home_manager.db as db_mod
    importlib.reload(db_mod)
    db_mod.init_db()
    conn = db_mod.get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO categories (id, parent_id, name) VALUES (1, NULL, '食物与饮品')")
    c.execute("INSERT INTO categories (id, parent_id, name) VALUES (2, NULL, '衣物与穿戴')")
    c.execute("INSERT INTO categories (id, parent_id, name) VALUES (3, 1, '零食')")
    c.execute("INSERT INTO categories (id, parent_id, name) VALUES (4, 2, '上装')")
    conn.commit()
    yield conn
    conn.close()
    monkeypatch.undo()
    importlib.reload(db_mod)


def _seed_item(conn, iid, name, cat_id, location, price=None, status="在家", qty=1,
               last_accessed=None, access_count=0):
    """直接 SQL 种子一个物品"""
    c = conn.cursor()
    c.execute(
        "INSERT INTO items (id, name, category_id, purchase_price, created_at, updated_at, "
        "last_accessed_at, access_count) VALUES (?,?,?,?,?,?,?,?)",
        (iid, name, cat_id, price, "2026-08-01 09:00:00", "2026-08-01 09:00:00",
         last_accessed, access_count))
    c.execute(
        "INSERT INTO item_locations (item_id, location, quantity, location_status) "
        "VALUES (?,?,?,?)",
        (iid, location, qty, status))
    conn.commit()


@pytest.fixture
def seeded(tmp_db):
    """标准种子:4 物品跨 3 位置(供多场景共享断言)"""
    _seed_item(tmp_db, 1, "TEST_钥匙", 4, "客厅/茶几", last_accessed="2026-08-02 08:00:00", access_count=3)
    _seed_item(tmp_db, 2, "TEST_牛奶", 3, "厨房/冰箱", last_accessed="2026-08-01 12:00:00", access_count=2)
    _seed_item(tmp_db, 3, "TEST_旧毛衣", 4, "卧室/衣柜", qty=1)
    _seed_item(tmp_db, 4, "TEST_酱油", 3, "厨房/调味区", qty=2, last_accessed="2026-08-03 18:00:00")
    return tmp_db


def _run_cli(*args):
    env = os.environ.copy()
    env["SKILLS_DB_PATH"] = os.environ.get("SKILLS_DB_PATH", "")
    r = subprocess.run(CLI + list(args), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env)
    return r


def _load_output(r):
    """CLI stdout 最后一行 = JSON 结果(render emit)"""
    line = r.stdout.strip().splitlines()[-1]
    return json.loads(line), r.returncode


# ═══════════════ SM2-4 空间视图 ═══════════════

def test_space_view_tree_structure(seeded):
    from 位置.tree import build_tree
    d = build_tree(seeded, current_path=None)
    assert d["current_path"] == ""
    # 顶层 3 个子位置(客厅/厨房/卧室)
    kids = {c["name"]: c for c in d["children"]}
    assert set(kids) == {"客厅", "厨房", "卧室"}
    assert kids["厨房"]["count"] == 3      # 冰箱 1 + 调味区 2
    assert kids["厨房"]["has_children"] is True


def test_space_view_drill_down(seeded):
    from 位置.tree import build_tree
    d = build_tree(seeded, current_path="厨房")
    assert d["current_name"] == "厨房"
    assert [b["name"] for b in d["breadcrumbs"]] == ["厨房"]
    kids = {c["name"]: c for c in d["children"]}
    assert set(kids) == {"冰箱", "调味区"}
    assert kids["调味区"]["count"] == 2


def test_space_view_items_at_level(seeded):
    from 位置.tree import build_tree
    d = build_tree(seeded, current_path="厨房/冰箱")
    assert [i["name"] for i in d["items"]] == ["TEST_牛奶"]
    # 底层无 children
    assert d["children"] == []


def test_space_view_e2e_cli(tmp_db, tmp_path, seeded):
    """端到端: sm2-view 出 HTML(每场景 ≥1 E2E 的 CLI 级)"""
    r = _run_cli("sm2-view", "--output", str(tmp_path / "view.html"))
    result, code = _load_output(r)
    assert code == 0 and result["status"] == "ok"
    html = (tmp_path / "view.html").read_text(encoding="utf-8")
    assert "空间视图" in html and "厨房" in html and "客厅" in html


# ═══════════════ SM2-1 位置管理 ═══════════════

def test_manage_view_payload(seeded):
    from 位置 import ops
    d = ops.manage_payload(seeded)
    assert d["total_nodes"] >= 4
    paths = {n["path"] for n in d["nodes"]}
    assert "客厅/茶几" in paths and "厨房/冰箱" in paths


def test_similar_detection(seeded):
    """「卧室/衣柜」vs「卧室衣柜」→ flattened 相同 → 相似组"""
    from 位置 import ops
    c = seeded.cursor()
    c.execute("INSERT INTO item_locations (item_id, location, quantity, location_status) "
              "VALUES (2, '卧室衣柜', 1, '在家')")
    seeded.commit()
    groups = ops.detect_similar(seeded)
    flat = ["".join(g["paths"]).replace("/", "") for g in groups]
    assert any("卧室衣柜" in p for p in flat)


def test_create_node(tmp_db):
    from 位置 import ops
    ok, msg, path = ops.create_node(tmp_db, " 玄关 / 抽屉 ")
    assert ok and path == "玄关/抽屉"
    # 祖先自动补建
    cursor = tmp_db.cursor()
    cursor.execute("SELECT path FROM location_nodes ORDER BY id")
    assert [r["path"] for r in cursor.fetchall()] == ["玄关", "玄关/抽屉"]
    # 重复创建拦截
    ok2, msg2, _ = ops.create_node(tmp_db, "玄关/抽屉")
    assert not ok2 and "已存在" in msg2


def test_create_node_invalid(tmp_db):
    from 位置 import ops
    ok, msg, _ = ops.create_node(tmp_db, "///")
    assert not ok
    ok, msg, _ = ops.create_node(tmp_db, "客厅/" + "长" * 31)
    assert not ok and "30 字" in msg


def test_rename_cascade(seeded):
    """改名级联:条目 + 固定位 + 节点"""
    from 位置 import ops
    ops.fixed_set(seeded, 2, "厨房/冰箱", cli_cmd="t")
    ok, msg, result = ops.rename_node(seeded, "厨房", "厨房区")
    assert ok and "涉及 2 件物品" in msg
    cursor = seeded.cursor()
    cursor.execute("SELECT location FROM item_locations WHERE item_id = 2")
    assert cursor.fetchone()["location"] == "厨房区/冰箱"
    cursor.execute("SELECT location FROM item_locations WHERE item_id = 4")
    assert cursor.fetchone()["location"] == "厨房区/调味区"
    cursor.execute("SELECT fixed_location FROM items WHERE id = 2")
    assert cursor.fetchone()["fixed_location"] == "厨房区/冰箱"
    # 事件写入(记录契约)
    cursor.execute("SELECT COUNT(*) AS n FROM item_events WHERE event_type = 'location_renamed'")
    assert cursor.fetchone()["n"] >= 2


def test_rename_conflict(seeded):
    """目标已是独立位置 → 拦截引导合并"""
    from 位置 import ops
    ops.create_node(seeded, "厨房区")
    ok, msg, _ = ops.rename_node(seeded, "厨房", "厨房区")
    assert not ok and "合并" in msg


def test_merge_node(seeded):
    from 位置 import ops
    ops.create_node(seeded, "卧室衣柜")
    _seed_item(seeded, 9, "TEST_毯子", 2, "卧室衣柜")
    ok, msg, result = ops.merge_node(seeded, "卧室衣柜", "卧室/衣柜")
    assert ok and "涉及 1 件物品" in msg
    cursor = seeded.cursor()
    cursor.execute("SELECT location FROM item_locations WHERE item_id = 9")
    assert cursor.fetchone()["location"] == "卧室/衣柜"
    cursor.execute("SELECT COUNT(*) AS n FROM location_nodes WHERE path = '卧室衣柜'")
    assert cursor.fetchone()["n"] == 0


def test_merge_node_tgt_exists(seeded):
    """相似检测典型:src/tgt 两节点都已存在 → 合并不崩(UNIQUE path),条目迁移+去重+固定位级联"""
    from 位置 import ops
    ops.create_node(seeded, "客厅/冰箱/上层")
    ops.create_node(seeded, "客厅/冰箱上层")
    _seed_item(seeded, 9, "TEST_牛奶2", 3, "客厅/冰箱/上层", qty=1)
    _seed_item(seeded, 10, "TEST_鸡蛋", 3, "客厅/冰箱上层", qty=2)
    ops.fixed_set(seeded, 9, "客厅/冰箱/上层", cli_cmd="t")
    ok, msg, result = ops.merge_node(seeded, "客厅/冰箱/上层", "客厅/冰箱上层", cli_cmd="t")
    assert ok and "涉及 1 件物品" in msg
    cursor = seeded.cursor()
    cursor.execute("SELECT location FROM item_locations WHERE item_id = 9")
    assert cursor.fetchone()["location"] == "客厅/冰箱上层"
    cursor.execute("SELECT location FROM item_locations WHERE item_id = 10")
    assert cursor.fetchone()["location"] == "客厅/冰箱上层"
    cursor.execute("SELECT fixed_location FROM items WHERE id = 9")
    assert cursor.fetchone()["fixed_location"] == "客厅/冰箱上层"
    cursor.execute("SELECT COUNT(*) AS n FROM location_nodes WHERE path = '客厅/冰箱/上层'")
    assert cursor.fetchone()["n"] == 0
    cursor.execute("SELECT COUNT(*) AS n FROM location_nodes WHERE path = '客厅/冰箱上层'")
    assert cursor.fetchone()["n"] == 1
    # 事件(记录契约)
    cursor.execute("SELECT COUNT(*) AS n FROM item_events WHERE event_type = 'location_renamed'")
    assert cursor.fetchone()["n"] >= 1


def test_delete_blocked_by_items(seeded):
    from 位置 import ops
    ok, msg, _ = ops.delete_node(seeded, "厨房")
    assert not ok and "不能删除" in msg


def test_delete_empty_node(tmp_db):
    from 位置 import ops
    ops.create_node(tmp_db, "杂物间/纸箱")
    ok, msg, _ = ops.delete_node(tmp_db, "杂物间/纸箱")
    assert ok
    cursor = tmp_db.cursor()
    cursor.execute("SELECT COUNT(*) AS n FROM location_nodes WHERE path LIKE '杂物间%'")
    assert cursor.fetchone()["n"] == 0  # 空父链一并清理


def test_manage_e2e_cli(tmp_db, tmp_path, seeded):
    """端到端: 管位置查看 + 改名回执"""
    r = _run_cli("sm2-manage", "--output", str(tmp_path / "mg.html"))
    result, code = _load_output(r)
    assert code == 0 and result["status"] == "ok"
    html = (tmp_path / "mg.html").read_text(encoding="utf-8")
    assert "位置体系管理" in html and "厨房" in html
    r2 = _run_cli("sm2-manage", "--action", "rename", "--old", "厨房", "--new", "厨房区")
    result2, code2 = _load_output(r2)
    assert code2 == 0 and result2["status"] == "ok"


# ═══════════════ SM2-2 固定位 ═══════════════

def test_fixed_set_and_list(seeded):
    from 位置 import ops
    ok, msg, payload = ops.fixed_set(seeded, 1, "玄关/抽屉")
    assert ok and payload["fixed_location"] == "玄关/抽屉"
    d = ops.fixed_list_payload(seeded)
    assert d["total"] == 1
    it = d["fixed_items"][0]
    assert it["name"] == "TEST_钥匙"
    assert it["warn"] is True       # 当前位置 客厅/茶几 ≠ 玄关/抽屉


def test_fixed_at_spot_no_warn(seeded):
    from 位置 import ops
    ops.fixed_set(seeded, 2, "厨房/冰箱")
    d = ops.fixed_list_payload(seeded)
    it = d["fixed_items"][0]
    assert it["at_fixed"] is True and it["warn"] is False


def test_fixed_clear(seeded):
    from 位置 import ops
    ops.fixed_set(seeded, 1, "玄关/抽屉")
    ok, msg, _ = ops.fixed_clear(seeded, 1)
    assert ok
    assert ops.fixed_list_payload(seeded)["total"] == 0
    # 未设置时解除 → 拦截
    ok2, msg2, _ = ops.fixed_clear(seeded, 1)
    assert not ok2 and "没有固定位" in msg2


def test_fixed_e2e_cli(tmp_db, tmp_path, seeded):
    r = _run_cli("sm2-fixed", "--action", "set", "--item-id", "1", "--location", "玄关/抽屉")
    result, code = _load_output(r)
    assert code == 0 and result["status"] == "ok"
    r2 = _run_cli("sm2-fixed", "--output", str(tmp_path / "fx.html"))
    result2, code2 = _load_output(r2)
    assert code2 == 0 and result2["status"] == "ok"
    html = (tmp_path / "fx.html").read_text(encoding="utf-8")
    assert "玄关/抽屉" in html and "不在固定位" in html


# ═══════════════ SM2-3 收纳建议 ═══════════════

def test_suggest_weak_evidence_keeps_current(seeded):
    """弱证据(同类 1/1 分布):保持现状,不推荐搬家(对抗审查定稿规则)"""
    from 位置 import ops
    rec = ops.recommend_item(seeded, 2)   # TEST_牛奶(厨房/冰箱),同类仅酱油在调味区
    assert rec["recommend"] is None
    assert rec["keep"] is not None
    assert rec["keep"]["location"] == "厨房/冰箱"
    assert "保持现状" in rec["keep"]["reason"]


def test_suggest_strong_evidence_recommends(seeded):
    """强证据(同分类 ≥2 件共用某位置):推荐搬移到热门位"""
    from 位置 import ops
    _seed_item(seeded, 5, "TEST_薯片", 3, "厨房/调味区")
    _seed_item(seeded, 6, "TEST_饼干", 3, "厨房/调味区")
    rec = ops.recommend_item(seeded, 2)   # TEST_牛奶(厨房/冰箱)
    assert rec["recommend"] is not None
    assert rec["recommend"]["location"] == "厨房/调味区"
    assert "3 件同类" in rec["recommend"]["reason"]
    # 已在热门位的调味区物品 → 保持
    rec2 = ops.recommend_item(seeded, 4)  # TEST_酱油(厨房/调味区)
    assert rec2["recommend"] is None
    assert rec2["keep"]["location"] == "厨房/调味区"


def test_suggest_related_location(seeded):
    """关联物品位置:跨分类关联 → 推荐关联物品所在位置"""
    from 位置 import ops
    from 物品.events import ensure_tables
    ensure_tables(seeded)
    c = seeded.cursor()
    c.execute("INSERT INTO categories (id, parent_id, name) VALUES (5, NULL, '数码与电子')")
    _seed_item(seeded, 9, "TEST_充电器", 5, "卧室/床头柜")
    # 充电器(数码,唯一) ↔ 钥匙(客厅/茶几):分类无同类 → 关联证据生效
    c.execute("INSERT INTO item_relations (item_id, related_item_id, relation_type, created_at) "
              "VALUES (9, 1, '常用搭配', '2026-08-01 09:00:00')")
    seeded.commit()
    rec = ops.recommend_item(seeded, 9)
    assert rec["recommend"] is not None
    assert rec["recommend"]["location"] == "客厅/茶几"
    assert "关联物品" in rec["recommend"]["reason"]


def test_suggest_seed_cold_start(tmp_db):
    """冷启动:物品无任何位置记录 → 种子兜底"""
    from 位置 import ops
    c = tmp_db.cursor()
    c.execute("INSERT INTO items (id, name, category_id, created_at, updated_at) "
              "VALUES (7, 'TEST_米', 3, '2026-08-01 09:00:00', '2026-08-01 09:00:00')")
    tmp_db.commit()
    rec = ops.recommend_item(tmp_db, 7)
    assert rec["seed_used"] is True
    assert rec["recommend"]["location"] == "厨房/食品柜"
    assert "冷启动" in rec["recommend"]["reason"]


def test_suggest_keep_matches_seed(tmp_db):
    """当前位置 == 种子默认 → 确认「符合分类默认」"""
    from 位置 import ops
    _seed_item(tmp_db, 8, "TEST_盐", 3, "厨房/食品柜")   # 零食种子 = 食品柜
    rec = ops.recommend_item(tmp_db, 8)
    assert rec["recommend"] is None
    assert rec["keep"] is not None
    assert "默认位置" in rec["keep"]["reason"]


def test_suggest_batch_only_used_items(seeded):
    """批量模式:没有固定位的常用件(用过/访问过)"""
    from 位置 import ops
    recs = ops.recommend_batch(seeded)
    names = [r["item"]["name"] for r in recs]
    assert "TEST_钥匙" in names          # last_accessed + access_count
    assert "TEST_旧毛衣" not in names    # 从未用过 → 不算常用件
    # 设了固定位后从批量清单消失
    ops.fixed_set(seeded, 1, "玄关/抽屉")
    recs2 = ops.recommend_batch(seeded)
    assert all(r["item"]["name"] != "TEST_钥匙" for r in recs2)


def test_suggest_items_multi(seeded):
    """指定多件(prompt「可多件」落地):一页逐件建议"""
    from 位置 import ops
    recs = ops.recommend_items(seeded, [2, 3])
    assert [r["item"]["name"] for r in recs] == ["TEST_牛奶", "TEST_旧毛衣"]
    assert all(r["recommend"] is not None or r["keep"] is not None for r in recs)
    # 不存在的 ID 跳过
    assert ops.recommend_items(seeded, [2, 9999])[0]["item"]["name"] == "TEST_牛奶"


def test_suggest_e2e_cli_multi(tmp_db, tmp_path, seeded):
    """端到端: --item-ids 一页多卡"""
    r = _run_cli("sm2-suggest", "--item-ids", "2,4", "--output", str(tmp_path / "sgm.html"))
    result, code = _load_output(r)
    assert code == 0 and result["status"] == "ok"
    html = (tmp_path / "sgm.html").read_text(encoding="utf-8")
    assert "TEST_牛奶" in html and "TEST_酱油" in html


def test_suggest_e2e_cli(tmp_db, tmp_path, seeded):
    _seed_item(seeded, 5, "TEST_薯片", 3, "厨房/调味区")
    _seed_item(seeded, 6, "TEST_饼干", 3, "厨房/调味区")
    r = _run_cli("sm2-suggest", "--item-id", "2", "--output", str(tmp_path / "sg.html"))
    result, code = _load_output(r)
    assert code == 0 and result["status"] == "ok"
    html = (tmp_path / "sg.html").read_text(encoding="utf-8")
    assert "推荐放置" in html
    r2 = _run_cli("sm2-suggest", "--batch", "--limit", "10")
    result2, code2 = _load_output(r2)
    assert code2 == 0 and result2["status"] == "ok"


def test_cli_rename_conflict_error_receipt(tmp_db, tmp_path):
    """改名到已存在位置 → 错误回执 HTML(不崩),失败原因透出"""
    from 位置 import ops
    ops.create_node(tmp_db, "书房/电竞桌")
    ops.create_node(tmp_db, "书房/电竞区")
    r = _run_cli("sm2-manage", "--action", "rename", "--old", "书房/电竞桌",
                 "--new", "书房/电竞区", "--output", str(tmp_path / "rename_err.html"))
    assert r.returncode != 0
    out, _ = _load_output(r)
    assert out["status"] == "ok"
    assert out["data"].get("template") == "位置/error.html"
    html = (tmp_path / "rename_err.html").read_text(encoding="utf-8")
    assert "合并" in html


def test_cli_merge_missing_src_error_receipt(tmp_db, tmp_path):
    """合并不存在的 src → 错误回执 HTML(不崩,不静默空成功)"""
    r = _run_cli("sm2-manage", "--action", "merge", "--old", "不存在/位置",
                 "--new", "客厅/茶几", "--output", str(tmp_path / "merge_err.html"))
    assert r.returncode != 0
    out, _ = _load_output(r)
    assert out["status"] == "ok"
    assert out["data"].get("template") == "位置/error.html"
    html = (tmp_path / "merge_err.html").read_text(encoding="utf-8")
    assert "不存在" in html


def test_merge_undo_button_item_precise(tmp_db, tmp_path):
    """撤销合并按钮精确到迁移物品(非路径级): 含物品清单, 不含「把整个位置改回」"""
    from 位置 import ops
    ops.create_node(tmp_db, "客厅/冰箱/上层")
    ops.create_node(tmp_db, "客厅/冰箱上层")
    _seed_item(tmp_db, 9, "TEST_牛奶", 3, "客厅/冰箱/上层", qty=1)
    _seed_item(tmp_db, 10, "TEST_鸡蛋", 3, "客厅/冰箱/上层", qty=2)
    _seed_item(tmp_db, 11, "TEST_酱油", 3, "客厅/冰箱上层", qty=1)  # tgt 原有物品
    r = _run_cli("sm2-manage", "--action", "merge", "--old", "客厅/冰箱/上层",
                 "--new", "客厅/冰箱上层", "--output", str(tmp_path / "merge.html"))
    out, code = _load_output(r)
    assert code == 0 and out["status"] == "ok"
    html = (tmp_path / "merge.html").read_text(encoding="utf-8")
    # 撤销按钮 = 物品级(仅本次迁移的 2 件), 不含 tgt 原有酱油
    assert "本次合并迁移的 2 件" in html
    assert "TEST_牛奶 (ID 9)" in html
    assert "TEST_鸡蛋 (ID 10)" in html
    assert "TEST_酱油 (ID 11)" not in html
    # merged_items 进 scene(复制数据可追溯)
    assert '"merged_items"' in html
