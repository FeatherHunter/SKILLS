#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_body_photo_gallery.py — 看身材照 gallery 体积预算 + 缺失标记回归(issue #51 · 2026-08-09)

现象(issue #51):
- Bug 1:查身材照 HTML 中部分图片显示"已丢失"(DB 记录引用文件不存在)
- Bug 2:身材照多时 HTML 体积过大,飞书发不出去(全量 base64 内嵌)

修复:
- Bug 2:embed 累计超 MAX_EMBED_BYTES 后,剩余照片标 embed_skipped(前端显示"未嵌入"),
  整页体积可控 → 保证飞书能发。
- Bug 1:文件缺失 → file_exists=false + 前端"照片数据不存在"明确标记(V4 退化方案)。

本测试锁住:三态渲染契约(missing / skipped / embedded)+ 预算截断行为。
"""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))

# 单张 embed 后体积:造一张真实小图验证累计预算
def _make_jpg(path: Path, px=80, quality=30):
    """PIL 造一张小 JPEG(可反复调用)"""
    from PIL import Image
    img = Image.new('RGB', (px, px), (120, 60, 40))
    img.save(path, format='JPEG', quality=quality)


@pytest.fixture()
def photo_env(temp_db, monkeypatch):
    """临时照片目录 + DB 记录(3 张:2 张存在文件 + 1 张引用缺失文件)"""
    import sqlite3

    photos_dir = temp_db.parent / 'caloriehub_test'
    photos_dir.mkdir(exist_ok=True)
    monkeypatch.setenv('CALORIE_PHOTOS_DIR', str(photos_dir))

    _make_jpg(photos_dir / '2026-08-01_001.jpg')
    _make_jpg(photos_dir / '2026-08-02_001.jpg')

    conn = sqlite3.connect(str(temp_db))
    conn.execute("INSERT INTO body_photos (date, time, photo_path, tag, note) VALUES ('2026-08-01','10:00:00','2026-08-01_001.jpg','正面','第一张')")
    conn.execute("INSERT INTO body_photos (date, time, photo_path, tag, note) VALUES ('2026-08-02','10:00:00','2026-08-02_001.jpg','侧面','第二张')")
    conn.execute("INSERT INTO body_photos (date, time, photo_path, tag, note) VALUES ('2026-08-03','10:00:00','2026-08-03_001.jpg','正面','第三张(文件不存在)')")
    conn.commit()
    conn.close()
    yield photos_dir


def _build(photo_env, **kw):
    import render_body_photo_gallery as g
    return g.build(None, None, None, **kw)


def test_gallery_embeds_existing_files(photo_env):
    """Bug 2 基础:存在的文件被 base64 嵌入,缺失的文件标 file_exists=false"""
    data = _build(photo_env)
    photos = data['data']['photos']
    by_path = {p['photo_path']: p for p in photos}
    assert by_path['2026-08-01_001.jpg']['photo_data_base64'].startswith('data:image/jpeg')
    assert by_path['2026-08-02_001.jpg']['photo_data_base64'].startswith('data:image/jpeg')
    # 缺失文件:不 embed + file_exists=false
    missing = by_path['2026-08-03_001.jpg']
    assert 'photo_data_base64' not in missing
    assert missing['file_exists'] is False
    # 无 skip(预算未耗尽)
    assert data['data']['meta']['embed_skipped_count'] == 0


def test_gallery_marks_skipped_when_budget_exceeded(photo_env):
    """Bug 2 核心:预算耗尽后剩余照片标 embed_skipped,不产生 broken"""
    data = _build(photo_env, max_embed_bytes=1024)  # 1KB 预算,第一张就超
    photos = data['data']['photos']
    # 预算很小 → 至少一张被 skip(按倒序 8/3 缺失不算,8/2 或 8/1 会被截)
    skipped = [p for p in photos if p.get('embed_skipped')]
    embedded = [p for p in photos if p.get('photo_data_base64')]
    assert skipped, '预算耗尽后必须有照片被标 skipped'
    assert embedded, '预算内应有照片被嵌入'
    # 被 skip 的照片:文件存在(不是缺失)但不 embed
    for p in skipped:
        assert p['file_exists'] is True
        assert 'photo_data_base64' not in p
    assert data['data']['meta']['embed_skipped_count'] == len(skipped)


def test_gallery_budget_meta_reported(photo_env):
    """meta 必须带预算信息(前端横幅依赖)"""
    data = _build(photo_env, max_embed_bytes=2048)
    meta = data['data']['meta']
    assert meta['embed_budget_bytes'] == 2048
    assert 'embed_skipped_count' in meta


def test_gallery_file_missing_flag_contract(photo_env):
    """Bug 1 契约:缺失照片必须带 file_exists=false,供前端显示"照片数据不存在" """
    data = _build(photo_env)
    photos = {p['photo_path']: p for p in data['data']['photos']}
    assert photos['2026-08-03_001.jpg']['file_exists'] is False
    # 每张照片都有 id/date 供前端展示
    assert photos['2026-08-03_001.jpg']['date'] == '2026-08-03'
