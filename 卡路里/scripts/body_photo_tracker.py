#!/usr/bin/env python3
"""
身材照片记录 - CLI工具
支持添加、查询、删除、修改标签、生成GIF
"""

import argparse
import os
import sys
import shutil
from datetime import datetime, date
from pathlib import Path

from db_utils import find_db_path, get_db as _get_db_conn

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

SKILL_DIR = Path(__file__).parent.parent
DB_FILENAME = "calorie_data.db"
DB_PATH = find_db_path(SKILL_DIR, DB_FILENAME)


def get_photos_dir():
    """获取照片存储目录，未配置则报错退出"""
    photos_dir = os.environ.get('CALORIE_PHOTOS_DIR')
    if not photos_dir:
        print("Error: 环境变量 CALORIE_PHOTOS_DIR 未配置")
        print("请设置环境变量指向照片存储目录，例如：")
        print("  export CALORIE_PHOTOS_DIR=/path/to/photos")
        sys.exit(1)

    path = Path(photos_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_db():
    """获取数据库连接"""
    return _get_db_conn(DB_PATH)


if __name__ == '__main__':
    # 基础入口 - 后续会扩展 argparse
    photos_dir = get_photos_dir()
    print(f"照片目录: {photos_dir}")
