"""SM7 家庭协作域测试(fixture 临时库 · 不碰生产库)

覆盖场景: 借用管理(借出/借入/归还/催还/超期)+ 家人档案(成员/归属标记)
seam: scripts/家庭协作/family_ops.py 公共函数(注入 conn)
"""
import sqlite3
from datetime import date, timedelta

import pytest

from 家庭协作 import family_ops

TODAY = date(2026, 8, 5)


@pytest.fixture
def fam_db(tmp_path):
    """临时独立库(种子 items/item_locations 最小结构 + family 表)"""
    conn = sqlite3.connect(str(tmp_path / "test_family.db"))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("""
        CREATE TABLE items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            owner TEXT DEFAULT '使用者',
            photo TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE item_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            location TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            location_status TEXT DEFAULT '在家',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    yield conn
    conn.close()


def _seed_item(conn, name="锯子", owner="使用者", status="在家"):
    cur = conn.cursor()
    cur.execute("INSERT INTO items (name, owner) VALUES (?, ?)", (name, owner))
    item_id = cur.lastrowid
    cur.execute(
        "INSERT INTO item_locations (item_id, location, quantity, location_status) VALUES (?, ?, 1, ?)",
        (item_id, "车库/工具柜", status),
    )
    conn.commit()
    return item_id


# ── 家人档案 · 成员 ──────────────────────────────────────────────────────


def test_member_add_returns_id_and_name(fam_db):
    m = family_ops.member_add(fam_db, "老王", relation="邻居", note="楼下大哥")
    assert m["name"] == "老王"
    assert m["relation"] == "邻居"
    assert m["note"] == "楼下大哥"
    assert m["id"] > 0


def test_member_add_duplicate_name_rejected(fam_db):
    family_ops.member_add(fam_db, "老王")
    with pytest.raises(ValueError):
        family_ops.member_add(fam_db, "老王")


def test_member_list_returns_all_members(fam_db):
    family_ops.member_add(fam_db, "妈妈")
    family_ops.member_add(fam_db, "宝宝")
    members = family_ops.member_list(fam_db)
    assert [m["name"] for m in members] == ["妈妈", "宝宝"]


def test_member_list_item_count_counts_owned_items(fam_db):
    family_ops.member_add(fam_db, "妈妈")
    family_ops.member_add(fam_db, "宝宝")
    _seed_item(fam_db, "毛衣", owner="妈妈")
    _seed_item(fam_db, "围巾", owner="妈妈")
    _seed_item(fam_db, "绘本", owner="宝宝")
    members = {m["name"]: m for m in family_ops.member_list(fam_db)}
    assert members["妈妈"]["item_count"] == 2
    assert members["宝宝"]["item_count"] == 1


def test_member_remove_reassigns_items_back_to_owner(fam_db):
    family_ops.member_add(fam_db, "老王")
    _seed_item(fam_db, "锯子", owner="老王")
    _seed_item(fam_db, "锤子", owner="老王")
    result = family_ops.member_remove(fam_db, "老王")
    assert result["reassigned"] == 2
    rows = fam_db.execute("SELECT owner FROM items").fetchall()
    assert all(r["owner"] == "使用者" for r in rows)
    assert family_ops.member_list(fam_db) == []


def test_member_remove_unknown_rejected(fam_db):
    with pytest.raises(ValueError):
        family_ops.member_remove(fam_db, "不存在的人")


# ── 家人档案 · 物品归属标记 ───────────────────────────────────────────────


def test_member_assign_marks_item_owner(fam_db):
    family_ops.member_add(fam_db, "妈妈")
    i1 = _seed_item(fam_db, "毛衣")
    i2 = _seed_item(fam_db, "围巾")
    n = family_ops.member_assign(fam_db, "妈妈", [i1, i2])
    assert n == 2
    rows = fam_db.execute("SELECT name, owner FROM items ORDER BY id").fetchall()
    assert [(r["name"], r["owner"]) for r in rows] == [("毛衣", "妈妈"), ("围巾", "妈妈")]


def test_member_assign_unknown_member_rejected(fam_db):
    i1 = _seed_item(fam_db, "毛衣")
    with pytest.raises(ValueError):
        family_ops.member_assign(fam_db, "不存在的人", [i1])


def test_member_assign_unknown_item_skipped(fam_db):
    family_ops.member_add(fam_db, "妈妈")
    n = family_ops.member_assign(fam_db, "妈妈", [99999])
    assert n == 0


# ── 借用管理 · 借出 ───────────────────────────────────────────────────────


def test_borrow_add_borrow_out_sets_item_status(fam_db):
    i1 = _seed_item(fam_db, "锯子")
    r = family_ops.borrow_add(fam_db, direction="借出", item_id=i1, object_name="老王",
                              borrowed_at="2026-08-01", due_date="2026-08-10")
    assert r["direction"] == "借出"
    assert r["item_name"] == "锯子"
    assert r["object_name"] == "老王"
    status = fam_db.execute(
        "SELECT location_status FROM item_locations WHERE item_id = ?", (i1,)
    ).fetchone()["location_status"]
    assert status == "借用中"


def test_borrow_add_borrow_out_without_item_id_rejected(fam_db):
    with pytest.raises(ValueError):
        family_ops.borrow_add(fam_db, direction="借出", item_id=None,
                              item_name="锯子", object_name="老王")


def test_borrow_add_rejects_scrapped_item(fam_db):
    i1 = _seed_item(fam_db, "坏锯子", status="已废弃")
    with pytest.raises(ValueError):
        family_ops.borrow_add(fam_db, direction="借出", item_id=i1, object_name="老王")


def test_borrow_add_rejects_already_borrowed_item(fam_db):
    i1 = _seed_item(fam_db, "锯子", status="借用中")
    with pytest.raises(ValueError):
        family_ops.borrow_add(fam_db, direction="借出", item_id=i1, object_name="老王")


def test_borrow_add_invalid_direction_rejected(fam_db):
    with pytest.raises(ValueError):
        family_ops.borrow_add(fam_db, direction="交换", item_name="锯子", object_name="老王")


# ── 借用管理 · 借入 ───────────────────────────────────────────────────────


def test_borrow_add_borrow_in_free_text_no_item(fam_db):
    r = family_ops.borrow_add(fam_db, direction="借入", item_name="电钻",
                              object_name="老王", borrowed_at="2026-07-20")
    assert r["item_id"] is None
    assert r["item_name"] == "电钻"


def test_borrow_add_borrow_in_keeps_item_status(fam_db):
    i1 = _seed_item(fam_db, "梯子")
    family_ops.borrow_add(fam_db, direction="借入", item_id=i1, object_name="老王")
    status = fam_db.execute(
        "SELECT location_status FROM item_locations WHERE item_id = ?", (i1,)
    ).fetchone()["location_status"]
    assert status == "在家"


def test_borrow_add_missing_item_name_rejected(fam_db):
    with pytest.raises(ValueError):
        family_ops.borrow_add(fam_db, direction="借入", item_name="", object_name="老王")


# ── 借用管理 · 归还 ───────────────────────────────────────────────────────


def test_borrow_return_marks_returned_and_restores_status(fam_db):
    i1 = _seed_item(fam_db, "锯子")
    r = family_ops.borrow_add(fam_db, direction="借出", item_id=i1, object_name="老王",
                              borrowed_at="2026-08-01", due_date="2026-08-10")
    ret = family_ops.borrow_return(fam_db, r["id"], returned_at="2026-08-05")
    assert ret["returned_at"] == "2026-08-05"
    status = fam_db.execute(
        "SELECT location_status FROM item_locations WHERE item_id = ?", (i1,)
    ).fetchone()["location_status"]
    assert status == "在家"


def test_borrow_return_borrow_in_does_not_touch_items(fam_db):
    r = family_ops.borrow_add(fam_db, direction="借入", item_name="电钻", object_name="老王")
    ret = family_ops.borrow_return(fam_db, r["id"])
    assert ret["returned_at"] is not None


def test_borrow_return_twice_rejected(fam_db):
    r = family_ops.borrow_add(fam_db, direction="借入", item_name="电钻", object_name="老王")
    family_ops.borrow_return(fam_db, r["id"])
    with pytest.raises(ValueError):
        family_ops.borrow_return(fam_db, r["id"])


def test_borrow_return_unknown_rejected(fam_db):
    with pytest.raises(ValueError):
        family_ops.borrow_return(fam_db, 99999)


# ── 借用管理 · 超期计算 ────────────────────────────────────────────────────


def test_overdue_days_positive_when_past_due(fam_db):
    i1 = _seed_item(fam_db, "锯子")
    r = family_ops.borrow_add(fam_db, direction="借出", item_id=i1, object_name="老王",
                              borrowed_at="2026-07-01", due_date="2026-07-10")
    status, days = family_ops.borrow_status(r, today=TODAY)
    assert status == "已超期 26 天"
    assert days == 26


def test_due_today_status(fam_db):
    r = family_ops.borrow_add(fam_db, direction="借入", item_name="电钻",
                              object_name="老王", borrowed_at="2026-08-01", due_date="2026-08-05")
    status, days = family_ops.borrow_status(r, today=TODAY)
    assert status == "今日到期"


def test_on_time_status(fam_db):
    r = family_ops.borrow_add(fam_db, direction="借入", item_name="电钻",
                              object_name="老王", borrowed_at="2026-08-01", due_date="2026-08-10")
    status, days = family_ops.borrow_status(r, today=TODAY)
    assert status == "借用中"


def test_no_due_date_never_overdue(fam_db):
    r = family_ops.borrow_add(fam_db, direction="借入", item_name="电钻",
                              object_name="老王", borrowed_at="2026-01-01")
    status, days = family_ops.borrow_status(r, today=TODAY)
    assert status == "借用中"


def test_days_borrowed_counts_from_borrowed_at(fam_db):
    r = family_ops.borrow_add(fam_db, direction="借入", item_name="电钻",
                              object_name="老王", borrowed_at="2026-07-20")
    assert r["days_borrowed"] == 16


# ── 借用管理 · 催还文案 ────────────────────────────────────────────────────


def test_remind_borrow_out_overdue(fam_db):
    i1 = _seed_item(fam_db, "锯子")
    r = family_ops.borrow_add(fam_db, direction="借出", item_id=i1,
                              object_name="老王", borrowed_at="2026-07-01", due_date="2026-07-10")
    text = family_ops.remind_text(r, today=TODAY)
    assert text == "老王,之前借的锯子已经借了35天了,方便还一下吗?"


def test_remind_borrow_out_due_today(fam_db):
    i1 = _seed_item(fam_db, "锯子")
    r = family_ops.borrow_add(fam_db, direction="借出", item_id=i1,
                              object_name="老王", borrowed_at="2026-08-01", due_date="2026-08-05")
    text = family_ops.remind_text(r, today=TODAY)
    assert text == "老王,之前借的锯子今天到归还日了,方便还一下吗?"


def test_remind_borrow_in_on_time(fam_db):
    r = family_ops.borrow_add(fam_db, direction="借入", item_name="电钻",
                              object_name="老王", borrowed_at="2026-08-01", due_date="2026-08-10")
    text = family_ops.remind_text(r, today=TODAY)
    assert text == "老王,之前借的电钻约定2026-08-10号归还,我记着呢"


# ── 借用管理 · 清单与 payload ──────────────────────────────────────────────


def test_borrow_list_splits_direction_and_computes_status(fam_db):
    i1 = _seed_item(fam_db, "锯子")
    family_ops.borrow_add(fam_db, direction="借出", item_id=i1,
                          object_name="老王", borrowed_at="2026-07-01", due_date="2026-07-10")
    family_ops.borrow_add(fam_db, direction="借入", item_name="电钻", object_name="老王",
                          borrowed_at="2026-08-01", due_date="2026-08-10")
    out, inn = family_ops.borrow_list(fam_db, today=TODAY)
    assert [x["item_name"] for x in out] == ["锯子"]
    assert out[0]["status"] == "已超期 26 天"
    assert [x["item_name"] for x in inn] == ["电钻"]
    assert inn[0]["status"] == "借用中"


def test_borrow_list_payload_shape_for_template(fam_db):
    i1 = _seed_item(fam_db, "锯子")
    family_ops.borrow_add(fam_db, direction="借出", item_id=i1,
                          object_name="老王", borrowed_at="2026-07-01", due_date="2026-07-10")
    payload = family_ops.borrow_list_payload(fam_db, today=TODAY)
    assert payload["status"] == "ok"
    data = payload["data"]
    assert set(data) >= {"summary", "borrowed_out", "borrowed_in", "overdue_count", "members"}
    assert data["overdue_count"] == 1
    assert data["summary"]["title"] == "借用管理"


def test_member_list_payload_shape_for_template(fam_db):
    family_ops.member_add(fam_db, "妈妈", relation="家人")
    payload = family_ops.member_list_payload(fam_db)
    assert payload["status"] == "ok"
    data = payload["data"]
    assert set(data) >= {"summary", "members", "total_items"}
    assert data["members"][0]["name"] == "妈妈"
    assert data["members"][0]["relation"] == "家人"
    assert data["members"][0]["item_count"] == 0
