# muted 视频拼接风险（v1.10 历史 bug）

> 本文档记录 v1.10 修复的 muted 视频拼接时长异常 bug，供未来参考。
> SKILL.md 不再保留此细节；如遇同类问题加载本文件。

## 核心问题

用 `-an`（去除音频）处理过的 mp4，可能残留 audio metadata 在 moov atom 中。这会导致后续 `trim.py concat` 时：

- ffmpeg 强行对齐 audio PTS → video 被压缩/拉长
- sequence 显示时长异常（过短或过长，例如 130 分钟）

## 触发场景

- `voice: "mute"` 的 video 后面拼接有 audio 的 video
- 多个 muted segments 互相拼接（累积偏移）

## 解决方案

### 方案 A（单 video 层 — 推荐）：mute 时强制 remux 清残留

```python
def remux_clean_residual_metadata(video_path):
    tmp = video_path.with_suffix(".clean.mp4")
    run_ffmpeg([
        "-y", "-i", str(video_path),
        "-map", "0:v",            # 只映射 video，丢弃 audio
        "-c", "copy",             # 不重编码
        "-map_metadata", "-1",    # 清空 metadata
        "-movflags", "+faststart",
        str(tmp),
    ])
    Path(tmp).replace(video_path)
```

### 方案 B（sequence 层）：用 filter_complex concat，每个 muted segment 加 anullsrc 占位 audio

```bash
ffmpeg -i seg1.mp4 -i seg2.mp4 -filter_complex \
  "anullsrc=cl=stereo:r=44100[a1];anullsrc=cl=stereo:r=44100[a2]; \
   [0:v][a1][1:v][a2]concat=n=2:v=1:a=1[v][a]" \
  -map "[v]" -map "[a]" output.mp4
```

## 检测方法

```bash
ffmpeg -i input.mp4 2>&1 | grep -A 1 "Stream #0"
# 如果 muted mp4 仍有 "Stream #0:1.*Audio" 行，说明残留
```

## v1.10 自动处理

`trim.py concat` 已加 pre-process，自动检测并清理残留 metadata。