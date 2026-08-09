#!/usr/bin/env python3
"""
私家大厨 - 照片/链接值类型判定表 + 三目录契约(G5 决策 · T8 · 2026-08-09)

统一契约: 三个字段共用一张「值类型判定表」:
    photo_url(成品照) / source_url(来源) / recipe_history.photo(作品照)

值类型判定表:
    chef:// 本地文件        → 拼根目录 → <img>
    图片扩展名 / 图床域名    → <img>
    视频平台域名 / 视频扩展名 → 外链 + 「🎬 视频」标识
    其他 URL               → 外链

本地文件三目录契约:
    photos/(成品照) + source_photos/(来源图,已有) + work_photos/(作品照,新建)
    命名 <recipe_slug>__<类型短码>__<YYYYMMDD>.<ext>
    chef:// 入库不存绝对路径(跨设备迁移,渲染时拼输出根目录)
    类型短码: photo(成品照) / source(来源图) / work(作品照)
"""
import re
from datetime import datetime
from pathlib import Path

# ── 值类型判定表 ──────────────────────────────────────────────
_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".svg", ".avif", ".heic"}
_VIDEO_EXTS = {".mp4", ".webm", ".mov", ".mkv", ".avi", ".flv", ".m4v"}

# 图床/图片托管域名(命中即按图片渲染)
_IMAGE_HOSTS = (
    "picsum.photos", "loremflickr.com", "imgur.com", "unsplash.com",
    "dummyimage.com", "placehold.co", "via.placeholder.com", "aliyuncs.com",
    "qiniucdn.com", "upyun.com", "sinaimg.cn", "sinaimg.com", "githubusercontent.com",
    "cloudinary.com", "bilibili.com/bfs", "twimg.com",
)
# 视频平台域名(命中即按视频渲染)
_VIDEO_HOSTS = (
    "youtube.com", "youtu.be", "bilibili.com/video", "b23.tv",
    "youku.com", "vimeo.com", "iqiyi.com", "douyin.com", "tiktok.com",
    "kuaishou.com", "xiaohongshu.com/discovery/item", "acfun.cn", "weibo.com/tv",
)

_CHEF_PREFIX = "chef://"


def _netloc(value: str) -> str:
    """提取 URL 的 netloc(小写);非 http 返回空"""
    m = re.match(r"^https?://([^/?#]+)", value.strip().lower())
    return m.group(1) if m else ""


def classify_media(value) -> str:
    """值类型判定表 → local / image / video / link"""
    if not value:
        return "link"
    v = str(value).strip()
    if not v:
        return "link"
    if v.startswith(_CHEF_PREFIX):
        return "local"
    lower = v.lower()
    netloc = _netloc(lower)
    host_path = lower.split("?", 1)[0].split("#", 1)[0]
    ext = Path(host_path).suffix.lower()
    if ext in _VIDEO_EXTS or any(host in host_path for host in _VIDEO_HOSTS):
        return "video"
    if ext in _IMAGE_EXTS or any(host in host_path for host in _IMAGE_HOSTS):
        return "image"
    return "link"


# ── 三目录契约 ────────────────────────────────────────────────
TYPE_SHORTCODES = {"photo": "photo", "source": "source", "work": "work"}
DIRS = {"photo": "photos", "source": "source_photos", "work": "work_photos"}


def relpath_for(slug: str, type_code: str, date: str, ext: str) -> str:
    """三目录契约命名: <目录>/<recipe_slug>__<类型短码>__<YYYYMMDD>.<ext>
    返回 chef:// 之后的相对路径(入库值 = chef:// + 此结果)"""
    if type_code not in TYPE_SHORTCODES:
        raise ValueError(f"未知类型短码:{type_code},合法:{sorted(TYPE_SHORTCODES)}")
    ext = ext.lower()
    if not ext.startswith("."):
        ext = "." + ext
    return f"{DIRS[type_code]}/{slug}__{TYPE_SHORTCODES[type_code]}__{date}{ext}"


def work_photo_relpath(slug: str, ext: str, date: str = None) -> str:
    """作品照相对路径(work_photos/ 目录)"""
    date = date or datetime.now().strftime("%Y%m%d")
    return relpath_for(slug, "work", date, ext)


def resolve_chef(value, output_root) -> Path:
    """chef:// 值 → 拼输出根目录 → 本地路径(仅 local 类型调用)"""
    if not str(value).startswith(_CHEF_PREFIX):
        raise ValueError(f"非 chef:// 值:{value}")
    rel = str(value)[len(_CHEF_PREFIX):]
    return Path(output_root) / rel


def build_media_html(value, output_root) -> str:
    """值类型判定表渲染: 返回可直接嵌入 HTML 的片段
    - local → <img src="file:///...">(拼根目录)
    - image → <img src="<url>">
    - video → <a href> 外链 + 🎬 视频
    - link  → <a href> 外链
    """
    if not value:
        return ""
    kind = classify_media(value)
    if kind == "local":
        local_path = resolve_chef(value, output_root)
        return (
            f'<img src="file:///{local_path.as_posix()}" alt="本地照片" '
            f'loading="lazy" style="max-width:100%;border-radius:8px;display:block" />'
        )
    if kind == "image":
        return (
            f'<img src="{value}" alt="照片" loading="lazy" '
            f'style="max-width:100%;border-radius:8px;display:block" />'
        )
    if kind == "video":
        return f'<a href="{value}" target="_blank" rel="noopener">🎬 视频</a>'
    return f'<a href="{value}" target="_blank" rel="noopener">查看原文</a>'


if __name__ == "__main__":
    samples = [
        "chef://work_photos/辣椒炒肉__work__20260809.jpg",
        "https://picsum.photos/seed/x/200/200",
        "https://example.com/a.jpg",
        "https://www.bilibili.com/video/BV1xx",
        "https://example.com/video.mp4",
        "https://baike.baidu.com/item/x",
    ]
    for s in samples:
        print(f"{classify_media(s):6s}  {s}")
