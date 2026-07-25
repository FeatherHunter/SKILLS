#!/usr/bin/env python3
"""body_photo_tracker.generate_gif v2.3.0 pytest 风格测试套

覆盖:
  · 默认参数生成
  · 显式 --photo-id 顺序
  · --crops JSON 裁剪
  · --watermark 水印
  · --transition fade/dissolve
  · 错误: --crops JSON 格式错
  · 错误: 指定 photo-id 不存在
"""

import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR / "scripts"))


@pytest.fixture
def photo_env():
    """建临时 DB + 临时照片目录 + 2 张 mock 照片 + monkey-patch"""
    fd_db, tmp_db = tempfile.mkstemp(suffix=".db")
    os.close(fd_db)

    # 建表 + 插 2 条
    conn = sqlite3.connect(tmp_db)
    conn.executescript("""
        CREATE TABLE body_photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            photo_path TEXT NOT NULL,
            tag TEXT NOT NULL,
            note TEXT NOT NULL
        );
    """)
    # 临时照片目录
    tmp_photos = tempfile.mkdtemp()
    img1_path = Path(tmp_photos) / "2026-07-01_front.jpg"
    img2_path = Path(tmp_photos) / "2026-07-15_front.jpg"
    Image.new('RGB', (800, 1200), (200, 100, 50)).save(img1_path)
    Image.new('RGB', (800, 1200), (50, 100, 200)).save(img2_path)

    conn.execute("INSERT INTO body_photos VALUES (?, ?, ?, ?, ?, ?)",
                 (1, "2026-07-01", "10:00:00", str(img1_path), "front", ""))
    conn.execute("INSERT INTO body_photos VALUES (?, ?, ?, ?, ?, ?)",
                 (2, "2026-07-15", "10:00:00", str(img2_path), "front", ""))
    conn.commit()
    conn.close()

    # monkey-patch: 让 generate_gif 用我们的临时 DB / photos dir
    import body_photo_tracker as bpt

    orig_init_db = bpt._init_db
    orig_get_db = bpt.get_db

    def _mock_get_db():
        return sqlite3.connect(tmp_db)

    bpt.get_db = _mock_get_db
    bpt._init_db = lambda *a, **kw: None  # 跳过

    # photos_dir patch: 让 generate_gif 用 tmp_photos
    def _mock_get_photos_dir():
        return Path(tmp_photos)

    bpt.get_photos_dir = _mock_get_photos_dir

    yield {
        'db': tmp_db,
        'photos_dir': Path(tmp_photos),
        'gif_dir': Path(tmp_photos) / "gifs",
        'img1': img1_path,
        'img2': img2_path,
    }

    bpt.get_db = orig_get_db
    bpt._init_db = orig_init_db
    os.unlink(tmp_db)
    import shutil
    shutil.rmtree(tmp_photos, ignore_errors=True)


def test_gif_default_params(photo_env):
    """默认参数生成 GIF(cut 过渡)"""
    import body_photo_tracker as bpt
    result = bpt.generate_gif(
        tag='front', days=60,
    )
    assert result is not None
    assert result.exists()
    # 默认 cut 过渡,2 张图 = 2 帧
    img = Image.open(result)
    assert img.n_frames == 2


def test_gif_explicit_photo_ids_order(photo_env):
    """--photo-id 显式按顺序(ID=2 先,ID=1 后)"""
    import body_photo_tracker as bpt
    result = bpt.generate_gif(
        tag='front', days=60,
        photo_ids=[2, 1],  # 显式顺序
    )
    assert result is not None
    assert result.exists()


def test_gif_crops_json(photo_env):
    """--crops JSON 单独裁剪每张"""
    import body_photo_tracker as bpt
    crops = json.dumps({
        "1": [100, 200, 600, 900],   # ID=1 裁剪到 100-600,200-900
        "2": [50, 150, 700, 1000],
    })
    result = bpt.generate_gif(
        tag='front', days=60,
        photo_ids=[1, 2],
        crops_json=crops,
        width=400, height=600,
    )
    assert result is not None
    img = Image.open(result)
    # 裁剪后是 400x600
    assert img.size == (400, 600)


def test_gif_watermark(photo_env):
    """--watermark 文字水印"""
    import body_photo_tracker as bpt
    result = bpt.generate_gif(
        tag='front', days=60,
        watermark="减脂 30 天",
    )
    assert result is not None


def test_gif_fade_transition(photo_env):
    """--transition fade 渐变"""
    import body_photo_tracker as bpt
    result = bpt.generate_gif(
        tag='front', days=60,
        transition='fade',
    )
    assert result is not None
    img = Image.open(result)
    # 2 张 + 10 步渐变 = 1 + 10 + 1 = 12 帧(PIL 可能合并最后一帧)
    assert img.n_frames >= 11


def test_gif_invalid_crops_json(photo_env):
    """--crops JSON 格式错应报错"""
    import body_photo_tracker as bpt
    result = bpt.generate_gif(
        tag='front', days=60,
        crops_json='{invalid json',
    )
    assert result is None  # 报错返回 None


def test_gif_photo_id_not_exist(photo_env):
    """指定 photo-id 不存在应报错"""
    import body_photo_tracker as bpt
    result = bpt.generate_gif(
        tag='front', days=60,
        photo_ids=[999],  # 不存在
    )
    assert result is None  # 0 行


def test_gif_dissolve_transition(photo_env):
    """--transition dissolve"""
    import body_photo_tracker as bpt
    result = bpt.generate_gif(
        tag='front', days=60,
        transition='dissolve',
    )
    assert result is not None
    img = Image.open(result)
    # dissolve 5 步 → 1 + 5 + 1 = 7 帧(PIL 可能合并)
    assert img.n_frames >= 6