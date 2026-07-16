# presets 子命令

> 详见 SKILL.md §② 子命令 3。

## 用法

```bash
# 列出所有预设
封面合成 presets --list

# 查特定平台
封面合成 presets --platform douyin
封面合成 presets --platform bilibili
封面合成 presets --platform shipinhao

# 按比例查
封面合成 presets --aspect 16:9
封面合成 presets --aspect 9:16
```

## 支持的平台

| 平台 | 比例 | 尺寸 |
|---|---|---|
| douyin (抖音) | 9:16 | 1080×1920 |
| shipinhao (视频号) | 3:4 | 1080×1440 |
| xiaohongshu (小红书) | 4:5 | 1080×1350 |
| kuaishou (快手) | 9:16 | 1080×1920 |
| bilibili (B 站) | 16:9 | 1920×1080 |
| youtube | 16:9 | 1920×1080 |
| weibo (微博) | 16:9 | 1280×720 |
| cover_16_9 (通用横屏) | 16:9 | 1920×1080 |
| cover_9_16 (通用竖屏) | 9:16 | 1080×1920 |
| cover_4_3 (通用 4:3) | 4:3 | 1440×1080 |
| cover_1_1 (通用方形) | 1:1 | 1080×1080 |

## 用 preset 决定 --aspect

```bash
# 抖音封面:9:16
封面合成 presets --platform douyin  # → {"ratio": "9:16", ...}
封面合成 compose --aspect 9:16 ...  # 用 9:16
```