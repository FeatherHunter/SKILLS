#!/usr/bin/env python3
"""
身材照片记录 - CLI工具
支持添加、查询、删除、修改标签、生成GIF

v1.1 改动(2026-07-17):
- add_photos 硬规则:tag 不能空 / 长度 ≤ 20
- add_photos 软规则:note 推荐填(给数据可读性)
- 文件头加 5 层架构自检 checklist
"""

import argparse
import json
import os
import sys
import shutil
from datetime import datetime, date
from pathlib import Path

from db_utils import find_db_path, get_db as _get_db_conn, init_db as _init_db

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

SKILL_DIR = Path(__file__).parent.parent
DB_FILENAME = "calorie_data.db"
DB_PATH = find_db_path(SKILL_DIR, DB_FILENAME)

# 最近一次 GIF 合成信息(ticket #10 · C3:呈现数据要"帧数/照片总数",generate_gif 返回 Path 兼容旧测试,
# 帧信息挂模块属性由 render_body_photo_gif_result 读取)
_last_gif_info = {}


def get_last_gif_info():
    return dict(_last_gif_info)


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


# ===== 多标签模型(2026-08-02 · ticket #10 决策:字符串编码,逗号分隔) =====
# tag 列存 '正面,侧面,背部' 形式的逗号分隔串(方案 2,0 schema 变更,见研究报告 §2.6)。
# 语义:改照片标签 = 覆盖整套 / 加照片标签 = 追加(判重) / 删照片标签 = 移除(至少保留 1 个)。
TAG_SEP = ','
TAG_MAX_LEN = 20          # 单个标签长度上限(沿用旧硬规则)
TAG_MAX_COUNT = 10        # 单张照片标签数量上限(串长保护)


def parse_tags(tag_str):
    """'正面, 侧面' → ['正面', '侧面'](去空白/去空项/去重保序)"""
    seen = set()
    out = []
    for t in (tag_str or '').split(TAG_SEP):
        t = t.strip()
        if not t:
            continue
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def serialize_tags(tags):
    """['正面', '侧面'] → '正面,侧面'"""
    return TAG_SEP.join(tags)


def validate_tags(tags):
    """校验标签列表(多标签硬规则):非空 + 单个长度 ≤ 20 + 数量 ≤ 10"""
    if not tags:
        raise ValueError("标签必填,当前是空列表")
    for t in tags:
        if len(t) > TAG_MAX_LEN:
            raise ValueError(f"标签太长({len(t)} > {TAG_MAX_LEN}): {t!r}")
    if len(tags) > TAG_MAX_COUNT:
        raise ValueError(f"标签数量太多({len(tags)} > {TAG_MAX_COUNT})")
    return tags


def tags_contain(tag_str, tag):
    """tag 串是否包含指定标签(多标签包含匹配,替代旧精确等值)"""
    return tag in parse_tags(tag_str)


def get_photo_row(photo_id):
    """按 id 取照片行(含 tag 解析),不存在返回 None"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, date, time, photo_path, tag, note, created_at FROM body_photos WHERE id = ?",
        (photo_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(zip(['id', 'date', 'time', 'photo_path', 'tag', 'note', 'created_at'], row))
    d['tag_list'] = parse_tags(d['tag'])
    return d


def days_since_tag_photo(tag, before_date=None):
    """距 before_date 之前最近一张含该标签照片的天数(规律拍照提示用)

    before_date 必传:查该日期之前(不含当天)最近一张含 tag 的照片。
    返回 None = 之前没有同标签照片。
    """
    from datetime import date as _date
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, tag, date FROM body_photos WHERE date < ? ORDER BY date DESC, time DESC",
        (before_date,))
    for pid, ptag, d in cur.fetchall():
        if tags_contain(ptag, tag):
            conn.close()
            delta = (_date.fromisoformat(before_date) - _date.fromisoformat(d)).days
            return delta if delta >= 0 else None
    conn.close()
    return None


def add_photos(photo_paths, tag, note=''):
    """添加照片记录(2026-08-02 支持多标签:tag 可传 '正面,侧面')"""
    # 硬规则(2026-07-17 加,2026-08-02 改多标签):标签非空 + 单个长度 ≤ 20 + 数量 ≤ 10
    tags = validate_tags(parse_tags(tag))
    tag_serialized = serialize_tags(tags)
    # 软规则:note 推荐非空(但不强制)
    if not note:
        print(f"[HINT] note 为空,推荐补充(便于后续搜索)")

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
        """, (today, now, dest_name, tag_serialized, note))
        photo_id = cur.lastrowid
        conn.commit()
        conn.close()

        added.append((photo_id, dest_name))
        print(f"✓ 已添加照片 #{photo_id}: {dest_name} (标签: {tag_serialized})")

    return added


def list_photos(days=7, tag=None, date_from=None, date_to=None, limit=100):
    """查询照片列表(2026-08-02 加 --date-from/--date-to/--limit + 标签包含匹配)"""
    conn = get_db()
    cur = conn.cursor()

    # 构建 WHERE
    where = []
    params = []
    if date_from:
        where.append("date >= ?")
        params.append(date_from)
    if date_to:
        where.append("date <= ?")
        params.append(date_to)
    if not date_from and not date_to:
        from datetime import timedelta
        start_date = (date.today() - timedelta(days=days)).isoformat()
        where.append("date >= ?")
        params.append(start_date)

    # 标签筛选:多标签包含匹配(取全部行后内存过滤,避免 LIKE 边界问题)
    sql = f"""
        SELECT id, date, time, photo_path, tag, note, created_at
        FROM body_photos
        WHERE {' AND '.join(where)}
        ORDER BY date DESC, time DESC
    """
    rows = cur.execute(sql, params).fetchall()
    conn.close()

    if tag:
        rows = [r for r in rows if tags_contain(r[4], tag)]
    rows = rows[:limit] if limit else rows

    if not rows:
        print(f"没有匹配的身材照片记录(最近{days}天/tag={tag or '-'}/范围={date_from or '-'}~{date_to or '-'})")
        return []

    print(f"\n身材照片记录:共 {len(rows)} 张")
    print("-" * 70)
    print(f"{'ID':>4} | {'日期':>10} | {'时间':>8} | {'标签':>12} | {'文件':20} | 备注")
    print("-" * 70)

    for r in rows:
        photo_id, p_date, p_time, photo_path, p_tag, p_note, created = r
        time_str = p_time[:8] if p_time else ''
        print(f"{photo_id:>4} | {p_date:>10} | {time_str:>8} | {p_tag:>12} | {photo_path:20} | {p_note or ''}")

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
    """修改照片标签(覆盖整套 · 2026-08-02 支持多标签 '正面,侧面')"""
    conn = get_db()
    cur = conn.cursor()

    # 检查照片是否存在
    cur.execute("SELECT id, tag FROM body_photos WHERE id = ?", (photo_id,))
    row = cur.fetchone()
    if not row:
        print(f"Error: 照片 #{photo_id} 不存在")
        conn.close()
        return False

    old_tag = row[1]
    tags = validate_tags(parse_tags(new_tag))
    new_serialized = serialize_tags(tags)

    # 更新标签
    cur.execute("UPDATE body_photos SET tag = ? WHERE id = ?", (new_serialized, photo_id))
    conn.commit()
    conn.close()

    print(f"✓ 已更新照片 #{photo_id} 标签: {old_tag!r} → {new_serialized!r}")
    return True


def tag_add(photo_id, tag):
    """加照片标签:追加(不覆盖已有),已存在则判重跳过

    2026-08-02 支持逗号分隔多标签(逐个追加,判重);返回新增标签数。
    """
    photo = get_photo_row(photo_id)
    if not photo:
        print(f"Error: 照片 #{photo_id} 不存在")
        return 0

    tags = validate_tags(parse_tags(tag))
    existing = photo['tag_list']
    added = []
    for new_tag in tags:
        if new_tag in existing:
            print(f"⚠ 标签「{new_tag}」已存在(照片 #{photo_id} 当前标签: {photo['tag']}),跳过")
            continue
        existing.append(new_tag)
        added.append(new_tag)

    if not added:
        return 0

    new_serialized = serialize_tags(existing)
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE body_photos SET tag = ? WHERE id = ?", (new_serialized, photo_id))
    conn.commit()
    conn.close()

    print(f"✓ 已为照片 #{photo_id} 追加标签「{'、'.join(added)}」→ 当前标签: {new_serialized}")
    return len(added)


def tag_remove(photo_id, tag):
    """删照片标签:移除单个标签(至少保留 1 个,删空报错拒绝)"""
    photo = get_photo_row(photo_id)
    if not photo:
        print(f"Error: 照片 #{photo_id} 不存在")
        return False

    tags = parse_tags(tag)
    if len(tags) != 1:
        print(f"Error: 删标签一次只删 1 个,收到 {len(tags)} 个: {tags!r}")
        return False
    rm_tag = tags[0]

    existing = photo['tag_list']
    if rm_tag not in existing:
        print(f"⚠ 标签「{rm_tag}」不存在(照片 #{photo_id} 当前标签: {photo['tag']}),无需删除")
        return False
    if len(existing) <= 1:
        print(f"Error: 照片 #{photo_id} 只有「{rm_tag}」1 个标签,每张照片至少保留 1 个标签(删空语义 2026-08-02)")
        return False

    existing.remove(rm_tag)
    new_serialized = serialize_tags(existing)
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE body_photos SET tag = ? WHERE id = ?", (new_serialized, photo_id))
    conn.commit()
    conn.close()

    print(f"✓ 已为照片 #{photo_id} 移除标签「{rm_tag}」→ 当前标签: {new_serialized}")
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


def generate_gif(tag, start_date=None, end_date=None, days=None,
                  photo_ids=None, crops_json=None,
                  width=400, height=600, duration=500, loop=0,
                  watermark=None, transition='cut', output=None):
    """生成 GIF 变化动画(v2.3.0)

    Args:
        tag: 照片标签
        start_date/end_date: 日期范围(YYYY-MM-DD)
        days: 最近 N 天(与 start/end 互斥)
        photo_ids: 显式选 ID + 顺序,None = 全部
        crops_json: JSON dict {id: [x1,y1,x2,y2]},可对每张照片单独裁剪
        width/height: 输出尺寸(默认 400×600)
        duration: 单帧 ms(默认 500)
        loop: 循环次数(0=无限)
        watermark: 文字水印(可选)
        transition: cut / fade / dissolve(默认 cut)
        output: 输出文件名
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
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

    # 解析 crops JSON
    crops_map = {}
    if crops_json:
        try:
            crops_map = {int(k): tuple(v) for k, v in json.loads(crops_json).items()}
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            print(f"Error: --crops JSON 解析失败: {e}")
            print("  期望格式: '{\"12\": [120,240,400,600], \"15\": [100,200,380,600]}'")
            return None

    # 查询照片
    conn = get_db()
    cur = conn.cursor()

    if photo_ids:
        # 显式按 ID + 顺序(占位符 ? 顺序展开)
        placeholders = ','.join('?' * len(photo_ids))
        cur.execute(f"""
            SELECT id, photo_path, date, time, tag
            FROM body_photos
            WHERE id IN ({placeholders})
            ORDER BY CASE id {' '.join(f'WHEN {i} THEN {idx}' for idx, i in enumerate(photo_ids))} END
        """, photo_ids)
        rows = cur.fetchall()
        # 按 photo_ids 顺序重排
        rows_dict = {r[0]: r for r in rows}
        rows = [rows_dict[i] for i in photo_ids if i in rows_dict]
    else:
        # 多标签包含匹配(2026-08-02:tag 可能是 '正面,侧面' 串,取全量后内存过滤)
        cur.execute("""
            SELECT id, photo_path, date, time, tag
            FROM body_photos
            WHERE date >= ? AND date <= ?
            ORDER BY date ASC, time ASC
        """, (start_date, end_date))
        all_rows = cur.fetchall()
        rows = [r for r in all_rows if tags_contain(r[4], tag)]
    conn.close()

    if not rows:
        if photo_ids:
            print(f"未找到指定 ID 的照片: {photo_ids}")
        else:
            print(f"未找到标签为 '{tag}' 的照片({start_date} ~ {end_date})")
        return None

    # 加载 + 处理图片
    images = []
    for photo_id, photo_path, photo_date, photo_time, _tag in rows:
        file_path = photos_dir / photo_path
        if not file_path.exists():
            print(f"  ⚠ 跳过(ID={photo_id}): 文件不存在 {file_path}")
            continue
        img = Image.open(file_path).convert('RGB')

        # 裁剪(如果指定)
        if photo_id in crops_map:
            x1, y1, x2, y2 = crops_map[photo_id]
            # 校验边界
            w_img, h_img = img.size
            x1 = max(0, min(x1, w_img))
            y1 = max(0, min(y1, h_img))
            x2 = max(x1, min(x2, w_img))
            y2 = max(y1, min(y2, h_img))
            img = img.crop((x1, y1, x2, y2))

        # 等比缩放 fit 到目标尺寸(留白填白)
        target_ratio = width / height
        img_ratio = img.size[0] / img.size[1]
        if img_ratio > target_ratio:
            # 宽主导 → 按宽缩放
            new_w = width
            new_h = int(width / img_ratio)
        else:
            new_h = height
            new_w = int(height * img_ratio)
        img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # 居中放白底
        canvas = Image.new('RGB', (width, height), (255, 255, 255))
        offset = ((width - new_w) // 2, (height - new_h) // 2)
        canvas.paste(img_resized, offset)
        img = canvas

        # 水印
        if watermark:
            draw = ImageDraw.Draw(img)
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
            except OSError:
                font = ImageFont.load_default()
            # 右下角白色文字 + 黑色描边
            text_bbox = draw.textbbox((0, 0), watermark, font=font)
            tw, th = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]
            margin = 12
            tx = width - tw - margin
            ty = height - th - margin
            for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                draw.text((tx + dx, ty + dy), watermark, fill=(0, 0, 0), font=font)
            draw.text((tx, ty), watermark, fill=(255, 255, 255), font=font)

        images.append(img)

    if not images:
        print("没有可用的照片文件")
        return None

    # 过渡效果
    if transition == 'cut' or len(images) < 2:
        # 直接拼
        final_frames = images
        frames_duration = [duration] * len(images)
    elif transition == 'fade':
        # 每对相邻帧之间插入 N 个渐变帧
        fade_steps = 10
        final_frames = []
        frames_duration = []
        for i in range(len(images) - 1):
            final_frames.append(images[i])
            frames_duration.append(duration)
            for step in range(1, fade_steps + 1):
                alpha = step / fade_steps
                blended = Image.blend(images[i], images[i + 1], alpha)
                final_frames.append(blended)
                frames_duration.append(duration // fade_steps)
        final_frames.append(images[-1])
        frames_duration.append(duration)
    elif transition == 'dissolve':
        # 简化版 dissolve = 同 fade(v2.3 不做棋盘格,留 v2.4 升级)
        final_frames = []
        frames_duration = []
        for i in range(len(images) - 1):
            final_frames.append(images[i])
            frames_duration.append(duration)
            for step in range(1, 6):
                alpha = step / 5
                blended = Image.blend(images[i], images[i + 1], alpha)
                final_frames.append(blended)
                frames_duration.append(duration // 5)
        final_frames.append(images[-1])
        frames_duration.append(duration)
    else:
        final_frames = images
        frames_duration = [duration] * len(images)

    # 输出文件名
    if not output:
        suffix = photo_ids[0] if photo_ids else None
        suffix = f"_id{suffix}" if suffix else ""
        output = f"{tag}_{start_date}_{end_date}{suffix}.gif"

    output_path = gifs_dir / output

    # 生成 GIF
    final_frames[0].save(
        output_path,
        save_all=True,
        append_images=final_frames[1:],
        duration=frames_duration,
        loop=loop,
        optimize=True,
    )

    print(f"✓ 已生成 GIF: {output_path}")
    print(f"  包含 {len(images)} 张原始照片 → {len(final_frames)} 帧")
    print(f"  参数: {width}×{height}, {duration}ms/帧, {transition}, 水印{'「'+watermark+'」' if watermark else '无'}")
    global _last_gif_info
    _last_gif_info = {
        'path': str(output_path),
        'photo_count': len(images),
        'frame_count': len(final_frames),
        'width': width, 'height': height,
        'duration_ms': duration, 'transition': transition,
    }
    return output_path


def main():
    parser = argparse.ArgumentParser(description="身材照片记录管理")
    subparsers = parser.add_subparsers(dest='cmd', help='子命令')

    # add
    p_add = subparsers.add_parser('add', help='添加照片')
    p_add.add_argument('photos', nargs='+', help='照片文件路径')
    p_add.add_argument('--tag', required=True, help='照片标签')
    p_add.add_argument('--note', default='', help='备注')

    # list
    p_list = subparsers.add_parser('list', help='查询照片')
    p_list.add_argument('--days', type=int, default=7, help='查询天数(未给日期范围时生效)')
    p_list.add_argument('--tag', help='按标签筛选(包含匹配)')
    p_list.add_argument('--date-from', dest='date_from', help='起始日期 YYYY-MM-DD')
    p_list.add_argument('--date-to', dest='date_to', help='结束日期 YYYY-MM-DD')
    p_list.add_argument('--limit', type=int, default=100, help='最多返回条数(默认 100)')

    # delete
    p_delete = subparsers.add_parser('delete', help='删除照片')
    p_delete.add_argument('id', type=int, help='照片ID')

    # tag(覆盖整套,多标签)
    p_tag = subparsers.add_parser('tag', help='修改照片标签(覆盖整套,可多标签逗号分隔)')
    p_tag.add_argument('id', type=int, help='照片ID')
    p_tag.add_argument('new_tag', help='新标签(多个用逗号分隔,如 正面,侧面)')

    # tag-add(追加)
    p_tag_add = subparsers.add_parser('tag-add', help='加照片标签(追加,不覆盖已有)')
    p_tag_add.add_argument('id', type=int, help='照片ID')
    p_tag_add.add_argument('tag', help='要追加的标签')

    # tag-remove(移除)
    p_tag_remove = subparsers.add_parser('tag-remove', help='删照片标签(移除单个,至少保留 1 个)')
    p_tag_remove.add_argument('id', type=int, help='照片ID')
    p_tag_remove.add_argument('tag', help='要移除的标签')

    # gif
    p_gif = subparsers.add_parser('gif', help='生成GIF(v2.3.0 增强)')
    p_gif.add_argument('--tag', required=True, help='照片标签')
    p_gif.add_argument('--start', help='开始日期 YYYY-MM-DD')
    p_gif.add_argument('--end', help='结束日期 YYYY-MM-DD')
    p_gif.add_argument('--days', type=int, help='最近N天')
    p_gif.add_argument('--photo-id', type=int, action='append',
                       help='显式选 ID(可重复,按传入顺序)。不传=该 tag 所有照片')
    p_gif.add_argument('--crops', help='JSON dict 单独裁剪: {"id": [x1,y1,x2,y2]}')
    p_gif.add_argument('--width', type=int, default=400, help='输出宽度(默认 400)')
    p_gif.add_argument('--height', type=int, default=600, help='输出高度(默认 600)')
    p_gif.add_argument('--duration', type=int, default=500, help='单帧 ms(默认 500)')
    p_gif.add_argument('--loop', type=int, default=0, help='循环次数(0=无限,默认 0)')
    p_gif.add_argument('--watermark', help='文字水印(右下角,可选)')
    p_gif.add_argument('--transition', choices=['cut', 'fade', 'dissolve'],
                       default='cut', help='过渡效果(默认 cut)')
    p_gif.add_argument('--output', help='输出文件名')

    args = parser.parse_args()

    # 初始化表（2026-07-13 改:本地 init_table 已删,统一调 db.init_db）
    _init_db(DB_PATH)

    if args.cmd == 'add':
        add_photos(args.photos, args.tag, args.note)
    elif args.cmd == 'list':
        list_photos(days=args.days, tag=args.tag, date_from=args.date_from,
                    date_to=args.date_to, limit=args.limit)
    elif args.cmd == 'delete':
        delete_photo(args.id)
    elif args.cmd == 'tag':
        update_tag(args.id, args.new_tag)
    elif args.cmd == 'tag-add':
        tag_add(args.id, args.tag)
    elif args.cmd == 'tag-remove':
        tag_remove(args.id, args.tag)
    elif args.cmd == 'gif':
        generate_gif(
            tag=args.tag,
            start_date=args.start,
            end_date=args.end,
            days=args.days,
            photo_ids=args.photo_id,
            crops_json=args.crops,
            width=args.width,
            height=args.height,
            duration=args.duration,
            loop=args.loop,
            watermark=args.watermark,
            transition=args.transition,
            output=args.output,
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    from _io_guard import guard_io; guard_io()
    main()
