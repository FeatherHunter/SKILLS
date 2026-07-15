"""
封面合成 scripts/layers.py
③ 业务层:图层原子操作(旋转 / 羽化 / alpha 二值化 / 放置)

⭐ 核心:封装今天踩的所有坑
- rotate_hard: 硬旋转,临时大画布 + bbox 裁切 + alpha 二值化
- binarize_alpha: 防止 anti-aliasing 残影
- place: 纯硬贴,无 shadow 无 feathering
"""
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from math import sqrt
from typing import Tuple
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.canvas import hex_to_rgb


def rotate_hard(path: str, target_w: int, target_h: int, angle: float) -> Image.Image:
    """硬旋转 ⭐ 关键函数

    流程:
    1. 加载 + 缩放到 target size
    2. 转 RGBA(防止旋转后填充黑色)
    3. 创建比图大的临时画布(对角线 + 余量)
    4. 在画布中心 paste 图
    5. 旋转整个画布(中心旋转)
    6. 裁切到内容 bbox(去掉 alpha=0 的新角)
    7. alpha 二值化(>128 → 255,否则 0)消除 anti-aliasing 残影

    防坑:
    - #1 RGB 旋转填充黑色
    - #2 alpha 羽化导致半透明黑
    - #6 旋转后角是黑色实色
    - #13 旋转后角是 fill 颜色而不是透明
    """
    im = Image.open(path).convert("RGB").resize((target_w, target_h), Image.LANCZOS)
    w, h = im.size
    diag = int(sqrt(w ** 2 + h ** 2)) + 20
    rgba = im.convert("RGBA")

    # 临时大画布,paste 原图到中心
    temp = Image.new("RGBA", (diag, diag), (0, 0, 0, 0))
    temp.paste(rgba, ((diag - w) // 2, (diag - h) // 2), rgba)

    # 旋转
    rotated = temp.rotate(angle, resample=Image.BICUBIC, expand=False)

    # 裁切到内容 bbox
    bbox = rotated.getbbox()
    if bbox:
        cropped = rotated.crop(bbox)
    else:
        cropped = rotated

    # alpha 二值化
    return binarize_alpha(cropped)


def binarize_alpha(rgba: Image.Image) -> Image.Image:
    """alpha 通道二值化

    >128 → 255(opaque)
    否则 → 0(transparent)

    原因:
    - PIL rotate 抗锯齿产生中间值 alpha
    - 中间值跟画布混合 → 半透明黑
    - 二值化彻底消除
    """
    if rgba.mode != "RGBA":
        rgba = rgba.convert("RGBA")
    r, g, b, a = rgba.split()
    a_arr = np.array(a)
    a_bin = (a_arr > 128).astype(np.uint8) * 255
    return Image.merge("RGBA", (r, g, b, Image.fromarray(a_bin, mode="L")))


def place(canvas: Image.Image, img: Image.Image, x: int, y: int) -> Image.Image:
    """纯硬贴图层(无 shadow 无 feathering)

    canvas 必须是 RGBA
    img 会被转 RGBA,自动用 alpha 作为 mask
    """
    if canvas.mode != "RGBA":
        canvas = canvas.convert("RGBA")
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    canvas.paste(img, (x, y), img)
    return canvas


def text_layer(canvas: Image.Image, content: str, position: str,
               font_size: int = 64, font_color=(255, 215, 0),
               outline_color=(0, 0, 0), outline_width: int = 4,
               font_path: str = None) -> Image.Image:
    """文字水印层

    position: 'top-center' / 'middle-center' / 'bottom-center'
              / 'top-left' / 'top-right' 等 9 宫格

    防坑:
    - #10 文字无描边,在亮色照片上读不清
    """
    if canvas.mode != "RGBA":
        canvas = canvas.convert("RGBA")
    draw = ImageDraw.Draw(canvas)
    W, H = canvas.size

    # 字体
    if font_path is None:
        from lib.presets_data import FONT_PATHS
        font_path = FONT_PATHS["bold"]
    font = ImageFont.truetype(font_path, font_size)

    # 计算位置
    bbox = draw.textbbox((0, 0), content, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    positions = {
        "top-center": ((W - text_w) // 2, 80),
        "middle-center": ((W - text_w) // 2, (H - text_h) // 2),
        "bottom-center": ((W - text_w) // 2, H - text_h - 80),
        "top-left": (80, 80),
        "top-right": (W - text_w - 80, 80),
        "bottom-left": (80, H - text_h - 80),
        "bottom-right": (W - text_w - 80, H - text_h - 80),
        "middle-left": (80, (H - text_h) // 2),
        "middle-right": (W - text_w - 80, (H - text_h) // 2),
    }
    x, y = positions.get(position, positions["middle-center"])

    draw.text((x, y), content, font=font, fill=font_color,
              stroke_width=outline_width, stroke_fill=outline_color)
    return canvas


def fit_text_to_area(canvas: Image.Image, content: str, max_width: int,
                     max_height: int, start_size: int = 200,
                     font_path: str = None,
                     font_color=(255, 215, 0),
                     outline_color=(0, 0, 0),
                     outline_ratio: float = 0.05) -> int:
    """字号自动适配,确保文字在 max_width × max_height 内

    Returns: 实际使用的字号
    """
    if font_path is None:
        from lib.presets_data import FONT_PATHS
        font_path = FONT_PATHS["bold"]

    size = start_size
    while size > 20:
        font = ImageFont.truetype(font_path, size)
        bbox = font.getbbox(content)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        if text_w <= max_width and text_h <= max_height:
            return size
        size -= 5
    return 20