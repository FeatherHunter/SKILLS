---
name: 智剪工坊
description: >
  代码视频剪辑工作台,对标剪映(图形化)+ 扩展(AI 能力)。
  触发词:剪辑、剪切、拼接、转场、调色、慢动作、推镜头、字幕、封面、BGM、流水线、一条龙、智剪工坊、视频工坊、代码剪辑、
  美颜、磨皮、瘦脸、大眼、beauty、
  去水词、填充词、filler、嗯啊、
  改词、改写、翻唱、TTS、配音、换声、改写文案、
  文字成片、文生视频、text-to-video、
  数字人、虚拟人、digital human。
  包含 30 个原子脚本 + 主体流程(粗加工 5 步 + 模板工作流)。
  底层:ffmpeg + OpenCV + mediapipe + mmx matrix MCP(免费 AI 能力)。
metadata: { "openclaw": { "emoji": "🎬", "requires": { "python": ">=3.10" } } }
---

# 智剪工坊 — 代码视频剪辑工作台

## 文件地图（v0.7）

**接手这个 skill 第一件事**：读这张表。每个文件**作用**和**何时读**：

| 文件 | 作用 | 何时读 |
|---|---|---|
| **SKILL.md** | 工具契约（你正在读） | **必读第一份** |
| 架构.md | 完整设计 + §8 决策落地位置 | 看完 SKILL 还想要上下文 |
| HANDOFF.md | Session 交接（v0.7 增量上下文在最前） | 接手 session 时 |
| CHANGELOG.md | 版本历史 | 查历史决策 |
| README.md | 产品级介绍（**v0.5 旧版，待更新**） | 用户/产品视角 |
| 模板/<name>.yaml | 类别化工作流 | 加载某个模板时 |
| scripts/30 个 .py | 原子工具（cut/xfade/bgm_loop/...） | 单独调用某个功能 |
| lib/common.py | ffmpeg 包装 + 错误 + 日志 | 共享逻辑 |
| lib/asr.py | faster-whisper 包装 | 粗加工 Step 4 |
| lib/modify.py | 改素材命令菜单 + 决策报告 | AI 改素材时 |
| executor.py | 5 原子 + run_coarse 编排 | AI 写新执行逻辑时 |
| intent.html | 唯一前端：填表 → intent.json | 用户新建项目时 |

**v0.7 当前状态**：
- ✅ 文档：SKILL.md / 架构.md / 模板/ / HANDOFF.md / CHANGELOG.md
- ✅ 代码：executor.py 5 原子 + lib/asr.py + lib/modify.py
- ⏸️ docs/*.md 4 个 + README.md 仍标 v0.5（**待下个 PR 同步**）
- ⏸️ 模板库只有「健身vlog.yaml」一个
- ⏸️ lib/modify.py 序列操作是 stub

**v0.7 关键设计**（详见 §主体流程）：
- 粗加工 5 步：解析自检 / 单视频处理 / sequence 拼接 / ASR 文字稿 / 决策报告
- 模板 = 工作流脚本（AI 引导用户做决策），不是 config
- 粗加工失败不退出主体，记入决策.md
- 工作区约定：`00_智剪/粗加工/`（单视频/组合/文字稿/中间产物/决策.md）

---

## 它是什么

代码驱动的"剪映代码版" + AI 扩展能力。底层用 **ffmpeg + OpenCV + mediapipe + mmx matrix MCP(免费 AI)** 实现。

**核心特点(剪映做不到的):**
- 自然语言触发("美颜一下我的脸" / "去掉'嗯啊'水词")
- 批量自动化(100 个视频一次性处理)
- AI 能力(美颜/去水词/改词/文字成片/数字人) — 全部走 mmx,免 API key
- Word-level 时间戳(精准切单字水词)

**当前版本:** v0.7(2026-07-04)

## 什么时候触发它

用户在视频剪辑/AI 处理上下文中提到以下任一概念:

### 基础剪辑
- **剪辑操作**:剪辑、剪切、切这段、保留 X 秒、拼接、转场、调色、慢动作、推镜头、字幕、封面、BGM
- **格式诉求**:1080x1920、竖屏、横屏、烧字幕、嵌入字幕
- **技能名**:智剪工坊、视频工坊

### AI 增强(核心差异)
- **美颜**:磨皮、瘦脸、大眼、美白、beauty
- **去水词**:填充词、filler、嗯啊、口头禅、那个、就是说
- **改词翻唱**:TTS、配音、换声、改写文案、改词、翻唱、AI 改词
- **文字成片**:文生视频、text-to-video、AI 生成视频
- **数字人**:虚拟人、digital human、AI 讲解

## 14 个子技能索引

| # | 子技能 | 触发词 | 文档 | 脚本 |
|---|---|---|---|---|
| 01 | **cut** | 剪切、切这段、保留 X 秒、从 A 到 B | [references/01-cutting.md](references/01-cutting.md) | `scripts/cut.py` |
| 02 | **xfade** | 转场、淡入淡出、溶解、擦除、切换 | [references/02-transitions.md](references/02-transitions.md) | `scripts/xfade.py` |
| 03 | **effects** | 慢动作、推镜头、zoom in、keyframe | [references/03-effects.md](references/03-effects.md) | `scripts/fx.py`, `scripts/keyframe.py` |
| 04 | **cinematic** | J-cut、L-cut、speed ramp、跳剪、变速、倒放 | [references/04-cinematic.md](references/04-cinematic.md) | `scripts/speed.py`, `scripts/reverse.py`, `scripts/multicam.py` |
| 05 | **color** | 调色、LUT、cinematic、调亮、调暗、风格化、HDR | [references/05-color.md](references/05-color.md) | `scripts/color_style.py`, `scripts/style_transfer.py`, `scripts/hdr_io.py` |
| 06 | **text** | 烧字幕、字幕动效、文字动画、自动字幕、字幕识别、变声 | [references/06-text.md](references/06-text.md) | `scripts/auto_subtitle.py`, `scripts/voice_change.py`, `scripts/translate.py` |
| 07 | **audio** | 加音乐、循环背景音乐、混音、BGM、节拍卡点 | [references/07-audio.md](references/07-audio.md) | `scripts/bgm_loop.py`, `scripts/beat_sync.py` |
| 08 | **cover** | AI 生图封面、设计封面、中文叠字 | [references/08-cover.md](references/08-cover.md) | `scripts/cover_ai.py` |
| 09 | **ai-features** | AI 抠图、金句检测、场景检测、蒙版、画中画、重新构图、**去水词** | [references/09-ai-features.md](references/09-ai-features.md) | `scripts/cutout.py`, `scripts/quotes.py`, `scripts/scene_detect.py`, `scripts/mask.py`, `scripts/overlay.py`, `scripts/reframe.py`, `scripts/remove_fillers.py` |
| 10 | **batch** | 批量处理、批量加转场、批量转码、批量封面、进度条 | [references/10-batch.md](references/10-batch.md) | `scripts/batch.py` |
| 11 | **pipelines** | 完整 vlog、流水线、一条龙、7 步流程 | [references/11-pipelines.md](references/11-pipelines.md) | `scripts/pipeline_vlog.py` |
| 12 | **🆕 beauty** | 美颜、磨皮、瘦脸、大眼、美白、人脸美化、beauty | [references/12-beauty.md](references/12-beauty.md) | `scripts/beauty.py` |
| 13 | **🆕 rewrite-audio** | 去水词后改写、TTS 配音、换声、agent 改文案、翻唱 | [references/13-rewrite-audio.md](references/13-rewrite-audio.md) | `scripts/rewrite_audio.py` |
| 14 | **🆕 text-to-video** | 文生视频、文字成片、AI 生成视频片段 | [references/14-text-to-video.md](references/14-text-to-video.md) | `scripts/text_to_video.py` |
| 15 | **🆕 digital-human** | 数字人、虚拟人、AI 讲解、头像说话 | [references/15-digital-human.md](references/15-digital-human.md) | `scripts/digital_human.py` |
| 16 | **🆕 edit** | 去头去尾 / 调音量 / 静音 / 黑边 / 缩放 / 裁剪 / 旋转 / 翻转 / 提音 / 淡入淡出 / 水印 / 多分辨率 / GIF / 缩略图 | [references/16-edit.md](references/16-edit.md) | `scripts/edit.py`(14 子命令) |

> 实际有 30 个 Python 脚本(部分子技能含多个脚本),详见 `scripts/` 目录。

## 调用范式

### 单技能调用

```
用户: "把这两段视频加个 1 秒的淡入淡出转场"
  ↓
路由到: xfade
参数确认: 转场类型 / 时长 / offset
执行: scripts/xfade.py --a clip1.mp4 --b clip2.mp4 --type fade --duration 1 --out joined.mp4
输出: joined_with_fade.mp4
```

### AI 增强(agent-driven 流程)

```
用户: "去掉我 vlog 里的'嗯啊那个'"
  ↓
路由到: remove_fillers (LLM 判断在 Mavis agent 里)
Step 1: scripts/remove_fillers.py transcribe --input vlog.mp4 --srt vlog.srt
Step 2: (Mavis 读 SRT + words.json) 判 10 个水词,返回词索引
Step 3: scripts/remove_fillers.py cut --input vlog.mp4 --srt vlog.srt --output clean.mp4 --remove-words "1,3,11,12,19,28,37,38,39,45"
输出: 干净视频(20s → 16.7s,省 3.3s)
```

### 大流程(流水线)

```
用户: "做一段完整 vlog,从素材到发布版"
  ↓
路由到: pipeline-vlog
自动串起:
  1. 4K → 1080p 降分辨率(若有)
  2. Whisper 转录所有段
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
| `--input` | (必填) | 输入视频或图片 |
| `--output` | (必填) | 输出路径 |
| `--resolution` | 1080:1920 | 输出分辨率(竖屏 vlog) |
| `--fps` | 30 | 帧率(强制统一避免 8 小时视频 bug) |
| `--vcodec` | libx264 | 视频编码(避开 NVENC 崩溃) |
| `--crf` | 20 | 质量(0-51,越小越清) |
| `--acodec` | aac | 音频编码 |
| `--abitrate` | 128k | 音频码率 |
| `--verbose` | False | 显示 debug 日志(写到 `~/.zhijian/logs/`) |

> 已知 bug 排查:见 [docs/FAQ.md](docs/FAQ.md)(高频 Q&A)和 [HANDOFF.md](HANDOFF.md)(完整开发历史)。子技能内部 bug 见 `references/05-color.md` / `09-ai-features.md` 等。

## 工作流建议

| 类型 | 推荐工具 |
|---|---|
| 粗活(批量、自动化) | 智剪工坊 batch.py |
| 精活(单条调色、特效) | 智剪工坊 color_style + ffmpeg |
| AI 能力(美颜/去水词/改词/数字人) | 智剪工坊(走 mmx 免 API key) |
| 完整 vlog 一条龙 | pipeline_vlog.py run |

## 目录结构(当前 v0.5)

```
智剪工坊/
├── SKILL.md                # 本文件(Mavis 入口)
├── README.md               # 产品级 README
├── HANDOFF.md              # Session 交接文档
├── CHANGELOG.md            # 版本变更日志
├── requirements.txt         # 依赖清单
├── setup.bat / setup.sh    # 一键安装(Win/Mac/Linux)
├── verify.py               # 环境验证(5 秒快检 / 2 分钟全检)
├── config.json             # ffmpeg 路径 + 平台信息
│
├── lib/
│   ├── common.py           # 公共库(ffmpeg + 错误处理 + 日志 + 进度条)
│   └── llm_client.py       # LLM 客户端封装(备用)
│
├── scripts/                # 29 个原子子技能
│   ├── cut.py / xfade.py / bgm_loop.py / cover_ai.py / pipeline_vlog.py
│   ├── reverse.py / speed.py / overlay.py / mask.py
│   ├── voice_change.py / color_style.py / beat_sync.py
│   ├── auto_subtitle.py / scene_detect.py / fx.py
│   ├── hdr_io.py / reframe.py / keyframe.py / multicam.py / style_transfer.py
│   ├── batch.py / quotes.py / cutout.py
│   ├── text_to_video.py / digital_human.py / translate.py
│   ├── beauty.py                ← v0.3 美颜 L2
│   ├── remove_fillers.py        ← v0.4 去水词 L2(word-level)
│   └── rewrite_audio.py         ← v0.4 改词翻唱 L2
│
├── references/             # 15 个子技能详细文档
│   ├── 01-cutting.md ... 11-pipelines.md (v0.1 老分类)
│   ├── 12-beauty.md              ← v0.3
│   ├── 13-rewrite-audio.md       ← v0.4
│   ├── 14-text-to-video.md       ← v0.5
│   └── 15-digital-human.md       ← v0.5
│
├── docs/                   # 产品文档
│   ├── GETTING_STARTED.md
│   ├── FEATURE_COMPARISON.md    # vs 剪映/Pr/Resolve/FCP 对比
│   ├── FAQ.md
│   └── VS_JIANYING.md
│
├── assets/                 # 资源
│   ├── fonts/ luts/ templates/ test_videos/
│   ├── output/ cache/
│   └── face_landmarker.task   # mediapipe 模型(自动下载)
│
└── ~/.zhijian/             # 用户级数据
    └── logs/               # 日志(滚动 10MB × 3)
        └── zhijian-YYYYMMDD.log
```

## 当前状态

| 维度 | 进度 | 备注 |
|---|---|---|
| 架构设计 | ✅ 100% | 16 子技能 + 1 大流程 + vlog 端到端 |
| SKILL.md | ✅ 100% | YAML frontmatter, 16 子技能索引 + vlog 流程 |
| References(子技能) | ✅ 100% | 16 个 .md,详细接口 + 命令 |
| 代码框架 | ✅ 100% | 30 个 .py 脚本,无 TODO/占位 |
| 公共库 | ✅ 100% | lib/common.py(读 config.json + 友好错误 + 进度条 + 文件日志) |
| 产品 README | ✅ 100% | 3 分钟快速开始 + 30 脚本速查 |
| 安装脚本 | ✅ 100% | setup.bat(Windows)+ setup.sh(Mac/Linux) |
| 验证脚本 | ✅ 100% | verify.py(5 秒快检 + 30 脚本 + 6 冒烟) |
| 依赖 | ✅ 100% | requirements.txt 9 个实依赖全开 |
| 验证(实测) | ✅ 100% | 30/30 import + 6/6 冒烟 + 17/17 edit 测过 |
| 跨平台 | ⚠️ 50% | setup.sh 写好但只测 Windows |
| 错误处理 | ✅ 100% | safe_run 增强 5 种错误类型(JSON/Timeout/OS/...) |
| 日志系统 | ✅ 100% | log_progress + 文件日志 + safe_batch |
| 原子操作覆盖 | ✅ 100% | 14 个 edit 子命令补全剪映 P0+P1 基础操作 |
| 单元测试 | ❌ 0% | 推迟(用户确认) |
| AI 视频实测 | ❌ 0% | mmx 配额 3/天,等真 vlog 时测 |
| 模板/<name>.yaml | ⚠️ 草稿 | 见[架构.md §8 D](架构.md) |
| executor.py 粗加工 | ❌ 未动 | 见[架构.md §8 C](架构.md) |

## 相关工具链

- **ffmpeg**:`D:\0Tools\Python313\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg.exe` v7.1
- **Python** 3.13(用户级)
- **mediapipe** 0.10.35(task-based API)
- **mmx matrix MCP**:TTS(327 声音)/ 视频生成 / 数字人(通过 `mavis mcp call matrix` 调用)
- **Whisper**:faster-whisper small(默认)/ 显存允许可换 medium/large-v3

## License

MIT

---

## AI 协作协议 (v0.6 新增)

> 这部分定义了 AI 在拿到 `intent.json` 后**如何理解与执行**。vlog 创作者填表后，AI 按本节规则解析。

### 时间字段解析规则 (pin-range / cut-middle / insert-image)

用户时间字段可能是**多种格式**。AI 必须**全兼容**，按以下顺序尝试：

| 写法 | 解析 | 示例 |
|---|---|---|
| `M:SS` 或 `MM:SS` | 标准格式 | `"1:30"` → 90s |
| `H:MM:SS` | 含小时 | `"1:30:00"` → 5400s |
| 纯数字（无单位） | **默认秒** | `"15"` → 15s |
| `"15秒"` / `"15s"` | 秒（中文/英文单位） | `"15秒"` → 15s |
| `"15分钟"` / `"15min"` | 分钟转秒 | `"15分钟"` → 900s |
| `"1分30秒"` | 复合 | `"1分30秒"` → 90s |
| 完全无法解析 | **必须问用户** | 不要瞎猜 |

### 序列（sequences）是**部分约束**，不是全连接

- 视频序列定义**部分视频的强制顺序**（每段内必须按此顺序连续播放）
- 序列之间 + 不在任何序列里的视频 = **AI 自由安排位置**
- 用户可以**不填序列**——这意味着"全交给你"
- 创作者写 **跨视频自由转场** 时 AI 可自由发挥
- **不要**误以为"没在序列里的视频不重要"——它们可能更重要

### 速度范围 (speed-up / slow-down factor)

- 表单 max=100（**建议值**），不是硬限制
- **执行器二次校验**：
  - `0.2 <= factor <= 10` → 正常
  - `10 < factor <= 100` → 高倍速（如冥想缩时），允许
  - `factor > 1000` → 报错退出，提示"几乎看不清，请确认"
  - `factor < 0.1` → 报错，提示"慢到几乎静止"
- 创作者填的 factor=90（冥想 10 分钟缩到 7 秒）是合理用例

### 自动读版本文件 diff

AI 收到 intent.json 后，**自动检查工作区里的版本文件**：

- `intent.json` (最新)
- `intent_v1.json` / `intent_v2.json` / ... (历史)

如果有多个版本：
- 自动 diff 所有字段变更
- 找出**哪些视频/字段被改**
- 重点关注变化区域，不是重新理解全部

创作者**不需要**在 `history[].note` 手动写"我改了啥"——AI 自己读 diff 就懂。

### 真实照片 vs 插画

封面图 / 内容图都用 `cover_ai.py` 或 `matrix_generate_image` **生成插画**，**不放真实照片**。
- prompt 要写明 "扁平设计 / 插画 / illustration / 平面设计" 等关键词
- 创作者提供的 JPG 文件**可以**作为内容参考，但封面不直接用

### 新增 ops (v0.6+)

| op 名 | 中文 | 字段 | 用途 |
|---|---|---|---|
| `insert-image` | 插入图片 | `file`, `at`, `duration`, `note` | 视频中插入静态图片（停顿 N 秒） |
| `opening-text` | 片头文字 | `text`, `duration`, `note` | 视频前 N 秒叠加文字卡（场景说明） |

**未实现的 op 触发 fallback**：如果 intent.json 里有 ops 名称不在已知列表中，AI 应：
1. 读 op 的 note 字段看用户意图
2. 尝试用最接近的智剪工坊脚本实现
3. 在最终回复里告知"该 op 暂用 X 脚本模拟"


---

## 主体流程

> 智剪工坊为单 vlog 项目提供端到端流程。详见 [架构.md](架构.md)。

### 一句话目标

用户写一个 intent.json，AI 按 `粗加工 → 模板加载 → 工作流 → 成片` 流程，把一堆原始视频拼成一段可用的 vlog。

### 工具端（智剪工坊/）

```
智剪工坊/
├── SKILL.md
├── 架构.md
├── 模板/                ← 类别化工作流
│   ├── 健身vlog.yaml
│   ├── 教程vlog.yaml
│   └── ...
├── 脚本/                ← 30 个原子
├── lib/
│   ├── common.py        ← 公共（ffmpeg + 错误 + 日志）
│   ├── asr.py           ← ASR 包装（whisper）
│   └── modify.py        ← 改素材操作菜单
├── 文档/                ← references/
├── intent.html
└── executor.py          ← 粗加工执行器（5 个原子函数）
```

### 工作区（<workspace>/）

```
<workspace>/
├── video_*.mp4                ← 源视频（AI 不动）
├── intent.json                ← 唯一跟源混居的 AI 文件
├── intent_v1.json             ← 版本快照
└── 00_智剪/                   ← AI 自管区
    ├── 粗加工/
    │   ├── 单视频/            ← 每个视频处理后的标准片段
    │   ├── 组合/              ← sequence + 转场拼好的组
    │   ├── 文字稿/            ← ASR 结果
    │   ├── 中间产物/          ← log / profile
    │   └── 决策.md            ← 整体要求 + 用户新增
    └── 成片/
        └── vlog_final.mp4     ← 模板工作流深度加工后
```

### 完整流程

```
1. AI提示用户电脑端可以打开intent.html进行素材处理，并且尝试帮助用户打开intent.html
2. 用户：intent.html 填表 → intent.json
3. 用户：把 intent.json 给 AI
4. AI：和用户一轮一轮交互 直至理解intent.json表达的含义和用户的想法一致
5. AI：素材粗加工（5 步）
6. AI：根据用户意图 或者 查看 视频关键帧和文字稿判断推荐用户加载的模板文件
   "你这是 [项目] [类型]，看到匹配 [模板] 模板，加载吗？"
7. AI：加载 模板/<name>.yaml
8. AI：按工作流引导（每 stage 一来一回）
9. AI：拼成 vlog_final.mp4
10. 用户：直接播放看
```

### 粗加工 5 步（详细）

**输入**：`intent.json`
**输出**：`00_智剪/粗加工/` 下 5 类文件

#### Step 1：解析 + 自检
- 解析 JSON
- 检查源文件存在、必填字段、exclude 列表
- 写状态到 `中间产物/自检报告.json`
- **失败**：列源缺失 / 字段缺失清单（不退出，让用户看到）

#### Step 2：单视频处理（per-video）

- 遍历 `intent.json.videos` 数组
- 每个视频：源 mp4 + ops → `单视频/video_{idx}.mp4`
- 同时写 `单视频/profile_{idx}.json`：
  ```json
  {
    "index": 3,
    "source_file": "video_xxx.mp4",
    "source_resolution": "1080x1920",
    "has_rotation_metadata": true,
    "applied_ops": ["cut-middle"],
    "output_resolution": "1920x1080",
    "output_duration": 6.4,
    "voice_mode": "keep"
  }
  ```
- **A 汇总报告**（Step 2 完成后）：
  - AI 输出 markdown 摘要到聊天 + 写入 `中间产物/单视频汇总.md`
  - 包含：每个视频的 applied_ops 列表、时长变化、有/无异常
  - 用户自看 `00_智剪/粗加工/单视频/`，不要求逐个交互

#### Step 3：sequence 拼接

- 输入：`单视频/` 里的成品 + `intent.json.sequences`
- 处理：每个 sequence 按内部顺序 xfade 链拼 → `组合/seq_{name}.mp4`
- 跨 sequence 最后再拼一次
- 写 `中间产物/拼接日志.log`

#### Step 4：ASR 文字稿

- 用 `lib/asr.py`（whisper / faster-whisper）转录
- 每个 `单视频/video_{idx}.mp4` → `文字稿/视频_{idx}.md`
- 合并：`文字稿/全部.md`

#### Step 5：决策报告

写 `决策.md`：
- intent.json 整体要求摘要
- 异常情况报告（哪些源是竖屏、哪些有 rotation、哪些 op 可能出问题）
- 用户在粗加工过程中提的额外要求

### 模板工作流

**模板 = 工作流脚本**。每个 stage = AI 一来一回对话。详细见 `模板/健身vlog.yaml`。

### 模板命名规则

按**类别**（不带人名）：
- `健身vlog.yaml` — 健身/减肥/训练记录
- `教程vlog.yaml` — 知识教学
- `VLOG.yaml` — 通用日常

### 约定

| # | 约定 |
|---|---|
| 1 | 粗加工是实质工作，每步生成文件 |
| 2 | 模板是工作流脚本，不是 config |
| 3 | 工作区结构：源视频 + `00_智剪/粗加工/` + `00_智剪/成片/` |
| 4 | 目录命名：粗加工中文，文件名/JSON 字段英文 |
| 5 | `intent.json` 跟源混居 |
| 6 | 不写 `decisions.json` / `state.json` / `review.html` |
| 7 | 模板命名按类别，不带人名 |
| 8 | HTML 文件名保持英文 |
| 9 | 不写 `schemas/` |
| 10 | 用户主导决策，每 stage 用户点头 |
| 11 | 粗加工失败不退出主体，列在决策.md；子流程修复后重跑 |

