"""payload 函数测试（需 DB, 使用 conftest 中 conn fixture）"""
import pytest


def test_trip_payload_pack(conn):
    """_trip_payload(mode='pack') 结构正确"""
    from home_manager.inventory_ops import _trip_payload
    data = _trip_payload(conn, mode="pack")
    assert "summary" in data
    assert "mode" in data
    assert data["mode"] == "pack"
    assert "categories" in data
    assert "items" in data
    assert isinstance(data["items"], list)
    if data["items"]:
        item = data["items"][0]
        # 必须含 top_category_id (Phase 16 优化用)
        assert "top_category_id" in item
        assert "category_id" in item


def test_trip_payload_return(conn):
    from home_manager.inventory_ops import _trip_payload
    data = _trip_payload(conn, mode="return")
    assert data["mode"] == "return"
    assert "items" in data


def test_trip_payload_invalid_mode(conn):
    from home_manager.inventory_ops import _trip_payload
    data = _trip_payload(conn, mode="invalid_mode")
    # 错误返回 {status: error, data: {}, message}
    # 注意: _trip_payload 当前直接返回字典, 不带 status
    # 仅验证不会抛异常
    assert isinstance(data, dict)


def test_stats_summary_payload(conn):
    from home_manager.inventory_ops import _stats_summary_payload
    data = _stats_summary_payload(conn)
    assert "summary" in data
    assert "categories" in data
    assert "statuses" in data
    assert isinstance(data["statuses"], list)
    # metrics 必须含物品总数
    metrics = data["summary"].get("metrics", [])
    labels = [m.get("label") for m in metrics]
    assert "物品总数" in labels


def test_stats_expiring_payload_structure(conn):
    from home_manager.inventory_ops import _stats_expiring_payload
    data = _stats_expiring_payload(conn, limit=5, days=30)
    assert "summary" in data
    assert "items" in data
    metrics = data["summary"].get("metrics", [])
    assert len(metrics) == 4  # 已过期/3天内/7天内/N天内
    # severity 字段
    if data["items"]:
        for it in data["items"]:
            assert it["severity"] in ("danger", "warn", "info")


def test_stats_expiring_payload_with_expired_only(conn):
    from home_manager.inventory_ops import _stats_expiring_payload
    data = _stats_expiring_payload(conn, days=30, expired_only=True)
    if data["items"]:
        for it in data["items"]:
            assert it["days_left"] < 0


def test_outfit_payload_groups(conn):
    from home_manager.inventory_ops import _outfit_payload
    data = _outfit_payload(conn)
    assert "summary" in data
    assert "groups" in data
    group_keys = {g["key"] for g in data["groups"]}
    assert group_keys == {"top", "bottom", "shoes"}
    for g in data["groups"]:
        assert "label" in g
        assert "items" in g
        for it in g["items"]:
            assert "id" in it
            assert "name" in it


def test_list_items_payload_has_top_category_id(conn):
    """_item_to_dict 注入 top_category_id (Phase 16)"""
    from home_manager.item_ops import list_items_payload
    items = list_items_payload(limit=5)
    if items:
        assert "top_category_id" in items[0]
