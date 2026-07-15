"""
封面合成 lib/diagnostics.py
④ 数据层:像素级分析(brightness / alpha / bbox)

用户视角:
- "我刚生成的封面有半透明黑色,看不出来在哪 — 帮我扫一下"
- → diagnose.py 调用 lib/diagnostics.py 的函数
"""
from PIL import Image
import numpy as np
from typing import List, Dict, Any


def brightness_map(img: Image.Image) -> np.ndarray:
    """返回 (H, W) 的 brightness map(每个像素的 RGB 均值)"""
    arr = np.array(img.convert("RGB"))
    return arr.mean(axis=2)


def alpha_map(img: Image.Image) -> np.ndarray:
    """返回 (H, W) 的 alpha 通道;非 RGBA 图返回 255 全开"""
    if img.mode != "RGBA":
        return np.full((img.height, img.width), 255, dtype=np.uint8)
    return np.array(img)[:, :, 3]


def find_semi_transparent(img: Image.Image, alpha_lo=10, alpha_hi=245) -> Dict[str, Any]:
    """检测半透明像素(alpha ∈ [lo, hi])

    Returns:
        {
          "count": 像素数,
          "pct": 占比百分比,
          "warning": bool 是否有问题,
          "bbox": (x1, y1, x2, y2) 或 None
        }
    """
    a = alpha_map(img)
    semi = ((a >= alpha_lo) & (a <= alpha_hi))
    count = int(semi.sum())
    total = semi.size
    pct = round(100 * count / total, 2)
    warning = pct > 1.0  # >1% 视为异常

    bbox = None
    if count > 0:
        ys, xs = np.where(semi)
        bbox = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))

    return {
        "count": count,
        "pct": pct,
        "warning": warning,
        "bbox": bbox,
    }


def find_dark_areas(img: Image.Image, threshold=30) -> Dict[str, Any]:
    """检测过暗区域(RGB 全 < threshold)

    用于识别:
    - 全黑画布 + 没贴图 → 整张图都是暗色
    - 半透明黑叠加 → 局部暗色区
    """
    bright = brightness_map(img)
    dark = bright < threshold
    count = int(dark.sum())
    total = bright.size
    pct = round(100 * count / total, 2)
    warning = pct > 60  # >60% 整图过暗,可能全黑底

    return {
        "count": count,
        "pct": pct,
        "warning": warning,
        "threshold": threshold,
    }


def find_dark_areas_by_region(img: Image.Image, threshold=30,
                                min_region_size=500) -> List[Dict[str, Any]]:
    """逐区域检测暗斑(连接分量)

    Returns: list of {bbox, pixel_count, pct_of_image}
    """
    bright = brightness_map(img)
    dark = (bright < threshold).astype(np.uint8)

    # 简单实现:用 bbox 找连通区域太复杂,先用网格扫描
    H, W = dark.shape
    regions = []
    block_h, block_w = H // 8, W // 8  # 8x8 网格
    for by in range(8):
        for bx in range(8):
            block = dark[by*block_h:(by+1)*block_h, bx*block_w:(bx+1)*block_w]
            block_dark_pct = block.mean() * 100
            if block_dark_pct > 80:  # 80% 以上是暗色
                regions.append({
                    "bbox": (bx*block_w, by*block_h, (bx+1)*block_w, (by+1)*block_h),
                    "dark_pct": round(block_dark_pct, 1),
                })
    return regions


def symmetry_check(img: Image.Image) -> Dict[str, Any]:
    """检查左右对称性

    翻转左半和右半,比较 brightness map 的差异
    Returns:
        {
          "diff_pct": 差异百分比,
          "warning": bool,
          "left_weight": 左半平均 brightness,
          "right_weight": 右半平均 brightness
        }
    """
    bright = brightness_map(img)
    H, W = bright.shape
    mid = W // 2
    left = bright[:, :mid]
    right = np.fliplr(bright[:, W-mid:])  # 翻转对齐
    diff = np.abs(left.astype(int) - right.astype(int)).mean()
    diff_pct = round(100 * diff / 255, 2)
    warning = diff_pct > 8  # >8% 视为明显不对称

    return {
        "diff_pct": diff_pct,
        "warning": warning,
        "left_brightness": round(float(left.mean()), 1),
        "right_brightness": round(float(right.mean()), 1),
    }


def full_diagnose(img: Image.Image) -> Dict[str, Any]:
    """一次性跑所有诊断,返回综合报告"""
    semi = find_semi_transparent(img)
    dark = find_dark_areas(img)
    dark_regions = find_dark_areas_by_region(img)
    sym = symmetry_check(img)

    issues = []
    if bool(semi.get("warning")):
        issues.append({
            "type": "semi_transparent_pixels",
            "severity": "high",
            "detail": f"{semi['count']} 像素({semi['pct']}%)alpha ∈ [10,245],通常来自旋转/羽化残留",
            "suggestion": "用 rotate_hard() 替代 rotate(expand=True);不要用 alpha 羽化",
        })
    if bool(dark.get("warning")):
        issues.append({
            "type": "too_much_dark",
            "severity": "med",
            "detail": f"{dark['pct']}% 像素 RGB < 30,可能全黑底或半透明黑叠加",
            "suggestion": "检查画布色 + shadow 扩散 + z-order",
        })
    if bool(sym.get("warning")):
        issues.append({
            "type": "asymmetric",
            "severity": "med",
            "detail": f"左右 diff {sym['diff_pct']}%(阈值 8%)",
            "suggestion": "对称布局时:左图 left_x 和右图 right_x 应镜像于画布中心",
        })

    return {
        "status": "warn" if issues else "ok",
        "issues": issues,
        "details": {
            "semi_transparent": semi,
            "dark_areas": dark,
            "dark_regions": dark_regions,
            "symmetry": sym,
        },
    }