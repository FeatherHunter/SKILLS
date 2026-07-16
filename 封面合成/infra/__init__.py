"""infra/ ④ 基础设施层入口

按手册 ④ 数据层职责,这里只放:
- 纯函数(无业务逻辑)
- 可被 core/ 调用的基础设施
- 没有任何 CLI 入口

子模块(都加 cover_ 前缀,与其它 Skill 区分):
- cover_canvas:    RGBA 画布 + 智能保存
- cover_diagnostics: 像素分析 + 图片特征分析(给 auto_compose 用)
- cover_presets_data: 平台规格常量

依赖方向:infra 不 import 上层(operations / core)
"""
from infra.cover_canvas import make_canvas, safe_save, hex_to_rgb, hex_to_color
from infra.cover_diagnostics import (
    brightness_map, alpha_map,
    find_semi_transparent, find_dark_areas, find_dark_areas_by_region,
    symmetry_check, full_diagnose,
    dominant_color, mean_brightness, contrast_score,
    analyze_image, decide_layout, decide_aspect, decide_bg, decide_text,
)
from infra.cover_presets_data import PLATFORM_SPECS, SAFE_AREA_4_3_IN_16_9, SAFE_AREA_9_16, FONT_PATHS

__all__ = [
    # cover_canvas
    "make_canvas", "safe_save", "hex_to_rgb", "hex_to_color",
    # cover_diagnostics - 像素分析
    "brightness_map", "alpha_map",
    "find_semi_transparent", "find_dark_areas", "find_dark_areas_by_region",
    "symmetry_check", "full_diagnose",
    # cover_diagnostics - 图片特征分析(给 auto_compose 用)
    "dominant_color", "mean_brightness", "contrast_score",
    "analyze_image", "decide_layout", "decide_aspect", "decide_bg", "decide_text",
    # cover_presets_data
    "PLATFORM_SPECS", "SAFE_AREA_4_3_IN_16_9", "SAFE_AREA_9_16", "FONT_PATHS",
]
