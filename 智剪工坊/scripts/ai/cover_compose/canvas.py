"""
③ 业务层 / ④ 基础设施:标准化画布创建 + 智能保存(RGBA/RGB 切换)

设计要点:
- 默认 RGBA 模式,允许透明合成
- 默认纯黑底色 — JPG 导出时透明区域自然变黑,无色彩断裂
- safe_save 自动判断输出格式(.png 留 alpha,.jpg 强制 RGB)
"""
from PIL import Image
from pathlib import Path
from typing import Tuple
import os


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """hex → RGB tuple,支持 '#FFF' / '#FFFFFF' / 'FFF' / 'FFFFFF'"""
    s = hex_color.lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


def make_canvas(width: int, height: int, bg_color="#000000") -> Image.Image:
    """创建 RGBA 画布

    关键:
    - RGBA 模式(alpha 默认 255,完全不透明)
    - bg_color 默认纯黑(避免 JPG 导出时透明区域颜色断裂)
    - 返回 Image 对象,可直接 paste RGBA 图层
    """
    bg = hex_to_rgb(bg_color) if isinstance(bg_color, str) else bg_color
    canvas = Image.new("RGBA", (width, height), bg + (255,))
    return canvas


def safe_save(canvas: Image.Image, output_path: str) -> str:
    """智能保存

    - .png → RGBA(alpha 保留)
    - .jpg/.jpeg → RGB(强制转,丢掉 alpha)
    - 自动 .bak 已有同名文件(YYYYMMDD_HHMMSS_mmm + pid 后缀,防同秒冲突)

    Returns: 实际保存的路径(可能加了 .bak 后缀如果原文件存在)
    """
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    # 备份已有文件(用毫秒 + 进程 id 防连续调用冲突)
    if p.exists():
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # 毫秒精度
        bak = p.with_suffix(f".{ts}_pid{os.getpid()}{p.suffix}")
        # 如果 bak 已存在(极端情况),追加数字
        n = 1
        while bak.exists():
            bak = p.with_suffix(f".{ts}_pid{os.getpid()}_{n}{p.suffix}")
            n += 1
        p.rename(bak)

    # 按扩展名决定格式
    ext = p.suffix.lower()
    if ext in (".jpg", ".jpeg"):
        if canvas.mode == "RGBA":
            canvas = canvas.convert("RGB")
        canvas.save(p, quality=92)
    elif ext == ".png":
        canvas.save(p)
    else:
        # 未知扩展名 → 默认 PNG
        canvas.save(p.with_suffix(".png"))

    return str(p)


def hex_to_color(color):
    """统一接受 hex str / RGB tuple / RGBA tuple"""
    if isinstance(color, str):
        return hex_to_rgb(color)
    return color
