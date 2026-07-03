# fonts/

字体文件(用于烧字幕、叠封面字)。

## Windows(默认)

不需要额外装,系统自带:
- `C:\Windows\Fonts\msyh.ttc` —— 微软雅黑
- `C:\Windows\Fonts\msyhbd.ttc` —— 微软雅黑 Bold
- `C:\Windows\Fonts\simhei.ttf` —— 黑体
- `C:\Windows\Fonts\simsun.ttc` —— 宋体

## Mac

- `/Library/Fonts/PingFang.ttc` —— 苹方
- `/System/Library/Fonts/STHeiti Medium.ttc` —— 华文黑体

## Linux

- `fonts-noto-cjk` —— Noto Sans CJK
- `fonts-wqy-microhei` —— 文泉驿微米黑
- `fonts-wqy-zenhei` —— 文泉驿正黑

## 推荐下载(开源字体)

| 字体 | 用途 | 链接 |
|---|---|---|
| Noto Sans CJK SC | 中英文兼容,开源 | Google Fonts |
| Source Han Sans | 思源黑体,Adobe + Google | source-han-sans |
| 思源宋体 | Source Han Serif,优雅 | source-han-serif |

## 当前状态

🚧 **空目录** —— 默认用 Windows 系统字体,不需下载。

如果需要换字体,把 .ttf / .otf / .ttc 放这里,修改 `cover_ai.py` / `burn_subtitle.py` 里的 `FONT_BOLD` / `FONT_NORMAL` 路径。