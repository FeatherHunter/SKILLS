# __init__.py - home_manager 包导出（兼容原 import 路径）
from .item_ops import add_item, search_items, update_item, list_items, item_detail
from .inventory_ops import inventory, stats
from .tag_ops import tag_merge, list_tags
from .db import init_db, get_conn
