# -*- coding: utf-8 -*-
"""
智剪工坊 · cover_ai 子技能
AI 生成封面图 + 中文叠字(B 站风格)

用法:
  # 单图模式:已有图片,加中文
  python cover_ai.py --image bg.png --text "184" --text "→" --text "139.9" --out cover.jpg

  # AI 模式:从主题描述自动生成视觉图 + 叠字
  python cover_ai.py --prompt "A man's silhouette on a body weight scale, dramatic red lighting" \
    --text "184→139.9" --subtitle "Day 1" --out cover.jpg


📖 SKILL.md §14 索引 → REQUIRED: read references/08-cover.md
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))
from common import (
    ensure_dir, log_info, log_warn, log_section, safe_run, SKILL_ROOT,
)


# 默认字体路径(Windows)
FONT_BOLD = r"C:\Windows\Fonts\msyhbd.ttc"
FONT_NORMAL = r"C:\Windows\Fonts\msyh.ttc"


def generate_image(prompt, output_png, aspect="16:9", resolution="2K"):
    """用 matrix MCP 生成 AI 视觉图"""
    log_section(f"AI 生图: {prompt[:50]}...")
    req = {
        "requests": [{
            "prompt": prompt,
            "aspect_ratio": aspect,
            "resolution": resolution,
        }]
    }
    req_file = Path(tempfile.gettempdir()) / "cover_req.json"
    req_file.write_text(json.dumps(req, ensure_ascii=False), encoding="utf-8")

    result = subprocess.run(
        ["mavis", "mcp", "call", "matrix", "matrix_generate_image", "--file", str(req_file)],
        capture_output=True, text=True, encoding="utf-8"
    )
    if result.returncode != 0:
        log_warn(f"matrix 调用失败: {result.stderr}")
        return None

    # 解析 output_url
    import re
    match = re.search(r'"output_url":\s*"([^"]+)"', result.stdout)
    if not match:
        log_warn("matrix 返回无 output_url")
        return None

    output_url = match.group(1)
    # Windows 路径
    if output_url.startswith("C:\\"):
        src = Path(output_url)
        if src.exists():
            import shutil
            shutil.copy2(src, output_png)
            log_info(f"AI 图已复制: {output_png}")
            return output_png
    return None


def overlay_text(image_path, output_path, text_specs):
    """
    在图上叠中文(PIL)
    text_specs: list of dict,每个含 content/x/y/size/color/font
    """
    from PIL import Image, ImageDraw, ImageFont
    log_section(f"叠中文: {Path(image_path).name}")

    img = Image.open(image_path).convert("RGB")
    w, h = img.size
    log_info(f"原图: {w}x{h}")

    draw = ImageDraw.Draw(img)
    for spec in text_specs:
        font_path = spec.get("font", FONT_BOLD)
        font = ImageFont.truetype(font_path, spec["size"])
        draw.text(
            (spec["x"], spec["y"]),
            spec["content"],
            font=font,
            fill=tuple(spec["color"]),
        )

    img.save(output_path, quality=92)
    log_info(f"封面输出: {output_path}")


def make_cover(image, output, title_main, subtitle=None, tag=None, author=None):
    """通用封面叠字模板(右上半部分)"""
    w = 1920
    h = 1080
    specs = []
    if title_main:
        specs.append({"content": title_main, "x": 1080, "y": 320, "size": 150, "font": FONT_BOLD, "color": (255, 215, 0)})
    if subtitle:
        specs.append({"content": subtitle, "x": 1080, "y": 530, "size": 56, "font": FONT_NORMAL, "color": (255, 255, 255)})
    if tag:
        specs.append({"content": tag, "x": 1080, "y": 620, "size": 50, "font": FONT_BOLD, "color": (255, 180, 60)})
    if author:
        specs.append({"content": author, "x": 80, "y": h - 70, "size": 32, "font": FONT_NORMAL, "color": (255, 255, 255)})

    overlay_text(image, output, specs)


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · AI 封面(生图 + 中文叠字)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
两种模式:
1. --image + 叠字(纯文字)
2. --prompt + --image(AI 生图 + 叠字)
        """,
    )
    parser.add_argument("--image", help="已有图片(若不提供则 AI 生图)")
    parser.add_argument("--prompt", help="AI 生图 prompt(若不提供 --image 必须)")
    parser.add_argument("--text", action="append", default=[], help="叠字内容(可多次)")
    parser.add_argument("--title-main", help="主标题")
    parser.add_argument("--subtitle", help="副标题")
    parser.add_argument("--tag", help="系列标签")
    parser.add_argument("--author", help="作者标识(左下角)")
    parser.add_argument("--output", dest="output", required=True, help="输出封面(JPG)")
    args = parser.parse_args()

    ensure_dir(Path(args.output).parent)

    # 决定用 AI 生图还是已有图
    image_path = args.image
    if not image_path and args.prompt:
        # AI 生图
        tmp_png = Path(args.output).with_suffix(".ai_bg.png")
        image_path = generate_image(args.prompt, str(tmp_png))
        if not image_path:
            log_warn("AI 生图失败,需要 --image 提供背景")
            return

    if not image_path or not Path(image_path).exists():
        log_warn(f"图片不存在: {image_path}")
        return

    # 叠字
    if args.text:
        # 自定义模式
        specs = []
        y_offset = 100
        for i, t in enumerate(args.text):
            specs.append({
                "content": t,
                "x": 100, "y": y_offset + i * 100,
                "size": 80, "font": FONT_BOLD, "color": (255, 255, 255)
            })
        overlay_text(image_path, args.output, specs)
    else:
        # 模板模式
        make_cover(image_path, args.output, args.title_main, args.subtitle, args.tag, args.author)


if __name__ == "__main__":
    safe_run(main)()
