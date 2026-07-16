"""
封面合成 infra/diagnostics.py
④ 基础设施:像素级分析(brightness / alpha / bbox / dominant color / shape)

用户视角:
- "我刚生成的封面有半透明黑色,看不出来在哪 — 帮我扫一下"
- → operations/diagnose.py 调用这里的函数
- "我有多张图片,帮我分析每张的尺寸/主色/亮度,决定怎么排"
- → operations/auto_compose.py 调用 analyze_image()
"""
from PIL import Image
import numpy as np
from typing import List, Dict, Any, Tuple


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


# ============================================================================
# analyze_image():给 auto_compose 用的"读图"函数(不只诊断,还提取特征)
# ============================================================================

def dominant_color(img: Image.Image, sample_step: int = 10) -> Tuple[int, int, int]:
    """计算图片的 dominant color(去 alpha 透明区后取均值)

    sample_step: 采样步长(每隔 N 像素采 1 个,加快计算)
    Returns: (R, G, B) 0-255
    """
    rgb = img.convert("RGB")
    H, W = rgb.size[1], rgb.size[0]

    # 取 alpha 掩码(如果是 RGBA,只算不透明像素)
    if img.mode == "RGBA":
        alpha = img.split()[3]
        mask_arr = np.array(alpha) > 128
        if mask_arr.any():
            arr = np.array(rgb)[mask_arr]  # (N, 3)
        else:
            # 全透明,降采样
            arr = np.array(rgb)[::sample_step, ::sample_step, :].reshape(-1, 3)
    else:
        arr = np.array(rgb)[::sample_step, ::sample_step, :].reshape(-1, 3)

    if arr.size == 0:
        return (0, 0, 0)

    # arr 现在保证是 (N, 3) shape
    mean_vals = arr.mean(axis=0)
    # mean_vals 是长度为 3 的 numpy 数组
    return (int(mean_vals[0]), int(mean_vals[1]), int(mean_vals[2]))


def mean_brightness(img: Image.Image) -> float:
    """图片平均亮度 0-255"""
    return float(brightness_map(img).mean())


def contrast_score(img: Image.Image) -> float:
    """图片对比度评分:高对比(亮暗差大)→ 高分"""
    bright = brightness_map(img)
    return float(bright.std())


def analyze_image(path: str) -> Dict[str, Any]:
    """分析单张图片的"关键特征",给 auto_compose 决策用

    Returns:
        {
          "path": str,
          "width": int, "height": int,
          "ratio": float (w/h),
          "orientation": "portrait" | "landscape" | "square",
          "dominant_color": (R, G, B),
          "mean_brightness": float (0-255),
          "contrast_score": float (标准差,越大越对比),
          "is_photo": bool (判断是否真照片,而不是单色图),
        }
    """
    from PIL import Image as PILImage
    import os

    p = PILImage.open(path)
    W, H = p.size
    ratio = W / H

    if abs(ratio - 1) < 0.05:
        orientation = "square"
    elif ratio > 1:
        orientation = "landscape"
    else:
        orientation = "portrait"

    dom = dominant_color(p)
    bright = mean_brightness(p)
    contrast = contrast_score(p)

    # 判断是否"真照片":对比度 > 20 且 亮度在 30-225 之间
    is_photo = (contrast > 20) and (30 < bright < 225)

    return {
        "path": path,
        "filename": os.path.basename(path),
        "width": W,
        "height": H,
        "ratio": round(ratio, 3),
        "orientation": orientation,
        "dominant_color": dom,
        "mean_brightness": round(bright, 1),
        "contrast_score": round(contrast, 1),
        "is_photo": is_photo,
    }


def decide_layout(photo_analyses: List[Dict[str, Any]]) -> str:
    """根据图片分析结果决定 layout

    决策逻辑:
    - 1 张图 → cascade(主图,无副图)
    - 2 张图 → symmetric-cascade
    - 3 张图 → symmetric-cascade(默认)
    - 4+ 张图 → polaroid
    - 任何 square 多图 → grid
    """
    n = len(photo_analyses)
    if n == 1:
        return "cascade"
    if n == 2:
        return "symmetric-cascade"
    if n == 3:
        return "symmetric-cascade"
    if all(p["orientation"] == "square" for p in photo_analyses):
        return "grid"
    return "polaroid"


def decide_aspect(photo_analyses: List[Dict[str, Any]]) -> str:
    """根据图片主方向决定画布比例

    - 全 portrait(竖图)→ 9:16(竖屏)
    - 全 landscape(横图)→ 16:9(横屏)
    - 混合或 square → 16:9(默认)
    """
    orientations = [p["orientation"] for p in photo_analyses]
    if all(o == "portrait" for o in orientations):
        return "9:16"
    if all(o == "landscape" for o in orientations):
        return "16:9"
    return "16:9"  # 默认


def decide_bg(photo_analyses: List[Dict[str, Any]]) -> str:
    """根据主图主色决定画布底色

    - 主图亮(> 128)→ 用主图主色作为背景
    - 主图暗 → 用纯黑 #000000
    - 主图无主色(全白/全黑)→ 用纯黑
    """
    if not photo_analyses:
        return "#000000"

    main = photo_analyses[0]
    bright = main["mean_brightness"]
    contrast = main["contrast_score"]

    if contrast < 15:
        return "#000000"  # 单色图,用纯黑

    if bright > 128:
        # 主图亮 → 用主图主色作为画布底色
        r, g, b = main["dominant_color"]
        return f"#{r:02x}{g:02x}{b:02x}"
    else:
        # 主图暗 → 用纯黑
        return "#000000"


def decide_text(photo_analyses: List[Dict[str, Any]], hint: str = None) -> Dict[str, Any]:
    """根据图片分析 + hint 生成文字层

    hint 可以是:
    - None → 自动从文件名提取关键词
    - str → 用户给的关键词
    - dict → 用户指定的具体文字
    """
    if hint is None:
        # 自动从第一个文件名提取
        if photo_analyses:
            from pathlib import Path
            stem = Path(photo_analyses[0]["path"]).stem
            # 简单提取:去掉数字 + 后缀
            import re
            cleaned = re.sub(r'[_\-\d\W]+', ' ', stem).strip()
            if cleaned:
                return {"main": cleaned, "sub": "", "tags": ""}
        return {}

    if isinstance(hint, str):
        return {"main": hint, "sub": "", "tags": ""}

    if isinstance(hint, dict):
        return hint

    return {}