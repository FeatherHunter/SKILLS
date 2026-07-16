"""
封面合成 scripts/presets.py
③ 业务层:预设模板查询

CLI:
    cover-composer presets [--platform douyin] [--aspect 16:9]
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from infra.cover_presets_data import PLATFORM_SPECS, SAFE_AREA_4_3_IN_16_9, SAFE_AREA_9_16


def get_preset(platform: str = None, aspect: str = None) -> dict:
    """查询预设

    Args:
        platform: douyin / bilibili / shipinhao / xiaohongshu / kuaishou / youtube / weibo
                  或通用 cover_16_9 / cover_9_16 / cover_4_3 / cover_1_1
        aspect: 16:9 / 9:16 / 4:3 / 1:1 (会查找匹配的 cover_* preset)

    Returns:
        {
          "platform": ...,
          "ratio": "16:9",
          "size": [1920, 1080],
          "name": "...",
          "safe_area": {...}  # 仅 16:9 / 9:16 有
        }
    """
    if platform:
        if platform in PLATFORM_SPECS:
            spec = PLATFORM_SPECS[platform].copy()
            ratio = f"{spec['ratio'][0]}:{spec['ratio'][1]}"
            spec["ratio"] = ratio
            spec["size"] = list(spec["size"])
            # 加 safe_area
            if ratio == "16:9":
                spec["safe_area"] = SAFE_AREA_4_3_IN_16_9
            elif ratio == "9:16":
                spec["safe_area"] = SAFE_AREA_9_16
            return spec
        return {"error": f"未知平台:{platform}", "available": sorted(PLATFORM_SPECS.keys())}

    if aspect:
        # 找匹配的通用 preset
        for k, v in PLATFORM_SPECS.items():
            if v["ratio"] == tuple(int(x) for x in aspect.split(":")):
                spec = v.copy()
                spec["ratio"] = aspect
                spec["size"] = list(spec["size"])
                return spec
        return {"error": f"未知比例:{aspect}", "available_ratios": sorted(set(
            f"{v['ratio'][0]}:{v['ratio'][1]}" for v in PLATFORM_SPECS.values()
        ))}

    return PLATFORM_SPECS


def list_presets() -> dict:
    """列出所有预设"""
    return PLATFORM_SPECS