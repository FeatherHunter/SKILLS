# 01 - cutting (剪切 + 拼接)

## 触发词

"剪切"、"切这段"、"保留 X 秒"、"从 A 到 B"、"拼接"、"合并多个视频"

## 输入 / 输出

- **输入**: 1-N 个视频文件路径
- **输出**: 剪切后的片段 / 拼接后的成片

## 参数

| 参数 | 说明 | 默认 |
|---|---|---|
| `--input` | 输入文件 | 必填 |
| `--ss` | 起始时间(秒) | 0 |
| `--t` | 时长(秒) | 视频剩余 |
| `--output` | 输出文件 | 必填 |
| `--resolution` | 输出分辨率 | 1080x1920 |
| `--fps` | 帧率 | 30 |
| `--vcodec` | 视频编码 | libx264 |
| `--crf` | 质量 | 20 |

## 拼接(concat)

```bash
ffmpeg -f concat -safe 0 -i concat_list.txt \
  -c:v libx264 -preset medium -crf 20 \
  -c:a aac -b:a 128k \
  _concat_raw.mp4
```

`concat_list.txt` 格式:
```
file 'clip1.mp4'
file 'clip2.mp4'
file 'clip3.mp4'
```

## 核心命令

```bash
ffmpeg -ss [start] -i [input] -t [dur] \
  -vf "scale=1080:1920:force_original_aspect_ratio=decrease,\
       pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,setsar=1,fps=30" \
  -c:v libx264 -preset medium -crf 20 \
  -c:a aac -b:a 128k \
  [output]
```

## 调用示例

```
用户: "把这段视频从 30 秒开始,保留 20 秒"
→ cut --input video.mp4 --ss 30 --t 20 --output clip.mp4
```

```
用户: "把这 3 段视频按顺序拼起来"
→ cut --concat --inputs clip1.mp4,clip2.mp4,clip3.mp4 --output joined.mp4
```

## 限制 / 注意

1. **强制 fps=30**:不同原始视频 fps 不一致会导致拼接 bug,统一 30
2. **强制分辨率**:统一 1080x1920(竖屏 vlog)避免拼接时 filter graph reconfig 崩溃
3. **统一编码**:libx264 比 NVENC 稳(避免 Access Violation)

## 已知 Bug

- **Bug 2**(详见 SKILL.md):段 10 是 23.65fps 拼接后变 8 小时 → 强制 fps=30 修复