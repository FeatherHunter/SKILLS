"""
封面合成 scripts/text.py
③ 业务层:文字水印(细化的位置/样式/字体管理)

split from layers.py because it gets long
"""
from PIL import Image, ImageDraw, ImageFont
import sys
from pathlib import Path
from typing import Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.presets_data import FONT_PATHS


# 9 宫格位置(支持更精细的 absolute positioning)
POSITIONS_9_GRID = {
    "top-left":      lambda tw, th, cw, ch, margin: (margin, margin),
    "top-center":    lambda tw, th, cw, ch, margin: ((cw - tw) // 2, margin),
    "top-right":     lambda tw, th, cw, ch, margin: (cw - tw - margin, margin),
    "middle-left":   lambda tw, th, cw, ch, margin: (margin, (ch - th) // 2),
    "middle-center": lambda tw, th, cw, ch, margin: ((cw - tw) // 2, (ch - th) // 2),
    "middle-right":  lambda tw, th, cw, ch, margin: (cw - tw - margin, (ch - th) // 2),
    "bottom-left":   lambda tw, th, cw, ch, margin: (margin, ch - th - margin),
    "bottom-center": lambda tw, th, cw, ch, margin: ((cw - tw) // 2, ch - th - margin),
    "bottom-right":  lambda tw, th, cw, ch, margin: (cw - tw - margin, ch - th - margin),
}


def draw_text(canvas: Image.Image, content: str, position: str = "middle-center",
              font_size: int = 64,
              font_color: Tuple[int, int, int] = (255, 215, 0),
              outline_color: Tuple[int, int, int] = (0, 0, 0),
              outline_width: int = 4,
              margin: int = 80,
              font_path: str = None) -> Image.Image:
    """在画布上画文字(完整版)

    防坑 #10: 文字必须有黑色描边,否则在亮色照片上读不清
    """
    if canvas.mode != "RGBA":
        canvas = canvas.convert("RGBA")
    draw = ImageDraw.Draw(canvas)
    W, H = canvas.size

    # 字体
    if font_path is None:
        font_path = FONT_PATHS["bold"]
    font = ImageFont.truetype(font_path, font_size)

    # 计算文字位置
    bbox = draw.textbbox((0, 0), content, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    if position not in POSITIONS_9_GRID:
        raise ValueError(f"position '{position}' 不在 9 宫格白名单")

    x, y = POSITIONS_9_GRID[position](text_w, text_h, W, H, margin)

    # 描边宽度按字号比例(防 #14 字号过大)
    actual_outline = outline_width if outline_width else max(2, font_size // 25)

    draw.text((x, y), content, font=font, fill=font_color,
              stroke_width=actual_outline, stroke_fill=outline_color)
    return canvas


def draw_text_lines(canvas: Image.Image, lines: list) -> Image.Image:
    """批量画文字(简化接口)

    lines: [{"text", "position", "size", "font_color", "outline_color", "outline_width"}]
    """
    for line in lines:
        draw_text(
            canvas,
            content=line["text"],
            position=line.get("position", "middle-center"),
            font_size=line.get("size", 64),
            font_color=tuple(line.get("font_color", [255, 215, 0])),
            outline_color=tuple(line.get("outline_color", [0, 0, 0])),
            outline_width=line.get("outline_width", 4),
            font_path=line.get("font_path"),
        )
    return canvas


def fit_text_size(content: str, max_width: int, max_height: int,
                  start_size: int = 200, font_path: str = None,
                  min_size: int = 20) -> int:
    """字号自动适配,确保文字在 max_width × max_height 内"""
    if font_path is None:
        font_path = FONT_PATHS["bold"]
    size = start_size
    while size > min_size:
        font = ImageFont.truetype(font_path, size)
        bbox = font.getbbox(content)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        if text_w <= max_width and text_h <= max_height:
            return size
        size -= 5
    return min_size