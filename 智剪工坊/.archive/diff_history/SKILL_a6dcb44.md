---
name: 智剪工坊
description: >
  代码视频剪辑工作台,对标剪映(图形化)+ 扩展(AI 能力)。
  触发词:剪辑、剪切、拼接、转场、调色、慢动作、推镜头、字幕、封面、BGM、流水线、一条龙、智剪工坊、视频工坊、视频剪辑、代码剪辑。
  包含 11 个子技能(cut / xfade / effects / cinematic / color / text / audio / cover-ai / ai-features / batch / pipelines)
  + 1 个大流程(pipeline-vlog 7 步自动化)。
  底层:ffmpeg + MoviePy + OpenCV + matrix AI。
metadata: { "openclaw": { "emoji": "🎬", "requires": { "python": ">=3.10" } } }
---

# 智剪工坊 — 代码视频剪辑工作台

## 它是什么

代码驱动的"剪映代码版" + AI 扩展能力。底层用 **ffmpeg + MoviePy + OpenCV + matrix 工具**实现。

**核心特点(剪映做不到的):**
- 自然语言触发("加个淡入淡出转场")
- 批量自动化(100 个视频一次性处理)
- AI 能力(抠图、金句检测、节拍对位、AI 生图)

**中文别名:** 智剪工坊 / 视频工坊 / 视频剪辑 / 代码剪辑台
**英文 alias:** video-editor(历史命名,保留兼容)

## 什么时候触发它

用户在视频剪辑上下文中提到以下任一概念:
- **剪辑操作**:剪辑、剪切、切这段、保留 X 秒、拼接、转场、调色、慢动作、推镜头、字幕、封面、BGM
- **流程**:完整 vlog、一条龙、流水线、从素材到成片
- **格式诉求**:1080x1920、竖屏、横屏、烧字幕、嵌入字幕
- **技能名**:智剪工坊、视频工坊

## 子技能索引

| # | 子技能 | 触发词 | 文档 |
|---|---|---|---|
| 01 | **cut** | 剪切、切这段、保留 X 秒、从 A 到 B | [references/01-cutting.md](references/01-cutting.md) |
| 02 | **xfade** | 转场、淡入淡出、溶解、擦除、切换 | [references/02-transitions.md](references/02-transitions.md) |
| 03 | **slowmo** | 慢动作、慢放、0.5 倍速、插帧 | [references/03-effects.md](references/03-effects.md) |
| 04 | **zoompan** | 推镜头、zoom in、推到脸、放大 | [references/03-effects.md](references/03-effects.md) |
| 05 | **cinematic** | J-cut、L-cut、speed ramp、跳剪、变速 | [references/04-cinematic.md](references/04-cinematic.md) |
| 06 | **color-lut** | 调色、电影感、LUT、cinematic、调亮、调暗 | [references/05-color.md](references/05-color.md) |
| 07 | **text-anim** | 打字机、字幕动效、文字动画、烧字幕 | [references/06-text.md](references/06-text.md) |
| 08 | **bgm-loop** | 配 BGM、加音乐、循环背景音乐、混音 | [references/07-audio.md](references/07-audio.md) |
| 09 | **cover-ai** | 做封面、AI 生图、设计封面 | [references/08-cover.md](references/08-cover.md) |
| 10 | **ai-features** | AI 抠图、金句检测、节拍卡点、智能剪辑 | [references/09-ai-features.md](references/09-ai-features.md) |
| 11 | **batch** | 批量处理、批量转码、批量加转场 | [references/10-batch.md](references/10-batch.md) |
| 12 | **pipeline-vlog** | 完整 vlog、一条龙、7 步流水线 | [references/11-pipelines.md](references/11-pipelines.md) |

## 调用范式

### 单技能调用

```
用户: "把这两段视频加个 1 秒的淡入淡出转场"
  ↓
路由到: xfade
参数确认: 转场类型 / 时长 / offset
执行: scripts/xfade.py --a clip1.mp4 --b clip2.mp4 --type fade --duration 1
输出: joined_with_fade.mp4
```

### 大流程(流水线)

```
用户: "做一段完整 vlog,从素材到发布版"
  ↓
路由到: pipeline-vlog
自动串起:
  1. 4K → 1080p 降分辨率(若有)
  2. Whisper GPU 转录所有段
  3. 抽关键帧(每 15s 一帧)
  4. AI 分析生成剪辑建议
  5. 用户勾选保留秒数
  6. ffmpeg 拼接 + 烧字幕 + BGM 混合
  7. AI 生图封面 + 中文叠字
  8. 输出最终成片 + 字幕 SRT + 封面图
```

## 通用参数(所有子技能共享)

| 参数 | 默认值 | 说明 |
|---|---|---|
| `--resolution` | 1080x1920 | 输出分辨率(竖屏 vlog 默认) |
| `--fps` | 30 | 帧率(统一 30 避免拼接 bug) |
| `--vcodec` | libx264 | 视频编码(NVENC 不稳,默认 CPU) |
| `--crf` | 20 | 质量(0-51,越小越清) |
| `--acodec` | aac | 音频编码 |
| `--abitrate` | 128k | 音频码率 |
| `--format` | mp4 | 输出格式 |

## 关键技术教训(必看)

**Bug 1: NVENC 随机崩溃(Access Violation 0xC0000005)**
- 解决:全程用 libx264 CPU 编码

**Bug 2: 帧率不一致导致 8 小时视频 bug**
- 现象:不同原始视频 fps 不一致(60 vs 23.65),拼接后时长被错算
- 解决:剪切时强制 `fps=30` filter

**Bug 3: AI 生图对中文支持差**
- 解决:先生成视觉,后用 PIL 叠中文

## 工作流建议

| 类型 | 推荐工具 |
|---|---|
| 粗活(批量、自动化) | ffmpeg / 本 skill |
| 精活(单条调色、特效) | 剪映手动补刀 |
| AI 能力(剪映做不到) | 本 skill |

## 目录结构

```
video-editor/
├── SKILL.md                (本文件 - 主入口)
├── README.md               (架构说明)
├── references/             (子技能文档)
│   ├── 01-cutting.md
│   ├── 02-transitions.md
│   ├── 03-effects.md
│   ├── 04-cinematic.md
│   ├── 05-color.md
│   ├── 06-text.md
│   ├── 07-audio.md
│   ├── 08-cover.md
│   ├── 09-ai-features.md
│   ├── 10-batch.md
│   └── 11-pipelines.md
├── scripts/                (Python + ffmpeg 包装脚本)
└── assets/                 (LUT、字体、测试视频)
```

## 当前状态(2026-07-03)

- ✅ **阶段 1 骨架完成**:目录 + SKILL.md + 11 个子技能占位 md
- 🚧 **阶段 2 进行中**:核心 4 个子技能(cut / xfade / bgm-loop / cover-ai)落地中
- ⏳ **阶段 3 待办**:剩余 6 个子技能 + 大流程 pipeline-vlog

## 相关工具链

- **ffmpeg**: `D:\0Tools\Python313\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg.exe`
- **Python 库**: faster-whisper, faster-whisper, Pillow, moviepy(可选), opencv-python(可选)
- **matrix MCP**: 音乐生成 + 图像生成