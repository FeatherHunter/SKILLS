"""
封面合成 lib/presets_data.py
④ 数据层:平台规格常量(不存数据库,纯静态数据)

来源:各平台官方文档 + 实测常用值
"""
from typing import Tuple

# 平台尺寸规格(宽, 高)
PLATFORM_SPECS = {
    # 短视频/竖屏
    "douyin":       {"ratio": (9, 16), "size": (1080, 1920), "name": "抖音"},
    "shipinhao":    {"ratio": (3, 4),  "size": (1080, 1440), "name": "视频号"},
    "xiaohongshu":  {"ratio": (4, 5),  "size": (1080, 1350), "name": "小红书"},
    "kuaishou":     {"ratio": (9, 16), "size": (1080, 1920), "name": "快手"},

    # 长视频/横屏
    "bilibili":     {"ratio": (16, 9), "size": (1920, 1080), "name": "B 站"},
    "youtube":      {"ratio": (16, 9), "size": (1920, 1080), "name": "YouTube"},
    "weibo":        {"ratio": (16, 9), "size": (1280, 720),  "name": "微博"},

    # 通用
    "cover_16_9":   {"ratio": (16, 9), "size": (1920, 1080), "name": "16:9 横屏封面"},
    "cover_9_16":   {"ratio": (9, 16), "size": (1080, 1920), "name": "9:16 竖屏封面"},
    "cover_4_3":    {"ratio": (4, 3),  "size": (1440, 1080), "name": "4:3 横屏封面"},
    "cover_1_1":    {"ratio": (1, 1),  "size": (1080, 1080), "name": "1:1 方形封面"},
}

# 4:3 安全区(用于横屏封面,确保平台裁切不切到重要内容)
# 横屏画布 16:9,4:3 安全区是中间 1440x1080 区域,左右各 240px 黑色边带
SAFE_AREA_4_3_IN_16_9 = {
    "x_min": 240, "x_max": 1680,
    "y_min": 0,   "y_max": 1080,
    "description": "横屏 16:9 画布的中央 4:3 安全区,左右各 240px 黑色边带"
}

# 9:16 安全区(竖屏封面,确保不被平台 UI 遮挡)
SAFE_AREA_9_16 = {
    "x_min": 0,   "x_max": 1080,
    "y_min": 200, "y_max": 1680,  # 顶部 200 + 底部 240 留给平台 UI
    "description": "竖屏 9:16 画布的安全区,避开顶部标题栏 + 底部评论栏"
}

# 字体路径(Windows 默认字体)
FONT_PATHS = {
    "bold":    r"C:\Windows\Fonts\msyhbd.ttc",  # 微软雅黑 Bold
    "normal":  r"C:\Windows\Fonts\msyh.ttc",     # 微软雅黑 Regular
    "fallback": r"C:\Windows\Fonts\simsun.ttc",  # 宋体 fallback
}