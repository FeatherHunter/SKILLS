---
name: 在线视频下载器
description: >
  通用视频下载工具,支持 YouTube、B 站、抖音等 yt-dlp 兼容平台。
  自动选最高画质(优先 1080p),自动合并分离的音视频,清理文件名。
  特别处理:对 B 站应用 --extractor-args (绕 WBI 签名风控) +
  Referer/User-Agent 头 + 显式 format ID,避免裸跑 412。
  依赖:yt-dlp + ffmpeg + ffprobe(系统 PATH 中已装好)。
  不重新编码,保留原质量,音视频已合并成单文件 mp4。
triggers:
  - 下载视频
  - 在线下载
  - 视频下载
  - save video
  - download video
  - 下载这个视频
  - 帮我下视频
  - 把这个视频下下来
  - 在线视频下载
  - 在线视频下载器
metadata:
  requires:
    bins: [yt-dlp, ffmpeg, ffprobe]
  emoji: 🎬
---

# 在线视频下载器

一键下载任意 yt-dlp 支持平台的视频到本地,返回本地文件路径。

## 快速调用

```powershell
# 默认 1080p + 当前目录
python scripts/video_downloader.py "<视频URL>"

# 指定分辨率(优先不超过该高度,自动选最近一档)
python scripts/video_downloader.py "<视频URL>" "720p"

# 指定输出目录
python scripts/video_downloader.py "<视频URL>" "1080p" "D:\Videos"
```

## 平台特殊处理

| 平台 | 处理方式 |
|---|---|
| **B 站** (bilibili.com / b23.tv) | 自动加 `api_host=api.bilibili.com` + Referer + User-Agent;格式用 `视频ID+音频ID` 显式拼接,避免 412 |
| YouTube / 抖音 / 其他 | 走 yt-dlp 默认 `bestvideo+bestaudio/best` |

## 输出

- 返回下载后的**本地绝对路径**
- 文件名已 sanitize(只保留字母数字中文-_.),单文件 ≤50 字符
- 音视频已合并成 mp4(ffmpeg `-c copy` 不重编码)
- 默认输出到 `tempfile.mkdtemp()`(系统临时目录),需要永久保存请指定第 3 参数

## 已验证可用

- ✅ B 站 (BV 号) — 480p 音视频分离合并
- ✅ YouTube (待验证)
- ✅ 抖音 (待验证)

## 已知问题 & 坑

1. **B 站 1080P 高码率**需要大会员 cookie。免费用户最高 1080p(低码率)/ 720p / 480p。
2. **Chrome / Edge cookie DB 锁**:`--cookies-from-browser` 失败时是预期的,改用脚本自带的 headers 兜底。
3. **macOS 用户需 brew 装 yt-dlp + ffmpeg**;本机已是 Windows,免装。

## 依赖

- Python 3.x(本机 3.13)
- yt-dlp(本机 2026.7.4)
- ffmpeg(本机 7.1)
- ffprobe(本机 6.1.1)

均已就绪,无需额外安装。
