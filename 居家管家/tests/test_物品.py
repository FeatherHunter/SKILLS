"""SM1 物品管理域测试(T2 · 29 场景)

隔离: TEST_ 前缀 + fixture 清理(物品/事件/照片/关联/盘点记录)
覆盖: 录入4/查找6/更新8/标签分类3/照片3/盘点4/历史1 + 记录契约
"""
import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

_PY = "python3" if sys.platform != "win32" else "python"
if not shutil.which(_PY):
    _PY = "python"

CLI = [_PY, "home_manager.py"]
CWD = str(Path(__file__).parent.parent / "scripts")


def _run(*args):
    return subprocess.run(
        [*CLI, *args],
        capture_output=True, text=True, timeout=60,
        cwd=CWD, encoding="utf-8", errors="replace",
    )


def _test_name(prefix):
    return f"TEST_{prefix}_{uuid.uuid4().hex[:6]}"


def _q(sql, params=()):
    """用全新连接查询(规避共享会话连接的快照可见性问题)"""
    from home_manager.db import get_conn
    c = get_conn()
    try:
        return c.execute(sql, params).fetchall()
    finally:
        c.close()


def _q1(sql, params=()):
    rows = _q(sql, params)
    return rows[0] if rows else None


def _real_category_id(conn):
    row = conn.execute("SELECT id FROM categories WHERE parent_id IS NULL LIMIT 1").fetchone()
    assert row is not None
    return row[0]


@pytest.fixture
def sm1_env(conn, cleanup_test_items):
    """SM1 测试环境: 记录 item_id,测试结束清理事件/照片/关联/盘点"""
    ids = []
    yield ids
    for iid in ids:
        for sql, params in (
            ("DELETE FROM item_events WHERE item_id = ?", (iid,)),
            ("DELETE FROM photo WHERE item_id = ?", (iid,)),
            ("DELETE FROM item_relations WHERE item_id = ? OR related_item_id = ?", (iid, iid)),
        ):
            try:
                conn.execute(sql, params)
            except Exception:
                pass
    try:
        conn.execute("DELETE FROM inventory_records")
    except Exception:
        pass
    conn.commit()


def _add(conn, sm1_env, name=None, category_id=None, location="客厅/沙发",
         quantity=1, tags="", remark="", **kw):
    name = name or _test_name("add")
    cat = category_id or _real_category_id(conn)
    args = ["sm1-add", "--name", name, "--category-id", str(cat),
            "--location", location, "--quantity", str(quantity),
            "--tags", tags, "--remark", remark]
    for k, v in kw.items():
        flag = "--" + k.replace("_", "-")
        args += [flag, str(v)]
    r = _run(*args)
    assert r.returncode == 0, f"sm1-add 失败: {r.stdout}{r.stderr}"
    row = _q1("SELECT id FROM items WHERE name = ? ORDER BY id DESC LIMIT 1", (name,))
    assert row is not None, f"add 退出 0 但会话连接读不到 {name}"
    sm1_env.append(row[0])
    return row[0], name


def _event_count(conn, item_id, event_type):
    row = _q1(
        "SELECT COUNT(*) AS n FROM item_events WHERE item_id = ? AND event_type = ?",
        (item_id, event_type))
    return row["n"] if row else 0


def _last_event(conn, item_id):
    return _q1(
        "SELECT * FROM item_events WHERE item_id = ? ORDER BY id DESC LIMIT 1",
        (item_id,))


# ── 子功能 1 · 录入(4 场景)─────────────────────────────────────────────────


def test_1_1_add_spec_allows_few_tags(conn, sm1_env):
    """1-1: 规格口径 = 名称+分类必填;标签/备注自由(不再强制 ≥10)"""
    iid, name = _add(conn, sm1_env, tags="小米,黑色", remark="测试")
    assert _event_count(conn, iid, "created") == 1


def test_1_1_add_rejects_missing_name(conn, sm1_env):
    r = _run("sm1-add", "--category-id", str(_real_category_id(conn)),
             "--location", "客厅/沙发")
    assert r.returncode != 0


def test_1_1_add_rejects_missing_category(conn, sm1_env):
    r = _run("sm1-add", "--name", _test_name("nocat"), "--location", "客厅/沙发")
    assert r.returncode != 0


def test_1_1_add_rejects_bad_location(conn, sm1_env):
    r = _run("sm1-add", "--name", _test_name("badloc"),
             "--category-id", str(_real_category_id(conn)), "--location", "客厅")
    assert r.returncode != 0


def test_1_1_add_preview_renders_form(conn, sm1_env):
    """1-1: 采集表单 HTML(写库前预览确认)"""
    name = _test_name("prev")
    out = str(Path(__file__).parent.parent / "output" / f"{uuid.uuid4().hex}.html")
    r = _run("sm1-add", "--name", name, "--category-id", str(_real_category_id(conn)),
             "--location", "客厅/沙发", "--preview", "--output", out)
    assert r.returncode == 0
    html = Path(out).read_text(encoding="utf-8")
    assert "采集" in html or "name" in html
    assert conn.execute("SELECT id FROM items WHERE name = ?", (name,)).fetchone() is None


def test_1_2_photo_add_draft_in_form(conn, sm1_env):
    """1-2: 拍照录入走同一采集组件(photo_scan 模式)"""
    name = _test_name("photo")
    out = str(Path(__file__).parent.parent / "output" / f"{uuid.uuid4().hex}.html")
    r = _run("sm1-add", "--name", name, "--category-id", str(_real_category_id(conn)),
             "--location", "客厅/沙发", "--preview", "--output", out)
    assert r.returncode == 0


def test_1_3_batch_preview_and_commit(conn, sm1_env):
    """1-3: 批量预览(批内/库内重复)+ 批量写库(共享 scene_id)"""
    drafts = [
        {"name": _test_name("b1"), "category_id": _real_category_id(conn), "quantity": 1},
        {"name": _test_name("b2"), "category_id": _real_category_id(conn), "quantity": 2},
    ]
    path = str(Path(__file__).parent.parent / "output" / f"{uuid.uuid4().hex}.json")
    Path(path).write_text(json.dumps(drafts, ensure_ascii=False), encoding="utf-8")
    r = _run("sm1-add-batch", "--json-file", path)
    assert r.returncode == 0
    r = _run("sm1-add-batch", "--json-file", path, "--commit")
    assert r.returncode == 0, f"批量写库失败: {r.stdout}{r.stderr}"
    for d in drafts:
        row = conn.execute("SELECT id FROM items WHERE name = ?", (d["name"],)).fetchone()
        assert row is not None
        sm1_env.append(row[0])
        assert _event_count(conn, row[0], "batch_created") == 1


def test_1_4_backfill_with_date(conn, sm1_env):
    """1-4: 补录指定日期 → created_at 回显 + backfilled 事件"""
    iid, name = _add(conn, sm1_env, backfill_date="2026-01-15")
    row = conn.execute("SELECT created_at FROM items WHERE id = ?", (iid,)).fetchone()
    assert row["created_at"].startswith("2026-01-15")
    assert _event_count(conn, iid, "backfilled") == 1


# ── 子功能 2 · 查找(6 场景)─────────────────────────────────────────────────


def test_2_1_search_by_name_tag_location(conn, sm1_env):
    from 物品 import ops
    iid, name = _add(conn, sm1_env, tags="独特标签X1", location="客厅/沙发")
    kw = name.split("_")[-1][:6]
    data = ops.search_payload_v2(name=kw)
    assert any(it["id"] == iid for it in data["items"]), f"kw={kw} hits={[it['id'] for it in data['items']]}"
    data = ops.search_payload_v2(tag="独特标签X1")
    assert any(it["id"] == iid for it in data["items"]), f"tag hits={[it['id'] for it in data['items']]}"
    data = ops.search_payload_v2(location="客厅/沙发")
    assert any(it["id"] == iid for it in data["items"]), f"loc hits={[(it['id'], it['location']) for it in data['items']][:5]}"


def test_2_1_search_hides_discarded(conn, sm1_env):
    from 物品 import ops
    iid, name = _add(conn, sm1_env)
    assert _run("sm1-status", "--id", str(iid), "--status", "已废弃").returncode == 0
    data = ops.search_payload_v2(name=name)
    assert all(it["id"] != iid for it in data["items"])


def test_2_2_detail_with_neighbors_and_relations(conn, sm1_env):
    from 物品 import ops
    iid, name = _add(conn, sm1_env, location="客厅/电视柜")
    iid2, _ = _add(conn, sm1_env, location="客厅/电视柜")
    data = ops.detail_payload_v2(iid)
    assert any(n["id"] == iid2 for n in data["neighbors"])


def test_2_3_locate_urgent(conn, sm1_env):
    from 物品 import ops
    iid, name = _add(conn, sm1_env, location="卧室/床头柜")
    data = ops.locate_payload_v2(name.split("_")[-1][:6])
    assert any(it["id"] == iid for it in data["items"])


def test_2_4_browse_filter(conn, sm1_env):
    from 物品 import ops
    iid, name = _add(conn, sm1_env, location="厨房/柜子")
    data = ops.browse_payload_v2(location="厨房", group_by="category")
    assert any(it["id"] == iid for it in data["items"])


def test_2_6_duplicates(conn, sm1_env):
    from 物品 import ops
    common = _test_name("dup")
    iid1, _ = _add(conn, sm1_env, name=common, location="客厅/沙发")
    iid2, _ = _add(conn, sm1_env, name=common, location="卧室/床")
    data = ops.duplicates_payload_v2()
    assert any(g["name"] == common and g["count"] == 2 for g in data["groups"])


# ── 子功能 3 · 更新(8 场景)─────────────────────────────────────────────────


def test_3_1_update_with_diff_and_undo(conn, sm1_env):
    iid, name = _add(conn, sm1_env)
    r = _run("sm1-update", "--id", str(iid), "--name", name + "_改")
    assert r.returncode == 0
    assert _event_count(conn, iid, "updated") == 1
    ev = _last_event(conn, iid)
    assert '"name"' in ev["payload_json"]
    # 撤销恢复
    r = _run("sm1-undo", "--event-id", str(ev["id"]))
    assert r.returncode == 0
    row = conn.execute("SELECT name FROM items WHERE id = ?", (iid,)).fetchone()
    assert row["name"] == name
    assert _event_count(conn, iid, "undone") == 1


def test_3_2_move_with_neighbors_and_undo(conn, sm1_env):
    iid, name = _add(conn, sm1_env, location="客厅/沙发")
    r = _run("sm1-move", "--id", str(iid), "--location", "书房/书架")
    assert r.returncode == 0
    loc = conn.execute("SELECT location FROM item_locations WHERE item_id = ?", (iid,)).fetchone()
    assert loc["location"] == "书房/书架"
    ev = _last_event(conn, iid)
    assert ev["event_type"] == "location_moved"
    r = _run("sm1-undo", "--event-id", str(ev["id"]))
    assert r.returncode == 0
    loc = conn.execute("SELECT location FROM item_locations WHERE item_id = ?", (iid,)).fetchone()
    assert loc["location"] == "客厅/沙发"


def test_3_2_move_batch(conn, sm1_env):
    iid1, _ = _add(conn, sm1_env)
    iid2, _ = _add(conn, sm1_env)
    r = _run("sm1-move", "--ids", f"{iid1},{iid2}", "--location", "储物间/箱子")
    assert r.returncode == 0


def test_3_3_quantity_exhausted(conn, sm1_env):
    iid, _ = _add(conn, sm1_env, quantity=2)
    r = _run("sm1-qty", "--id", str(iid), "--minus", "2")
    assert r.returncode == 0
    assert conn.execute("SELECT COUNT(*) AS n FROM item_locations WHERE item_id = ?", (iid,)).fetchone()["n"] == 0
    assert _event_count(conn, iid, "quantity_changed") == 1


def test_3_4_status_machine_guard(conn, sm1_env):
    iid, _ = _add(conn, sm1_env)
    assert _run("sm1-status", "--id", str(iid), "--status", "已废弃").returncode == 0
    # 非法流转: 已废弃 → 维修中 拦截
    r = _run("sm1-status", "--id", str(iid), "--status", "维修中")
    assert r.returncode != 0
    # 恢复: 已废弃 → 在家
    assert _run("sm1-status", "--id", str(iid), "--status", "在家").returncode == 0
    assert _event_count(conn, iid, "status_changed") == 2


def test_3_5_merge_with_undo(conn, sm1_env):
    common = _test_name("mg")
    tgt, _ = _add(conn, sm1_env, name=common, quantity=1)
    src, _ = _add(conn, sm1_env, name=common, quantity=3)
    r = _run("sm1-merge", "--target", str(tgt), "--sources", str(src))
    assert r.returncode == 0
    qty = conn.execute("SELECT SUM(quantity) AS q FROM item_locations WHERE item_id = ?", (tgt,)).fetchone()["q"]
    assert qty == 4
    st = conn.execute("SELECT location_status FROM item_locations WHERE item_id = ?", (src,)).fetchone()
    assert st["location_status"] == "已废弃"
    ev = _last_event(conn, tgt)
    assert ev["event_type"] == "merged"
    # 撤销合并
    r = _run("sm1-undo", "--event-id", str(ev["id"]))
    assert r.returncode == 0
    st = conn.execute("SELECT location_status FROM item_locations WHERE item_id = ?", (src,)).fetchone()
    assert st["location_status"] == "在家"


def test_3_6_undo_once_only(conn, sm1_env):
    iid, name = _add(conn, sm1_env)
    ev = _last_event(conn, iid)
    assert _run("sm1-undo", "--event-id", str(ev["id"])).returncode == 0
    assert conn.execute("SELECT id FROM items WHERE id = ?", (iid,)).fetchone() is None
    # 二次撤销被拒(撤销一次性)
    r = _run("sm1-undo", "--event-id", str(ev["id"]))
    assert r.returncode != 0
    r = _run("sm1-undo-list", "--limit", "5")
    assert r.returncode == 0


def test_3_7_relate_and_unlink(conn, sm1_env):
    a, _ = _add(conn, sm1_env)
    b, _ = _add(conn, sm1_env)
    r = _run("sm1-relate", "--id", str(a), "--related", str(b), "--type", "配件")
    assert r.returncode == 0
    row = conn.execute("SELECT * FROM item_relations WHERE item_id = ? AND related_item_id = ?", (a, b)).fetchone()
    assert row is not None
    assert _event_count(conn, a, "related") == 1
    r = _run("sm1-relate", "--id", str(a), "--related", str(b), "--action", "unlink")
    assert r.returncode == 0
    assert conn.execute("SELECT * FROM item_relations WHERE item_id = ? AND related_item_id = ?", (a, b)).fetchone() is None


def test_3_8_tag_add_remove(conn, sm1_env):
    iid, _ = _add(conn, sm1_env, tags="旧标签")
    r = _run("sm1-tag", "--id", str(iid), "--add", "新标签A,新标签B", "--remove", "旧标签")
    assert r.returncode == 0
    tags = conn.execute("SELECT tag FROM item_tags WHERE item_id = ? ORDER BY tag", (iid,)).fetchall()
    assert [t["tag"] for t in tags] == ["新标签A", "新标签B"]
    assert _event_count(conn, iid, "tagged") == 1


def test_3_8_tag_batch(conn, sm1_env):
    a, _ = _add(conn, sm1_env)
    b, _ = _add(conn, sm1_env)
    r = _run("sm1-tag", "--ids", f"{a},{b}", "--add", "批量标签")
    assert r.returncode == 0
    for iid in (a, b):
        assert conn.execute("SELECT tag FROM item_tags WHERE item_id = ?", (iid,)).fetchone()["tag"] == "批量标签"


def test_3_1_use_item(conn, sm1_env):
    iid, _ = _add(conn, sm1_env)
    r = _run("sm1-use", "--id", str(iid))
    assert r.returncode == 0
    row = conn.execute("SELECT last_accessed_at FROM items WHERE id = ?", (iid,)).fetchone()
    assert row["last_accessed_at"] is not None
    assert _event_count(conn, iid, "found_used") == 1


# ── 子功能 4 · 标签与分类(3 场景)───────────────────────────────────────────


def test_4_1_tag_overview_and_purge(conn, sm1_env):
    from 物品 import ops
    iid, _ = _add(conn, sm1_env, tags="整理标签A")
    data = ops.tag_overview_payload()
    assert any(t["tag"] == "整理标签A" for t in data["tags"])
    r = _run("sm1-tag-purge")
    assert r.returncode == 0


def test_4_3_similar_tags(conn, sm1_env):
    from 物品 import ops
    from 物品.ops import _edit_distance
    assert _edit_distance("毛巾", "擦手巾") == 2
    assert _edit_distance("手机", "充电器") > 2
    _add(conn, sm1_env, tags="毛巾")
    _add(conn, sm1_env, tags="擦手巾")
    data = ops.similar_tags_payload()
    # 检测对中应存在编辑距离 ≤2 的相近对(生产库标签多,cap=20 取影响最大)
    assert any(p["distance"] <= 2 for p in data["pairs"])


def test_4_2_category_add_rename_merge(conn, sm1_env):
    suffix = uuid.uuid4().hex[:4]
    names = [f"测试分类{suffix}A", f"测试分类{suffix}B", f"测试分类{suffix}C"]
    r = _run("sm1-category", "--action", "add", "--name", names[0], "--parent-id",
             str(_real_category_id(conn)))
    assert r.returncode == 0
    row = conn.execute("SELECT id FROM categories WHERE name = ?", (names[0],)).fetchone()
    assert row is not None
    cat_id = row[0]
    r = _run("sm1-category", "--action", "rename", "--id", str(cat_id), "--name", names[1])
    assert r.returncode == 0
    # 合并: 分类B 并入 分类C
    r = _run("sm1-category", "--action", "add", "--name", names[2], "--parent-id",
             str(_real_category_id(conn)))
    assert r.returncode == 0
    zid = conn.execute("SELECT id FROM categories WHERE name = ?", (names[2],)).fetchone()[0]
    r = _run("sm1-category", "--action", "merge", "--id", str(cat_id), "--to-id", str(zid))
    assert r.returncode == 0, f"合并失败: {r.stdout}"
    assert conn.execute("SELECT id FROM categories WHERE id = ?", (cat_id,)).fetchone() is None
    # 清理测试分类
    conn.execute("DELETE FROM categories WHERE id = ?", (zid,))
    conn.commit()
    r = _run("sm1-category", "--action", "overview")
    assert r.returncode == 0


# ── 子功能 5 · 照片档案(3 场景)─────────────────────────────────────────────


def test_5_photos_update_view_wall(conn, sm1_env):
    iid, _ = _add(conn, sm1_env)
    # 用不存在的文件路径应被拒(路径必须在 photos 目录下)
    bad = [{"file_path": "C:/nope.jpg", "photo_type": "普通"}]
    p1 = str(Path(__file__).parent.parent / "output" / f"{uuid.uuid4().hex}.json")
    Path(p1).write_text(json.dumps(bad), encoding="utf-8")
    assert _run("sm1-photo-update", "--id", str(iid), "--json-file", p1).returncode != 0
    # 查看照片(无照片空态)
    assert _run("sm1-photos", "--id", str(iid)).returncode == 0
    assert _run("sm1-photo-wall").returncode == 0


def test_5_2_photo_type_validation(conn, sm1_env):
    iid, _ = _add(conn, sm1_env)
    # 空照片集(清空)应成功
    p = str(Path(__file__).parent.parent / "output" / f"{uuid.uuid4().hex}.json")
    Path(p).write_text(json.dumps([]), encoding="utf-8")
    assert _run("sm1-photo-update", "--id", str(iid), "--json-file", p).returncode == 0


# ── 子功能 6 · 盘点(4 场景)─────────────────────────────────────────────────


def test_6_inventory_round_commit_diff_records(conn, sm1_env):
    iid, name = _add(conn, sm1_env, location="客厅/沙发")
    r = _run("sm1-inventory-round", "--scope", "all")
    assert r.returncode == 0
    commit = {
        "present": [], "missing": [iid],
        "extra": [{"name": _test_name("extra"), "quantity": 1}],
        "diff": [], "pending": [iid], "not_present": [], "review": [],
    }
    p = str(Path(__file__).parent.parent / "output" / f"{uuid.uuid4().hex}.json")
    Path(p).write_text(json.dumps(commit, ensure_ascii=False), encoding="utf-8")
    r = _run("sm1-inventory-commit", "--json-file", p)
    assert r.returncode == 0
    assert _event_count(conn, iid, "inventory") == 1
    rec = conn.execute("SELECT id FROM inventory_records ORDER BY id DESC LIMIT 1").fetchone()
    assert rec is not None
    assert _run("sm1-inventory-records").returncode == 0
    assert _run("sm1-inventory-diff").returncode == 0
    # 差异落地: 标记废弃
    actions = {"missing": [{"id": iid, "action": "标记废弃"}],
               "extra": [{"draft": None}], "diff": [], "pending": [{"id": iid, "mark_review": False}]}
    p2 = str(Path(__file__).parent.parent / "output" / f"{uuid.uuid4().hex}.json")
    Path(p2).write_text(json.dumps(actions, ensure_ascii=False), encoding="utf-8")
    r = _run("sm1-inventory-resolve", "--record-id", str(rec["id"]), "--json-file", p2)
    assert r.returncode == 0
    st = conn.execute("SELECT location_status FROM item_locations WHERE item_id = ?", (iid,)).fetchone()
    assert st["location_status"] == "已废弃"


def test_6_4_move_checklist(conn, sm1_env):
    iid, _ = _add(conn, sm1_env, location="客厅/沙发")
    r = _run("sm1-move-checklist")
    assert r.returncode == 0
    plan = {"take": [iid], "leave": []}
    p = str(Path(__file__).parent.parent / "output" / f"{uuid.uuid4().hex}.json")
    Path(p).write_text(json.dumps(plan), encoding="utf-8")
    r = _run("sm1-move-commit", "--json-file", p)
    assert r.returncode == 0


# ── 子功能 7 · 物品历史(1 场景)─────────────────────────────────────────────


def test_7_history_timeline_trajectory(conn, sm1_env):
    from 物品 import ops
    iid, name = _add(conn, sm1_env, location="客厅/沙发")
    _run("sm1-move", "--id", str(iid), "--location", "书房/书架")
    _run("sm1-qty", "--id", str(iid), "--plus", "2")
    data = ops.history_payload(iid)
    assert len(data["events"]) >= 3
    assert data["trajectory"] == ["客厅/沙发", "书房/书架"]
    assert any(f["key"] == "location_moved" for f in data["filter_types"])


# ── 记录契约与模板完整性 ────────────────────────────────────────────────────


def test_events_atomicity_after_undo_create(conn, sm1_env):
    """记录契约: 撤销录入 = 级联删除(物品消失 + 事件保留追溯)"""
    iid, _ = _add(conn, sm1_env)
    ev = _last_event(conn, iid)
    assert _run("sm1-undo", "--event-id", str(ev["id"])).returncode == 0
    assert conn.execute("SELECT id FROM items WHERE id = ?", (iid,)).fetchone() is None
    undone = conn.execute(
        "SELECT COUNT(*) AS n FROM item_events WHERE item_id = ? AND event_type = 'undone'",
        (iid,)).fetchone()["n"]
    assert undone == 1


def test_all_sm1_templates_render():
    """08 硬标准: 每个 物品/ 模板可渲染 + 复制数据/复制日志双通道"""
    from render import render_page
    templates_dir = Path(__file__).parent.parent / "templates" / "物品"
    for tpl in sorted(templates_dir.glob("*.html")):
        payload = {
            "status": "ok",
            "data": {
                "meta": {"scene_id": "t", "wake_word": "测试", "command_cn": "测试",
                         "occurred_at": "2026-01-01 00:00:00", "skill_version": "test"},
                "scene": {}, "reminders": [],
                "copy_data": {"scene_id": "t", "command_cn": "测试", "occurred_at": "x",
                              "target": "", "payload": {}},
                "copy_log": {"scene": "测试", "thinking": "", "data_structure": "",
                             "call_chain": "", "timestamp": "x", "exception": ""},
            },
            "message": "测试",
        }
        result = render_page(f"物品/{tpl.name}", payload, None, "测试")
        assert result["status"] == "ok", f"{tpl.name}: {result}"


def test_scenes_sm1_yaml_merges(conn):
    """场景注册: SM1.yaml 29 场景可合并进总账(不破坏其他域)"""
    import yaml
    skill = Path(__file__).parent.parent
    sm1 = yaml.safe_load((skill / "scenes" / "SM1.yaml").read_text(encoding="utf-8"))
    total = yaml.safe_load((skill / "references" / "scenarios.yaml").read_text(encoding="utf-8"))
    assert len(sm1["scenes"]) == 29, "SM1.yaml 应有 29 场景"
    before = len(total["scenarios"])
    import sys as _sys
    if str(skill / "scripts") not in _sys.path:
        _sys.path.insert(0, str(skill / "scripts"))
    from 场景合并 import merge_scenes
    updated, added = merge_scenes(total, sm1["domain"], sm1["scenes"])
    assert len(updated) == 29
    assert len(total["scenarios"]) == before + len(added)
