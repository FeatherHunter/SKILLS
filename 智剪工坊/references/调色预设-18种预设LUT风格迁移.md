# 调色预设 - 18种预设LUT风格迁移

> **对应脚本**: `scripts/video_color.py` + `scripts/video_style.py` + `scripts/video_hdr.py`
> **触发词**: "调色"、"电影感"、"LUT"、"cinematic"、"调亮"、"调暗"、"对比度"、"饱和度"、"色温"、"teal & orange"
> **实测状态**: ✅ 验证通过

---

## 1. 调用范式

### 场景 1

```bash
# 调色(18 预设)
python scripts/video_color.py --input v.mp4 --preset cinematic --output out.mp4

# 风格迁移
python scripts/video_style.py --input v.mp4 --reference ref.jpg --output out.mp4

# HDR 导入/导出
python scripts/video_hdr.py --input hdr.mp4 --output sdr.mp4 --direction to_sdr
```

### 场景 2

```bash
# 调亮
ffmpeg -i in.mp4 -vf "eq=brightness=0.1" out.mp4

# 调暗(电影感)
ffmpeg -i in.mp4 -vf "eq=brightness=-0.05:contrast=1.1:saturation=0.9" out.mp4

# 提高对比度
ffmpeg -i in.mp4 -vf "curves=preset=contrast" out.mp4

# 内置 curves preset
# darker / contrast / cross_process / warmer / cooler / saturated
# faded / film_contrast / medium_contrast / punchy
```

### 场景 3

```bash
ffmpeg -i in.mp4 -vf "lut3d=file=cinematic.cube" out.mp4
```

## 2. 参数

| 参数 | 短选项 | 默认值 | 说明 |
|---|---|---|---|
| `--input` | `-i` | (必填) | 输入视频/音频/图片 |
| `--output` | `-o` | (必填) | 输出路径 |

## 3. 常见错误 / 限制

1. **LUT 是参考** —— 同一 LUT 对不同视频效果差异大,可能需要微调
2. **顺序很关键** —— 多个调色 filter 叠加顺序会影响最终效果
3. **资源文件** —— `assets/luts/` 下需要提前放好 .cube 文件

## 4. 相关参考

- **SKILL.md §14 子技能索引**：本子技能的路由表
- **scripts/README.md**：scripts/ 目录命名规范（`<维度>_<动作>.py`）
- `.archive/CHANGELOG.md`：本子技能历史变更

---

<details>
<summary>📋 原文存档（v0.5 旧版，仅供 git history 追溯）</summary>

# 05 - color (调色 / LUT) — v0.5 已实现

> **对应脚本:** `scripts/video_color.py` + `scripts/video_style.py` + `scripts/video_hdr.py`(3 个)
> **实测状态:** ✅ 验证通过
> **注意:** ffmpeg 7.1 不支持 `curves=preset=`,已改用 `colorbalance` + `eq` filter(v0.5 修 bug 9)

```bash
# 调色(18 预设)
python scripts/video_color.py --input v.mp4 --preset cinematic --output out.mp4

# 风格迁移
python scripts/video_style.py --input v.mp4 --reference ref.jpg --output out.mp4

# HDR 导入/导出
python scripts/video_hdr.py --input hdr.mp4 --output sdr.mp4 --direction to_sdr
```

---

## 触发词

"调色"、"电影感"、"LUT"、"cinematic"、"调亮"、"调暗"、"对比度"、"饱和度"、"色温"、"teal & orange"

## 输入 / 输出

- **输入**: 单个视频
- **输出**: 调色后的视频

## A. 简单调色(curves / eq)

```bash
# 调亮
ffmpeg -i in.mp4 -vf "eq=brightness=0.1" out.mp4

# 调暗(电影感)
ffmpeg -i in.mp4 -vf "eq=brightness=-0.05:contrast=1.1:saturation=0.9" out.mp4

# 提高对比度
ffmpeg -i in.mp4 -vf "curves=preset=contrast" out.mp4

# 内置 curves preset
# darker / contrast / cross_process / warmer / cooler / saturated
# faded / film_contrast / medium_contrast / punchy
```

### 常用参数

```
brightness: -1.0 ~ 1.0(默认 0)
contrast: 0.0 ~ 2.0(默认 1.0)
saturation: 0.0 ~ 3.0(默认 1.0)
gamma: 0.0 ~ 10.0(默认 1.0)
hue: -180 ~ 180(默认 0)
```

## B. LUT 调色(电影级)

LUT(Look-Up Table)是电影工业标准的调色预设,效果比 curves 强大得多。

```bash
ffmpeg -i in.mp4 -vf "lut3d=file=cinematic.cube" out.mp4
```

**常用 LUT 来源(免费):**
- 小红书 / B 站搜 "LUT 调色预设"
- 知名 LUT: Kodak 2383, Fuji F125, Teal & Orange
- 自制 LUT:用 DaVinci Resolve / Premiere 调色后导出 .cube 文件

**本 skill 资源位置:**
- `assets/luts/cinematic.cube`
- `assets/luts/teal_orange.cube`
- `assets/luts/vintage.cube`

## C. 调色流程(标准)

```
1. 校准(校准白平衡)
2. 基础调色(曝光、对比度、白平衡)
3. 创意调色(LUT / curves / 风格化)
4. 局部调色(vignette、HSL 调整)
```

## D. 风格化滤镜

```bash
# 复古 / 老电影风
ffmpeg -i in.mp4 -vf "curves=preset=vintage,vignette" out.mp4

# 黑白
ffmpeg -i in.mp4 -vf "hue=s=0" out.mp4

# 暗角(vignette)
ffmpeg -i in.mp4 -vf "vignette=PI/4" out.mp4

# 色调分离(冷色 / 暖色)
ffmpeg -i in.mp4 -vf "colorbalance=rs=0.1:bs=-0.1" out.mp4  # 暖色
ffmpeg -i in.mp4 -vf "colorbalance=rs=-0.1:bs=0.1" out.mp4  # 冷色
```

## E. AI 自动调色(进阶)

剪映做不到的:
- 场景识别 → 自动应用不同 LUT
- 风格迁移(把视频风格转成另一参考视频)

```python
# OpenCV + LUT 应用示例(待写进 scripts/)
import cv2
import numpy as np

def apply_lut(frame, lut):
    # lut: shape (256, 3) 的查表
    return cv2.LUT(frame, lut)
```

## 调用示例

```
用户: "调暗一点,加点电影感"
→ color --preset cinematic --brightness -0.05 --contrast 1.1
```

```
用户: "用 teal & orange LUT"
→ color --lut assets/luts/teal_orange.cube
```

## 限制 / 注意

1. **LUT 是参考** —— 同一 LUT 对不同视频效果差异大,可能需要微调
2. **顺序很关键** —— 多个调色 filter 叠加顺序会影响最终效果
3. **资源文件** —— `assets/luts/` 下需要提前放好 .cube 文件

## LUT 文件下载

```bash
# 常见免费 LUT 包下载(脚本预留)
# 1. https://fixthephoto.com/free-luts.html
# 2. https://www.rocketstock.com/free-luts-for-premiere-pro/
# 3. https://luts.io/
```

下载后放入 `assets/luts/` 即可调用。

</details>
