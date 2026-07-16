"""
封面合成 scripts/diagnose.py
③ 业务层:诊断子命令入口

CLI:
    cover-composer diagnose --image x.jpg [--check transparency,darkness,symmetry]

输出:
    {
      "status": "ok" | "warn" | "error",
      "data": {
        "image": "x.jpg",
        "size": [1920, 1080],
        "semi_transparent": {...},
        "dark_areas": {...},
        "dark_regions": [...],
        "symmetry": {...}
      },
      "message": "...",
      "warnings": [...]
    }
"""
from PIL import Image
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from infra.cover_diagnostics import (
    find_semi_transparent, find_dark_areas, find_dark_areas_by_region,
    symmetry_check, full_diagnose,
)


def diagnose_image(image_path: str, checks: list = None) -> dict:
    """诊断一张图片

    Args:
        image_path: 图片路径
        checks: ['transparency', 'darkness', 'symmetry', 'all']
                默认 ['all']
    """
    if checks is None:
        checks = ['all']

    p = Path(image_path)
    if not p.exists():
        return {
            "status": "error",
            "message": f"图片不存在:{image_path}",
            "data": {},
        }
    if not p.is_file():
        return {
            "status": "error",
            "message": f"路径不是文件:{image_path}",
            "data": {},
        }

    try:
        img = Image.open(p)
    except Exception as e:
        return {
            "status": "error",
            "message": f"图片打开失败:{e}",
            "data": {},
        }

    result = {"image": str(p), "size": list(img.size)}

    if "all" in checks or "transparency" in checks:
        result["semi_transparent"] = find_semi_transparent(img)
    if "all" in checks or "darkness" in checks:
        result["dark_areas"] = find_dark_areas(img)
        result["dark_regions"] = find_dark_areas_by_region(img)
    if "all" in checks or "symmetry" in checks:
        result["symmetry"] = symmetry_check(img)

    # 汇总警告
    warnings = []
    if "all" in checks or "transparency" in checks:
        if bool(result["semi_transparent"]["warning"]):
            warnings.append({
                "type": "semi_transparent",
                "severity": "high",
                "pct": result["semi_transparent"]["pct"],
                "suggestion": "检查 rotate_hard() 调用;alpha 通道必须二值化",
            })
    if "all" in checks or "darkness" in checks:
        if bool(result["dark_areas"]["warning"]):
            warnings.append({
                "type": "too_dark",
                "severity": "med",
                "pct": result["dark_areas"]["pct"],
                "suggestion": "检查画布色 + shadow 扩散 + z-order",
            })
    if "all" in checks or "symmetry" in checks:
        if bool(result["symmetry"]["warning"]):
            warnings.append({
                "type": "asymmetric",
                "severity": "med",
                "diff_pct": result["symmetry"]["diff_pct"],
                "suggestion": "对称布局时 left_x 和 right_x 应镜像于画布中心",
            })

    status = "warn" if warnings else "ok"
    return {
        "status": status,
        "data": result,
        "message": f"诊断完成:{'有警告' if warnings else '无问题'}",
        "warnings": warnings,
    }