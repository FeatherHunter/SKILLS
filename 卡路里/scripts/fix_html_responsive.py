#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/fix_html_responsive.py — 一键修 26 处 HTML 响应式违例

ticket Phase 3c · 2026-07-29

对每个 templates/*.html:
  1. 加 @media (max-width:640px) 断点(若缺)
  2. SVG height: 固定像素 → clamp()
  3. <table> 外包 <div class="table-wrap">

用法:
    python scripts/fix_html_responsive.py            # 全部模板
    python scripts/fix_html_responsive.py templates/calorie_trend.html  # 单文件
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = SKILL_DIR / "templates"

# 通用 mobile-friendly 媒体查询块(供注入)
DEFAULT_MEDIA_BLOCK = """
  /* Phase 3c:mobile 断点(640px 以下单列堆叠 + 缩 padding) */
  @media (max-width:640px) {
    body { padding:20px 14px 80px; }
    h1 { font-size:22px; }
    .section { padding:16px 18px; border-radius:12px; }
    .kpi-grid { grid-template-columns:1fr 1fr; gap:10px; }
    .food-card .macros { grid-template-columns:1fr 1fr; }
  }
  /* table 在小屏内滚 */
  .table-wrap { overflow-x:auto; -webkit-overflow-scrolling:touch; }
"""

# SVG height 固定像素模式
FIXED_SVG_HEIGHT_RE = re.compile(
    r"(svg\s*\{[^}]*?height\s*:\s*)(\d+)px",
    re.IGNORECASE,
)


def fix_media_query(html: str) -> tuple[str, bool]:
    """若缺 @media,在 </style> 前插入默认块"""
    if "@media" in html:
        return html, False
    # 在最后一个 </style> 前注入
    new_html = re.sub(
        r"(\s*</style>)",
        DEFAULT_MEDIA_BLOCK + r"\1",
        html,
        count=1,
    )
    return new_html, new_html != html


def fix_svg_fixed_height(html: str) -> tuple[str, int]:
    """svg { height: Npx } → svg { height: clamp(180px, 40vh, 320px) }"""
    count = 0

    def _replace(m):
        nonlocal count
        count += 1
        return f"{m.group(1)}clamp(180px, 40vh, 320px)"

    new_html = FIXED_SVG_HEIGHT_RE.sub(_replace, html)
    return new_html, count


def fix_table_wrapping(html: str) -> tuple[str, int]:
    """<table>...</table> → <div class="table-wrap"><table>...</table></div>

    只包裹直接出现的 <table>(不在 table-wrap 内的)
    """
    count = 0
    parts = []
    i = 0
    while i < len(html):
        idx = html.find("<table", i)
        if idx == -1:
            parts.append(html[i:])
            break
        # 已包裹?
        pre = html[max(0, idx - 200):idx]
        if 'class="table-wrap"' in pre:
            parts.append(html[i:idx + len("<table")])
            i = idx + len("<table")
            continue
        # 找匹配的 </table>
        end = html.find("</table>", idx)
        if end == -1:
            parts.append(html[i:])
            break
        end += len("</table>")
        parts.append(html[i:idx])
        parts.append('<div class="table-wrap">')
        parts.append(html[idx:end])
        parts.append('</div>')
        count += 1
        i = end
    return "".join(parts), count


def fix_one(path: Path) -> dict:
    """fix 单个 HTML,返回改动统计"""
    html = path.read_text(encoding="utf-8")
    before = html
    html, added_media = fix_media_query(html)
    html, svg_count = fix_svg_fixed_height(html)
    html, table_count = fix_table_wrapping(html)
    if html != before:
        path.write_text(html, encoding="utf-8")
    return {
        "added_media": added_media,
        "svg_fixed_count": svg_count,
        "tables_wrapped": table_count,
    }


def main() -> int:
    targets = sys.argv[1:]
    if targets:
        files = [Path(p) for p in targets]
    else:
        files = sorted(TEMPLATES_DIR.glob("*.html"))

    print(f"🔧 修复 {len(files)} 个 HTML 模板\n")
    total = {"added_media": 0, "svg_fixed_count": 0, "tables_wrapped": 0}
    for f in files:
        if not f.exists():
            print(f"  ⏭ {f.name}: 不存在")
            continue
        try:
            stats = fix_one(f)
            changes = sum(stats.values())
            if changes:
                msg = []
                if stats["added_media"]:
                    msg.append("+@media")
                if stats["svg_fixed_count"]:
                    msg.append(f"SVG×{stats['svg_fixed_count']}")
                if stats["tables_wrapped"]:
                    msg.append(f"table-wrap×{stats['tables_wrapped']}")
                print(f"  ✅ {f.name}: {' '.join(msg)}")
            else:
                print(f"  ⚪ {f.name}: 无需修")
            for k, v in stats.items():
                total[k] += v
        except Exception as e:
            print(f"  ❌ {f.name}: {e}")

    print(f"\n📊 合计: +@media {total['added_media']} · SVG {total['svg_fixed_count']} · table-wrap {total['tables_wrapped']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())