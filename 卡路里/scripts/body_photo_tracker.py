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


def init_table():
    """初始化身材照片表"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS body_photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            photo_path TEXT NOT NULL,
            tag TEXT NOT NULL,
            note TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_body_photos_date ON body_photos(date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_body_photos_tag ON body_photos(tag)")
    conn.commit()
    conn.close()


def add_photos(photo_paths, tag, note=''):
    """添加照片记录"""
    photos_dir = get_photos_dir()
    today = date.today().isoformat()
    now = datetime.now().strftime("%H:%M:%S")

    # 获取今天的照片数量用于生成序号
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM body_photos WHERE date = ?", (today,))
    count = cur.fetchone()[0]
    conn.close()

    added = []
    for i, src_path in enumerate(photo_paths):
        src = Path(src_path)
        if not src.exists():
            print(f"⚠ 文件不存在: {src_path}")
            continue

        # 生成目标文件名
        ext = src.suffix.lower()
        seq = count + i + 1
        dest_name = f"{today}_{seq:03d}{ext}"
        dest_path = photos_dir / dest_name

        # 复制文件
        shutil.copy2(src, dest_path)

        # 写入数据库
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO body_photos (date, time, photo_path, tag, note)
            VALUES (?, ?, ?, ?, ?)
        """, (today, now, dest_name, tag, note))
        photo_id = cur.lastrowid
        conn.commit()
        conn.close()

        added.append((photo_id, dest_name))
        print(f"✓ 已添加照片 #{photo_id}: {dest_name} (标签: {tag})")

    return added


def list_photos(days=7, tag=None):
    """查询照片列表"""
    conn = get_db()
    cur = conn.cursor()

    # 计算起始日期
    from datetime import timedelta
    start_date = (date.today() - timedelta(days=days)).isoformat()

    # 构建查询
    if tag:
        cur.execute("""
            SELECT id, date, time, photo_path, tag, note, created_at
            FROM body_photos
            WHERE date >= ? AND tag = ?
            ORDER BY date DESC, time DESC
        """, (start_date, tag))
    else:
        cur.execute("""
            SELECT id, date, time, photo_path, tag, note, created_at
            FROM body_photos
            WHERE date >= ?
            ORDER BY date DESC, time DESC
        """, (start_date,))

    rows = cur.fetchall()
    conn.close()

    if not rows:
        print(f"最近{days}天没有身材照片记录")
        return []

    print(f"\n身材照片记录（最近{days}天）：{len(rows)}张")
    print("-" * 70)
    print(f"{'ID':>4} | {'日期':>10} | {'时间':>8} | {'标签':>8} | {'文件':20} | 备注")
    print("-" * 70)

    for r in rows:
        photo_id, p_date, p_time, photo_path, p_tag, p_note, created = r
        time_str = p_time[:8] if p_time else ''
        print(f"{photo_id:>4} | {p_date:>10} | {time_str:>8} | {p_tag:>8} | {photo_path:20} | {p_note or ''}")

    print("-" * 70)
    return rows


def delete_photo(photo_id):
    """删除照片"""
    photos_dir = get_photos_dir()

    conn = get_db()
    cur = conn.cursor()

    # 查询照片信息
    cur.execute("SELECT photo_path FROM body_photos WHERE id = ?", (photo_id,))
    row = cur.fetchone()

    if not row:
        print(f"Error: 照片 #{photo_id} 不存在")
        conn.close()
        return False

    photo_path = row[0]

    # 删除数据库记录
    cur.execute("DELETE FROM body_photos WHERE id = ?", (photo_id,))
    conn.commit()
    conn.close()

    # 删除文件
    file_path = photos_dir / photo_path
    if file_path.exists():
        file_path.unlink()
        print(f"✓ 已删除照片 #{photo_id}: {photo_path}")
    else:
        print(f"⚠ 数据库记录已删除，但文件不存在: {photo_path}")

    return True


def update_tag(photo_id, new_tag):
    """修改照片标签"""
    conn = get_db()
    cur = conn.cursor()

    # 检查照片是否存在
    cur.execute("SELECT id FROM body_photos WHERE id = ?", (photo_id,))
    if not cur.fetchone():
        print(f"Error: 照片 #{photo_id} 不存在")
        conn.close()
        return False

    # 更新标签
    cur.execute("UPDATE body_photos SET tag = ? WHERE id = ?", (new_tag, photo_id))
    conn.commit()
    conn.close()

    print(f"✓ 已更新照片 #{photo_id} 标签为: {new_tag}")
    return True


def get_latest_weight():
    """获取最近的体重记录"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT weight_kg, date, time
        FROM weight_log
        ORDER BY created_at DESC
        LIMIT 1
    """)
    row = cur.fetchone()
    conn.close()

    if row:
        return {'weight': row[0], 'date': row[1], 'time': row[2]}
    return None


def generate_gif(tag, start_date=None, end_date=None, days=None, output=None):
    """生成 GIF 变化动画"""
    try:
        from PIL import Image
    except ImportError:
        print("Error: 需要安装 Pillow 库")
        print("请运行: pip install Pillow")
        return None

    photos_dir = get_photos_dir()
    gifs_dir = photos_dir / "gifs"
    gifs_dir.mkdir(exist_ok=True)

    # 计算日期范围
    if start_date and end_date:
        pass
    elif days:
        from datetime import timedelta
        end_date = date.today().isoformat()
        start_date = (date.today() - timedelta(days=days)).isoformat()
    else:
        print("Error: 请指定 --start/--end 或 --days")
        return None

    # 查询照片
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT photo_path, date
        FROM body_photos
        WHERE tag = ? AND date >= ? AND date <= ?
        ORDER BY date ASC, time ASC
    """, (tag, start_date, end_date))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        print(f"未找到标签为 '{tag}' 的照片（{start_date} ~ {end_date}）")
        return None

    # 加载图片
    images = []
    for photo_path, photo_date in rows:
        file_path = photos_dir / photo_path
        if file_path.exists():
            img = Image.open(file_path)
            # 统一尺寸
            img = img.resize((400, 600), Image.Resampling.LANCZOS)
            images.append(img)

    if not images:
        print("没有可用的照片文件")
        return None

    # 生成输出文件名
    if not output:
        output = f"{tag}_{start_date}_{end_date}.gif"

    output_path = gifs_dir / output

    # 生成 GIF
    images[0].save(
        output_path,
        save_all=True,
        append_images=images[1:],
        duration=500,
        loop=0
    )

    print(f"✓ 已生成 GIF: {output_path}")
    print(f"  包含 {len(images)} 张照片")
    return output_path


if __name__ == '__main__':
    photos_dir = get_photos_dir()
    print(f"照片目录: {photos_dir}")

    # 初始化数据库表
    init_table()

    # 验证表是否存在
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='body_photos'")
    result = cur.fetchone()
    conn.close()

    if result:
        print("✓ body_photos 表已创建")
    else:
        print("✗ body_photos 表创建失败")
