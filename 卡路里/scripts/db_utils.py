#!/usr/bin/env python3
"""数据库工具 - 兼容层（转发到 db.py）

旧脚本仍可 `from db_utils import find_db_path, get_db`。
新代码请直接 `from db import ...`。
"""
from db import (
    find_db_path,
    get_db,
    connection,
    init_db,
    DB_FILENAME,
)

__all__ = ['find_db_path', 'get_db', 'connection', 'init_db', 'DB_FILENAME']