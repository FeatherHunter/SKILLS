# 视频底层 lib — 字幕 / 转场 / 调色 / 速度 / 缩放 / 水印

> **对应 lib**：`lib/ffmpeg/video/*.py`（6 个文件，21 个公开函数）
> **对应触发词**：视频滤镜 / 转场 / 调色 / 字幕 / 烧字幕 / 水印 / 缩放 / 旋转 / 翻转 / 字母盒 / 变速 / 倒放 / 冻结帧 / 抽帧
> **v1.6 新增链路** | 上层脚本通过 lib 调用，不直接拼 ffmpeg

---

## 1. 链路架构

```
视频处理任务
    ↓
┌─────────────────────────────────────────┐
│  scripts/*.py（用户可见 CLI）         │
│   asr/burn_subtitle  → 烧字幕          │
│   （未来: video_xfade.py 等）          │
└─────────────────────────────────────────┘
    ↓ 调
┌─────────────────────────────────────────┐
│ lib/ffmpeg/video/*.py（底层 lib）     │
│   subtitle / transition / color        │
│   timing / transform / watermark       │
└─────────────────────────────────────────┘
    ↓ 调
ffmpeg subprocess.run (filters / xfade / overlay / drawtext ...)
```

**v1.6 之前**：scripts/asr/burn_subtitle.py 直接拼 ffmpeg -vf subtitles=...
**v1.6 之后**：scripts/asr/burn_subtitle.py 调 lib，lib 调 ffmpeg

---

## 2. 21 个公开函数（按 6 个 lib 文件分类）

### 2.1 `subtitle.py` — 字幕烧录（3 函数）

| 函数 | 用途 | 核心 ffmpeg 滤镜 |
|---|---|---|
| `burn_subtitle(video, srt, output, font_size=22, font="Microsoft YaHei")` | 烧录 SRT | `subtitles` |
| `burn_ass_subtitle(video, ass, output)` | 烧录 ASS 高级字幕 | `ass` |
| `draw_text(video, output, text, x, y, fontsize, ...)` | 视频叠加文字 | `drawtext` |

**典型用法**：
```python
from lib.ffmpeg.video.subtitle import burn_subtitle, burn_ass_subtitle, draw_text

# 1. 烧 SRT 字幕
burn_subtitle("video.mp4", "subtitles.srt", "out.mp4", font_size=24)

# 2. 烧 ASS 字幕（带样式）
burn_ass_subtitle("video.mp4", "styled.ass", "out.mp4")

# 3. 视频叠加文字（开场/水印/标注）
draw_text("video.mp4", "out.mp4", "Hello World",
          x=100, y=100, fontsize=36, fontcolor="white",
          start_time=0, duration=3)
```

### 2.2 `transition.py` — 转场（2 函数 + 41 种类型）

| 函数 | 用途 |
|---|---|
| `xfade_transition(video_a, video_b, output, transition="fade", duration=0.5)` | 两个视频间加转场 |
| `concat_simple(video_paths, output)` | 简单拼接（concat demuxer，无转场） |

**41 种 xfade 类型**（覆盖 SKILL.md 声明的 9 种 + 32 种扩展）：

| 类别 | 名称 |
|---|---|
| 基础 | fade / wipeleft / wiperight / wipeup / wipedown |
| 滑动 | slideleft / slideright / slideup / slidedown / smoothleft / smoothright / smoothup / smoothdown |
| 遮罩 | circlecrop / rectcrop / circleopen / circleclose / vertopen / vertclose / horzopen / horzclose |
| 擦除 | wipetl / wipetr / wipebl / wipebr |
| 切片 | hlslice / hrslice / vuslice / vdslice |
| 形状 | diagtl / diagtr / diagbl / diagbr / radial / distance |
| 色彩 | fadeblack / fadewhite / fadegrays |
| 模糊 | hblur |
| 像素 | pixelize |
| 溶解 | dissolve |

**典型用法**：
```python
from lib.ffmpeg.video.transition import xfade_transition, concat_simple

# 1. 淡入淡出（最常用）
xfade_transition("a.mp4", "b.mp4", "out.mp4", transition="fade", duration=0.5)

# 2. 圆形展开
xfade_transition("a.mp4", "b.mp4", "out.mp4", transition="circleopen", duration=0.8)

# 3. 简单拼接（无转场）
concat_simple(["a.mp4", "b.mp4", "c.mp4"], "merged.mp4")
```

### 2.3 `color.py` — 调色（6 函数）

| 函数 | 用途 | 核心滤镜 |
|---|---|---|
| `adjust_brightness_contrast(video, output, brightness=0, contrast=1.0, saturation=1.0, gamma=1.0)` | 亮度/对比度/饱和度/伽马 | `eq` |
| `color_balance(video, output, rs/gs/bs, rm/gm/bm, rh/gh/bh)` | 颜色平衡（阴影/中调/高光）| `colorbalance` |
| `hue_shift(video, output, hue=0, saturation=1.0)` | 色相/饱和度 | `hue` |
| `apply_lut(video, lut_file, output)` | 应用 3D LUT 文件（.cube / .3dl）| `lut3d` |
| `vibrance(video, output, intensity=0.5)` | 自然饱和度 | `vibrance` |
| `curves_adjust(video, output, preset="increase_contrast")` | 预设曲线（多 preset）| `curves` |

**典型用法**：
```python
from lib.ffmpeg.video.color import (
    adjust_brightness_contrast, hue_shift, apply_lut, vibrance
)

# 1. 调亮 + 提高对比度
adjust_brightness_contrast("v.mp4", "out.mp4",
                            brightness=0.05, contrast=1.15, saturation=1.1)

# 2. 色相偏移（90 度）
hue_shift("v.mp4", "out.mp4", hue=90, saturation=0.8)

# 3. 加 LUT 电影感
apply_lut("v.mp4", "cinematic.cube", "out.mp4")

# 4. 自然饱和度
vibrance("v.mp4", "out.mp4", intensity=0.3)
```

### 2.4 `timing.py` — 速度/时间（5 函数）

| 函数 | 用途 | 核心滤镜 |
|---|---|---|
| `change_speed(video, output, factor=1.0)` | 变速（setpts + atempo）| `setpts` |
| `trim_clip(video, output, start, duration)` | 截取片段 | `-ss / -t` |
| `reverse_video(video, output)` | 倒放 | `reverse` |
| `freeze_frame(video, output, time=0, freeze_duration=2)` | 冻结帧 | `freeze` |
| `set_fps(video, output, fps=30)` | 改帧率 | `fps` |

**典型用法**：
```python
from lib.ffmpeg.video.timing import change_speed, trim_clip, reverse_video

# 1. 2 倍速（推荐范围 0.25-4.0）
change_speed("v.mp4", "out.mp4", factor=2.0)

# 2. 半速慢动作
change_speed("v.mp4", "out.mp4", factor=0.5)

# 3. 截取片段
trim_clip("v.mp4", "out.mp4", start=10, duration=5)

# 4. 倒放
reverse_video("v.mp4", "out.mp4")
```

### 2.5 `transform.py` — 缩放/裁剪/旋转/翻转/黑边（6 函数）

| 函数 | 用途 | 核心滤镜 |
|---|---|---|
| `scale_video(video, output, width, height, keep_aspect=True)` | 缩放（保持比例 → 加黑边）| `scale` |
| `crop_video(video, output, x, y, width, height)` | 裁剪 | `crop` |
| `rotate_video(video, output, degrees=90)` | 旋转（90 / 180 / 270）| `transpose` |
| `flip_video(video, output, mode="h")` | 翻转（h / v / hv）| `hflip / vflip` |
| `pad_video(video, output, top, bottom, left, right, color="black")` | 加指定 padding | `pad` |
| `letterbox(video, output, target_width, target_height, color="black")` | 字母盒（目标尺寸）| `scale + pad` |

**典型用法**：
```python
from lib.ffmpeg.video.transform import (
    scale_video, crop_video, rotate_video, letterbox
)

# 1. 缩放 → 1920x1080（保持比例）
scale_video("v.mp4", "out.mp4", 1920, 1080)

# 2. 裁剪 (100,100,500,500)
crop_video("v.mp4", "out.mp4", x=100, y=100, width=500, height=500)

# 3. 旋转 90 度
rotate_video("v.mp4", "out.mp4", degrees=90)

# 4. 竖屏视频 → 9:16 标准（1080x1920，加黑边）
letterbox("v_vertical.mp4", "out.mp4", 1080, 1920)
```

### 2.6 `watermark.py` — 水印（2 函数）

| 函数 | 用途 |
|---|---|
| `add_watermark(video, logo, output, position="topright", opacity=0.7)` | 加 logo 水印（overlay）|
| `add_text_watermark(video, output, text, position="bottomright", ...)` | 加文字水印（drawtext）|

**5 种位置**：topleft / topright / bottomleft / bottomright / center

**典型用法**：
```python
from lib.ffmpeg.video.watermark import add_watermark, add_text_watermark

# 1. 加 logo 水印（右上，半透明）
add_watermark("v.mp4", "logo.png", "out.mp4",
              position="topright", opacity=0.7)

# 2. 加版权文字水印
add_text_watermark("v.mp4", "out.mp4", "© 2026 帅猎羽",
                   position="bottomright",
                   fontsize=20, fontcolor="white",
                   opacity=0.6)
```

---

## 3. 调用范式

### 3.1 上层 CLI → lib

```bash
# 烧字幕（v1.6 通过 lib）
python scripts/asr/burn_subtitle.py \
  --video in.mp4 --srt sub.srt --output out.mp4 --font-size 24
```

```python
# scripts/asr/burn_subtitle.py 内部
from lib.ffmpeg.video.subtitle import burn_subtitle as _lib_burn

def burn_subtitle_video(video, srt, output, font_size=22):
    _lib_burn(video, srt, output, font_size=font_size)
```

### 3.2 AI 在编排时直接调 lib

```python
# 阶段 2/3 可直接 import 调用
from lib.ffmpeg.video.transition import xfade_transition
from lib.ffmpeg.video.color import adjust_brightness_contrast
from lib.ffmpeg.video.transform import letterbox

xfade_transition("a.mp4", "b.mp4", "out.mp4", transition="fade")
adjust_brightness_contrast("out.mp4", "final.mp4", brightness=0.05)
```

### 3.3 不下沉到 lib 的场景（业务链 4 步合成）

```python
# 例：烧字幕时还要同时改分辨率 + 加水印
# 不下沉 —— 三个独立操作 + 多次 ffmpeg 调用
# 业务层用 filter_complex 一次完成 → 更快
```

---

## 4. 红线检查清单

修改 video lib 时，AI 必须主动同步：

1. **lib/ffmpeg/video/*.py 新增函数** → 同步本文件 + SKILL.md
2. **SKILL.md 触发词变更** → 同步本文件 + scripts/*.py
3. **scripts/asr/burn_subtitle.py 变更** → 同步本文件 + SKILL.md

**违规红线**：
- 上层脚本重新直接拼 ffmpeg 命令 → 视为脱离分层架构
- lib 函数不返回 `(success: bool, output_path)` → 破坏调用契约
- 公开函数在 SKILL.md 没声明 → AI 调度时找不到

---

## 5. 错误处理

所有 lib 函数遵循统一契约：

```python
def some_func(...) -> tuple[bool, str]:
    """Returns (success: bool, output_path_or_error_message)"""
```

调用方：
```python
ok, out = lib_func(...)
if not ok:
    raise RuntimeError(f"video lib 失败: {out}")
```

底层的 `run_ffmpeg` 自动捕获 ffmpeg 非 0 exit code，错误流通过 `safe_run` 包装后抛出。

---

## 6. 版本

- **v1.6**（2026-07-09）：首版本，21 函数，6 文件，覆盖 ffmpeg 视频滤镜全集
