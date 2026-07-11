# Rotation Metadata 3 层坑 — 视频 rotation 处理完整指南

> **何时加载**: AI 处理任何带 displaymatrix / rotation 字段的视频源时(手机竖屏拍摄最常见)
> **目的**: 把"3 层 rotation bug"的处理协议固化进 skill,所有加载此 skill 的 AI 自动规避
> **作者注**: 2026-07-11 DAY9 任务踩坑沉淀(智剪工坊 v1.13)

---

## ⚠️ 核心问题:rotation 处理有 3 层隐藏坑

### 坑 1:displaymatrix 残留

**症状**: 输出文件仍带 `displaymatrix: rotation of -90.00 degrees`,在部分播放器(剪映/微信/部分渲染器)中会"再旋转一次"。

**成因**:
- `-noautorotate` **只阻止 ffmpeg 自动应用** rotation
- **不会清** displaymatrix metadata
- 编码后 metadata 还在

**修复**:
```python
from lib.video.patch_mp4_rotation import patch_mp4_rotation
patch_mp4_rotation(Path(output_path), 0)  # 0 = 清成 identity
```

---

### 坑 2:user metadata `rotate=90` 残留(理论存在)

**症状**: 即使 tkhd matrix 已清,部分播放器(尤其是 iOS/微信)优先读 user metadata,导致"又旋转"。

**成因**:
- mp4 容器除了 tkhd matrix,还可存 user metadata `rotate=90`(QuickTime 风格)
- ffmpeg 默认不传播,但理论存在

**实测**: 2026-07-11 DAY9 任务实测修复后 3 个文件**无此残留**。
**修复**(防御性):
```bash
ffmpeg -i input.mp4 -map 0 -c copy \
  -map_metadata -1 \
  -metadata:s:v:0 rotate=0 \
  output.mp4
```

---

### 坑 3:filter_complex 传播 displaymatrix

**症状**: `trim.py` / `xfade.py` / `concat` 内部用 `filter_complex`,**会把 input stream 的 side data(displaymatrix)传播到 output**。

**成因**: ffmpeg filter graph 默认 propagate stream metadata / side data,除非显式 `-map_metadata -1` 或 patch tkhd。

**修复**: trim.py / xfade.py 结尾应 patch_mp4_rotation 一次(目前在 trim.py 里没有,需要 work-around)

---

## ✅ 完整修复套路(AI 必走)

### Step 1: 检测源
```bash
ffprobe -i input.mp4 2>&1 | grep "displaymatrix"
# 输出 "displaymatrix: rotation of -90.00 degrees" → 源是手机竖屏
# 无输出 → 源 metadata 缺失(可能是截屏/老安卓机/竖屏但没标)
```

### Step 2: v1 处理(per-video 处理)
```python
# 推荐方案:不加 -noautorotate,让 ffmpeg 自动应用 displaymatrix
# (比手动 transpose 准,因为不用猜方向)
cmd = [
    FFMPEG, '-y',
    '-i', INPUT,
    '-vf', 'trim=...,drawtext=...',  # 不加 transpose
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '20',
    '-c:a', 'aac',
    '-metadata', 'rotate=',           # 清 user metadata
    '-map_metadata', '-1',           # 清所有 user metadata(双保险)
    OUTPUT,
]
```

### Step 3: 三层保险 patch(每个 ffmpeg 工序结尾必走)
```python
from lib.video.patch_mp4_rotation import patch_mp4_rotation
from pathlib import Path
import shutil

# 1. patch tkhd matrix(binary 改 atom,稳)
patch_mp4_rotation(Path(OUTPUT), 0)

# 2. remux 清 user metadata
subprocess.run([
    FFMPEG, '-y', '-i', str(OUTPUT),
    '-map', '0', '-c', 'copy',
    '-map_metadata', '-1',
    '-metadata:s:v:0', 'rotate=0',
    '-movflags', '+faststart',
    str(OUTPUT) + '.tmp.mp4',
])
shutil.move(str(OUTPUT) + '.tmp.mp4', str(OUTPUT))
```

### Step 4: 拼接后再 patch
拼接(`trim.py concat` 或 `xfade.py`)会传播 side data,**拼接后必 patch 一次**。

---

## 🚨 暗坑:无 displaymatrix 但实际是竖屏

**症状**: 源是 1920x1080 + **无** displaymatrix metadata,但**视觉上是竖屏**(内容是站着的脚)。

**成因**:
- 老安卓机 / 截屏 / 某些录屏软件不写 displaymatrix
- 内容本身就是"竖屏",但编码器把 1920x1080 横屏数据存下来,不带 rotation 提示

**当前方案的盲点**:
- 让 ffmpeg 自动应用 displaymatrix → 没 metadata,不旋转 → 输出 1920x1080 横屏 ❌
- 用户看到"歪的"画面

**缓解(临时)**:
- ffmpeg probe 检测实际宽高比,如果 w=1920 h=1080 但没有 displaymatrix,**警告用户**"可能需要手动确认"
- 用户可手动用 `-vf "transpose=2"` 强制逆时针 90 度

**长期方案**(待实现):
- 用 AI 视觉模型检测源视频的"实际方向"(读第一帧分析)
- 或增加 `common.detect_video_orientation()` 函数

---

## 🪞 DAY9 真实案例:v2 源误判(AI 自作聪明的反例)

**事故**:v2 源 metadata `1080x1920` 没 displaymatrix。AI 抽帧 v2_src_21s.jpg 看视觉,看到"人脸在右",**误以为**这是"横屏内容"。

**AI 的"自作聪明"**:加了 `transpose=1+scale+pad`(letterbox),把 v2 弄成了"中间横屏 + 上下黑边"。

**结果**:用户看 v1 精加工,说"v2 段向右旋转了 90 度"。

**真相**:v2 实际是**正常 9:16 竖屏自拍**!人脸"在右"只是因为用户**侧身坐姿**(脸朝右看),不是视频被旋转。

**正确处理**:
- v2 源 1080x1920 没 displaymatrix → **直接信任 metadata**,不转置
- 只烧字幕 + 末尾裁剪就够了

**经验**(必读!):
- ❌ "AI 看到奇怪视觉就智能判断方向" → 容易把对的弄歪
- ✅ **先抽帧看实际视觉,确认是哪种情况再处理**
- ✅ vlog 自拍优先信任 metadata,只有明显是横屏内容(人脸侧躺 + 显示明显错位)才转置
- ✅ **让用户先确认"是这种视觉"再处理**,不要"自动化判断"

**修复步骤**(已验证):
```bash
# v2 直接烧字幕(不转置)
python scripts/asr/burn_subtitle.py -i v2.mp4 --srt v2.srt --output v2_sub.mp4 --font-size 32

# 末尾裁剪
ffmpeg -y -i v2_sub.mp4 -t 24.93 -c copy v2_trim.mp4
```

---

## 📋 AI 行为协议

### 必走(任何视频处理)
1. 处理前 `ffprobe -i input` 检查 displaymatrix
2. 处理后 `patch_mp4_rotation` 清 tkhd matrix
3. 拼接后再 patch 一次

### 推荐
- v1 处理:不加 `-noautorotate`,让 ffmpeg 自动应用
- ffmpeg 命令加 `-metadata rotate=`

### 必须问用户
- 源无 displaymatrix 但 w>h(可能是竖屏没标)→ 问用户"这是横屏还是竖屏没标?"

### 绝对不要
- ❌ 手动猜 transpose 方向(很可能猜错,见 DAY9 案例)
- ❌ 用 `-noautorotate` 但不 patch(会留 metadata)
- ❌ 拼接后不 patch(filter_complex 传播)

---

## 🔧 工具清单

| 工具 | 路径 | 作用 |
|---|---|---|
| `patch_mp4_rotation.py` | `lib/video/patch_mp4_rotation.py` | 直接改 mp4 tkhd atom 清 matrix |
| `ffprobe` | 系统 | 检测源 displaymatrix |
| `ffmpeg` | 系统 | 编码 + 可选 -noautorotate / -metadata rotate= |

**关键工具用法**:
```python
from lib.video.patch_mp4_rotation import patch_mp4_rotation
patch_mp4_rotation(Path("video.mp4"), 0)  # 0 = identity matrix(无旋转)
```

---

## 📅 案例索引

| 案例 | 日期 | 触发 |
|---|---|---|
| DAY9 减肥日记 | 2026-07-11 | 手机竖屏 v1 (1920x1080 + displaymatrix=-90) 处理后输出"向右旋转 90 度",用户反馈 |

---

## 🛠 架构改进建议(给开发者)

1. **`scripts/video/trim.py` 的 `concat` 内部加**:
   - `-metadata rotate=`
   - 调用 `patch_mp4_rotation` 在 output 后

2. **`common.py` 的 `run_ffmpeg` 默认加**:
   - `-noautorotate`(阻止自动应用)
   - `-metadata rotate=`(清 user metadata)

3. **新建 `scripts/_internal/strip_rotation.py`**:
   - 统一封装 patch_mp4_rotation + remux 清 user metadata
   - 所有 ffmpeg 结尾自动调用

4. **SKILL.md 主体的"⚠️ muted 拼接风险"旁边**:
   - 新加 "⚠️ rotation metadata 3 层坑" 章节
   - 引用本文件

---

**总结**: 3 层坑(displaymatrix 残留 / user metadata 残留 / filter_complex 传播)+ 1 个暗坑(无 metadata 竖屏)。
**必走**: 任何 ffmpeg 工序结尾 → patch_mp4_rotation + -metadata rotate=。
**别试**: 手动猜 transpose 方向(几乎肯定猜错)。
