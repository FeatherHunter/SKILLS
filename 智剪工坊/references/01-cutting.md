# 01-cutting - 剪切 — v1.2 已实现

> **对应脚本**: `scripts/video_trim.py`
> **触发词**: "剪切"、"切这段"、"保留 X 秒"、"从 A 到 B"、"拼接"、"合并多个视频"
> **实测状态**: ✅ 验证通过

---

## 1. 调用范式

### 场景 1

```bash
# 帧级剪切
python scripts/video_trim.py trim --input v.mp4 --start 30 --t 20 --output out.mp4

# 拼接(concat demuxer)
python scripts/video_trim.py concat --list clips.txt --output joined.mp4
```

### 场景 2

```bash
ffmpeg -f concat -safe 0 -i concat_list.txt \
  -c:v libx264 -preset medium -crf 20 \
  -c:a aac -b:a 128k \
  _concat_raw.mp4
```

### 场景 3

```bash
ffmpeg -ss [start] -i [input] -t [dur] \
  -vf "scale=1080:1920:force_original_aspect_ratio=decrease,\
       pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,setsar=1,fps=30" \
  -c:v libx264 -preset medium -crf 20 \
  -c:a aac -b:a 128k \
  [output]
```

## 2. 参数

| 参数 | 短选项 | 默认值 | 说明 |
|---|---|---|---|
| `--input` | `-i` | (必填) | 输入视频/音频/图片 |
| `--output` | `-o` | (必填) | 输出路径 |

## 3. 常见错误 / 限制

- **Bug 2**(详见 SKILL.md):段 10 是 23.65fps 拼接后变 8 小时 → 强制 fps=30 修复

## 4. 相关参考

- **SKILL.md §14 子技能索引**：本子技能的路由表
- **scripts/README.md**：scripts/ 目录命名规范（`<维度>_<动作>.py`）
- `.archive/CHANGELOG.md`：本子技能历史变更

---

<details>
<summary>📋 原文存档（v0.5 旧版，仅供 git history 追溯）</summary>

# 01 - cutting (剪切 + 拼接) — v0.5 已实现

> **对应脚本:** `scripts/video_trim.py`(1 个,含 `trim` / `concat` 子命令)
> **实测状态:** ✅ 验证通过

```bash
# 帧级剪切
python scripts/video_trim.py trim --input v.mp4 --start 30 --t 20 --output out.mp4

# 拼接(concat demuxer)
python scripts/video_trim.py concat --list clips.txt --output joined.mp4
```

---

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

</details>
