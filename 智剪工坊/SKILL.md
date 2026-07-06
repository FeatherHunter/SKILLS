---
name: 智剪工坊
description: >
  代码视频剪辑工作台,对标剪映(图形化)+ 扩展(AI 能力)。
  触发词:剪辑、剪切、拼接、转场、调色、慢动作、推镜头、字幕、封面、BGM、流水线、一条龙、智剪工坊、视频工坊、代码剪辑、
  美颜、磨皮、瘦脸、大眼、
  去水词、填充词、口头禅、嗯啊、
  改词、改写、翻唱、配音、换声、改写文案、
  文字成片、AI 生成视频、
  数字人、虚拟人、AI 讲解、
  音频降噪、降噪、噪声处理。
  包含 30 个原子脚本 + 主体流程(阶段 0-4：项目初始化 / 意图对齐 / 粗加工 / 模板 / 收尾)。
  底层:ffmpeg + OpenCV + mediapipe + mmx matrix MCP(免费 AI 能力)。
triggers:
  - 剪辑
  - 剪切
  - 拼接
  - 转场
  - 淡入淡出
  - 调色
  - LUT
  - 慢动作
  - 推镜头
  - 字幕
  - 烧字幕
  - 封面
  - AI 封面
  - BGM
  - 加音乐
  - 音频降噪
  - 降噪
  - 美颜
  - 磨皮
  - 瘦脸
  - 大眼
  - 去水词
  - 填充词
  - 嗯啊
  - 改词
  - 翻唱
  - TTS
  - 配音
  - 换声
  - 文字成片
  - 数字人
  - 虚拟人
  - AI 讲解
  - 批量
  - 智能剪辑
  - 金句
  - 节拍卡点
  - 自动字幕
metadata: { "openclaw": { "emoji": "🎬", "requires": { "python": ">=3.10" } } }
---

# 智剪工坊 — 代码视频剪辑工作台

## 文件地图（v1.2 精简后）

**AI 第一件事**：只读 SKILL.md。**不要 grep 找文件**——所有需要读的子文档都在 §14 子技能索引里**显式列出**，按需加载。

| 文件 | 作用 | 何时读 |
|---|---|---|
| **SKILL.md** | 工具契约（本文件） | **必读第一份** |
| **references/01-16.md** | 16 个子技能详细文档（触发词 + 参数 + ffmpeg） | 路由命中子技能后**REQUIRED** 读对应文档 |
| `scripts/*.py` | 36 个原子脚本（参数 `-i` `-o` `--start` `--output`） | AI 调脚本时按参数调用 |
| `lib/common.py` | ffmpeg 包装 + 错误 + 日志 + safe_run | 共享逻辑，**勿重写** |
| `lib/asr.py` | faster-whisper 包装 | 阶段 2 Step 2.1（ASR 优先） |
| `lib/processing.py` | 视频滤镜 + 转场 + rotation | 阶段 2 Step 2.2 / Step 3 |
| `lib/cli_args.py` | argparse 基础封装 | 写新脚本时复用 |
| ~~`executor.py`~~ | ~~5 个原子函数 + `run_coarse` 编排~~ | **❌ v1.2 已删除**（v0.7 时代批处理工具，跟 v1.0 阶段 2 流程契约矛盾） |
| `intent.html` | 唯一前端：填表 → intent.json | 阶段 0 项目初始化 |

> **不读**：`.archive/`（CHANGELOG / HANDOFF / README / 架构 / docs/ 历史沉淀），开发者面向，AI 不读。

**v1.2 当前状态**：
- ✅ 协议层：SKILL.md + references/15 个子技能文档（一子技能一文档）
- ✅ 代码层：scripts/ 36 个 + lib/ 6 个（v1.2 删了 modify.py + llm_client.py，executor.py 也删）
- ✅ 命名统一：参数 `-i` `-o` `--start` `--output`（v1.2 patch）
- ✅ 阶段 1 必走：操作清单 schema（6 象限）作为阶段 2 执行契约
- ✅ 阶段 2：ASR 前置 + 6 个 pipeline step 脚本（pipeline_step1_check / pipeline_step2_asr / pipeline_step2_process / pipeline_step3_assemble / pipeline_step4_review / pipeline_step5_decide）
- 🔄 模板库：当前 1 个（`健身vlog.yaml`），按类别扩展（教程vlog / VLOG 等）
- ⏸️ lib/modify.py 序列操作是 stub

**v1.2 关键设计**（详见 §主体流程 章节）：
- **阶段 0-4** 端到端流程（项目初始化 / 意图对齐 / 粗加工 / 模板 / 收尾）
- 阶段 1 必走：**操作清单 schema**（6 象限）作为阶段 2 执行契约
- 阶段 2 Step 2：**ASR 前置**，与单视频处理同步产出
- 阶段 2 Step 4：**整体复核 + 模糊项兜底**（AI 不闷头猜）
- 三原则：**零硬编码 / 零遗漏 / 零猜测**
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

## 14 个子技能索引

**AI 路由协议**：命中下表任一子技能的触发词 → **REQUIRED: read references/XX.md** → 再调 scripts/*.py。**禁止跳过 references 直接调脚本**。

| # | 子技能 | 触发词 | 文档（REQUIRED） | 脚本 |
|---|---|---|---|---|
| 01 | **cut** | 剪切、切这段、保留 X 秒、从 A 到 B | [references/01-cutting.md](references/01-cutting.md) | `scripts/video_trim.py` |
| 02 | **xfade** | 转场、淡入淡出、溶解、擦除、切换、黑场、白闪、圆形转场、像素化、径向 | [references/02-transitions.md](references/02-transitions.md) | `scripts/video_xfade.py` |
| 03 | **effects** | 慢动作、慢放、0.5 倍速、推镜头、zoom in、推到脸、插帧、放大、缩小、模糊、抖动、镜像 | [references/03-effects.md](references/03-effects.md) | `scripts/video_fx.py`, `scripts/video_keyframe.py` |
| 04 | **cinematic** | J-cut、L-cut、speed ramp、跳剪、变速、上下黑边、黑场、白闪、闪回、匹配剪辑 | [references/04-cinematic.md](references/04-cinematic.md) | `scripts/video_speed.py`, `scripts/video_reverse.py`, `scripts/video_multicam.py` |
| 05 | **color** | 调色、LUT、cinematic、teal & orange、调亮、调暗、对比度、饱和度、色温、风格化、HDR | [references/05-color.md](references/05-color.md) | `scripts/video_color.py`, `scripts/video_style.py`, `scripts/video_hdr.py` |
| 06 | **text** | 字幕、烧字幕、字幕动效、打字机、打字效果、淡入、弹跳、跑马灯、标题、文字 | [references/06-text.md](references/06-text.md) | `scripts/video_subtitle.py`, `scripts/audio_voice.py`, `scripts/ai_translate.py` |
| 07 | **audio** | 加音乐、配乐、背景音乐、循环、淡入、淡出、混音、音量、**音频降噪、降噪、噪声处理**、节拍、BGM | [references/07-audio.md](references/07-audio.md) | `scripts/audio_bgm.py`, `scripts/audio_beat.py` |
| 08 | **cover** | 封面、做封面、AI 封面、AI 生图、设计封面、缩略图、thumbnail | [references/08-cover.md](references/08-cover.md) | `scripts/ai_cover.py` |
| 09 | **ai-features** | AI 剪辑、智能剪辑、AI 抠图、自动找金句、金句、节拍卡点、自动字幕、人脸追踪、换背景、**去水词** | [references/09-ai-features.md](references/09-ai-features.md) | `scripts/ai_cutout.py`, `scripts/ai_quotes.py`, `scripts/video_scene.py`, `scripts/video_mask.py`, `scripts/video_overlay.py`, `scripts/video_reframe.py`, `scripts/ai_fillers.py` |
| 10 | **batch** | 批量、批处理、100 个视频都、批量加转场、批量调色、批量转码 | [references/10-batch.md](references/10-batch.md) | `scripts/batch.py` |
| 12 | **🆕 beauty** | 美颜、磨皮、瘦脸、大眼、美白、人脸美化 | [references/12-beauty.md](references/12-beauty.md) | `scripts/ai_beauty.py` |
| 13 | **🆕 rewrite-audio** | 改词、改写、翻唱、配音、换声、改写文案、TTS | [references/13-rewrite-audio.md](references/13-rewrite-audio.md) | `scripts/ai_rewrite.py` |
| 14 | **🆕 text-to-video** | 文字成片、AI 生成视频、文生视频 | [references/14-text-to-video.md](references/14-text-to-video.md) | `scripts/ai_text_to_video.py` |
| 15 | **🆕 digital-human** | 数字人、虚拟人、AI 讲解、头像说话 | [references/15-digital-human.md](references/15-digital-human.md) | `scripts/ai_digital_human.py` |
| 16 | **🆕 edit** | 去头去尾、调音量、静音、黑边、缩放、裁剪、旋转、翻转、提音、淡入淡出、水印、多分辨率、GIF、缩略图 | [references/16-edit.md](references/16-edit.md) | `scripts/edit.py`（14 子命令） |

> 实际有 36 个 Python 脚本（部分子技能含多个脚本），详见 `scripts/` 目录。

**路由示例**：

```
用户说"降噪"
  ↓
命中 §14 索引第 07 audio（触发词"音频降噪"）
  ↓
REQUIRED: 读 references/07-audio.md
  ↓
找到 [§D 音频降噪](references/07-audio.md#d-音频降噪)（ffmpeg highpass / afftdn 命令）
  ↓
调底层 ffmpeg 或 scripts/audio_bgm.py 加 BGM 时一并处理
```

## 调用范式

### 单技能调用

```
用户: "把这两段视频加个 1 秒的淡入淡出转场"
  ↓
路由到: 02 xfade（命中触发词"转场"/"淡入淡出"）
REQUIRED: 读 references/02-transitions.md
  ↓
参数确认: 转场类型 / 时长 / offset
执行: scripts/video_xfade.py -a clip1.mp4 -b clip2.mp4 --type fade --duration 1 -o joined.mp4
输出: joined_with_fade.mp4
```

### AI 增强(agent-driven 流程)

```
用户: "去掉我 vlog 里的'嗯啊那个'"
  ↓
路由到: 09 ai-features（命中触发词"去水词"）
REQUIRED: 读 references/09-ai-features.md
  ↓
Step 1: scripts/ai_fillers.py transcribe -i vlog.mp4 --srt vlog.srt
Step 2: (Mavis 读 SRT + words.json) 判 10 个水词,返回词索引
Step 3: scripts/ai_fillers.py cut -i vlog.mp4 --srt vlog.srt -o clean.mp4 --remove-words "1,3,11,12,19,28,37,38,39,45"
输出: 干净视频(20s → 16.7s,省 3.3s)
```

### 大流程(主体阶段 0-4)

```
用户: "做一段完整 vlog,从素材到发布版"
  ↓
路由到: 阶段 0-4（详见 §主体流程 章节）
  阶段 0: AI 帮用户用 intent.html 填表 → intent.json
  阶段 1: AI 读 intent.json → 生成操作清单（6 象限 schema）→ 用户确认
  阶段 2: 粗加工 5 步（调 step1~5 脚本）
  阶段 3: 模板工作流（按 健身vlog.yaml 之类）
  阶段 4: 收尾成片（烧字幕 + BGM + 封面）
```

## 通用参数(所有子技能共享)

| 参数 | 短选项 | 默认值 | 说明 |
|---|---|---|---|
| `--input` | `-i` | (必填) | 输入视频或图片 |
| `--output` | `-o` | (必填) | 输出路径 |
| `--start` | - | 0 | 起始时间(秒)，**v1.2 命名统一**：cut.py 原 `--ss` 已改 `--start` |
| `--duration` | - | 全长 | 时长(秒) |
| `--resolution` | - | 1080:1920 | 输出分辨率(竖屏 vlog) |
| `--fps` | - | 30 | 帧率(强制统一避免 8 小时视频 bug) |
| `--vcodec` | - | libx264 | 视频编码(避开 NVENC 崩溃) |
| `--crf` | - | 20 | 质量(0-51,越小越清) |
| `--acodec` | - | aac | 音频编码 |
| `--abitrate` | - | 128k | 音频码率 |
| `--verbose` | - | False | 显示 debug 日志(写到 `~/.zhijian/logs/`) |

> 已知 bug 排查:见 `.archive/CHANGELOG.md`(版本历史)和 `.archive/HANDOFF.md`(开发历史)。子技能内部 bug 见 `references/05-color.md` / `09-ai-features.md` 等。

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
| 模板/<name>.yaml | ⚠️ 草稿 | 见[.archive/架构.md §8 D](.archive/架构.md) |
| ~~executor.py 粗加工~~ | ~~❌ 未动~~ | **v1.2 已删**（v0.7 时代批处理工具，与 v1.0 阶段 2 契约矛盾） |

## 相关工具链

- **ffmpeg**:`D:\0Tools\Python313\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg.exe` v7.1
- **Python** 3.13(用户级)
- **mediapipe** 0.10.35(task-based API)
- **mmx matrix MCP**:TTS(327 声音)/ 视频生成 / 数字人(通过 `mavis mcp call matrix` 调用)
- **Whisper**:faster-whisper small(默认)/ 显存允许可换 medium/large-v3

## License

MIT

---

## AI 协作协议 (v1.2 强制)

> **渐进式披露原则**：AI 必须按本协议加载文档，**禁止用 grep/glob 在目录里搜文件**。所有需要读的子文档都在 §14 子技能索引里**显式列出**。

**加载顺序（AI 必读）**：

```
1. 加载本文件（SKILL.md）
        ↓
2. 读 §14 子技能索引 → 命中子技能（如 "转场" → 02 xfade）
        ↓
3. REQUIRED: 读对应 references/XX.md（§14 索引里显式列了）
        ↓
4. 调 scripts/*.py（按 references/XX.md 的命令例子）
```

---

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
| `opening-text` | 片头文字 | `text`, `duration`, `note` | 视频前 N 秒画面上叠加场景说明文字 |

**未实现的 op 触发 fallback**：如果 intent.json 里有 ops 名称不在已知列表中，AI 应：
1. 读 op 的 note 字段看用户意图
2. 尝试用最接近的智剪工坊脚本实现
3. 在最终回复里告知"该 op 暂用 X 脚本模拟"


---

## ⚠️ AI 必读（v1.0 强制）

加载本 skill 必看。任何 AI 在执行智剪工坊前必须读完本节。

**核心原则（3 条）**

1. **零硬编码** — 不绑定具体项目（vlog 主题、平台、用户）。所有流程描述用通用 schema，遇到项目特有需求必须从 intent.json 读取。
2. **零遗漏** — intent.json 每个字段必须有去处（明确操作 / 隐含意图 / 未覆盖说明）。无"AI 心里有数"这种模糊状态。
3. **零猜测** — 凡 AI 推断的、模糊的、未覆盖的，必须主动交互式采访，不允许闷头执行。详见「AI 交互式采访触发条件」章节。

**执行契约（4 条，违反任意一条视为流程失败）**

- 阶段 1 必须输出「操作清单」并经用户确认 → 才进入阶段 2
- 阶段 2 Step 2 每处理完一个视频 → 立即向用户汇报产物路径 + 摘要 + 异常
- 出现卡死 / 超时 → 立即向用户汇报，不得静默
- 用户未明确指定的选项 → 用操作清单 D 象限（模糊项汇总）列出，逐条问

---

## 主体流程

> 智剪工坊为单 vlog 项目提供端到端流程。详见 [.archive/架构.md](.archive/架构.md)。

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
└── ~~executor.py~~      ← **v1.2 已删**（v0.7 时代批处理工具）
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
        ├── vlog_final.mp4     ← 模板工作流深度加工后
        └── cover.jpg          ← AI 封面
```

### 完整流程（v1.0）

#### 阶段 0 ▸ 项目初始化

```
0.1  AI 提示用户用 intent.html 填表
     (路径由用户在首问时提供；AI 必须主动用 shell 命令帮用户打开文件(如 Start-Process 或 xdg-open)，不得仅告知路径让用户自己找)
0.2  用户填表 → 生成 intent.json
0.3  用户把 intent.json 给 AI
0.4  [可选] 若 intent.json 缺失必填字段
       → AI 触发交互式采访补全
       → 不允许 AI 自己编默认值
```

#### 阶段 1 ▸ 意图对齐（必走）

```
1.1  AI 解析 intent.json → 生成「操作清单.md」（草稿）
     草稿六象限：A.per-video / B.project-level / C.sequence / D.模糊项 / E.推断标记 / F.未覆盖
1.2  AI 向用户呈现清单，重点高亮：
     - 明确操作（可立即执行）
     - 隐含意图（AI 从 notes / overall_intent 推断 → 必须用户确认）
     - 模糊点（必须问，不允许 AI 猜）
     - 未覆盖字段（out-of-scope 说明）
1.3  用户逐条确认/修正/补充
1.4  AI 写「操作清单.md (已确认)」+「自检报告.json」
     → 阶段 1 产物是阶段 2 的执行契约
```



#### 阶段 2 ▸ 粗加工（5 步）（v1.2 整合）

**输入**：`intent.json` + 已确认操作清单（阶段 1 产物）
**输出**：`00_智剪/粗加工/` 下 5 类文件
**阶段契约**：阶段 1 操作清单是本阶段执行契约，无清单不进入本阶段（参见 [§操作清单 schema](#操作清单-schema)）

---

##### Step 1：解析 + 自检

- **输入**：`intent.json` + 已确认操作清单
- **输出**：`中间产物/自检报告.json`
- **跳过**：无（必须遍历所有视频）
- **行为**：
  - 解析 JSON
  - 检查源文件存在、必填字段、exclude 列表
  - 写状态到 `中间产物/自检报告.json`
- **异常处理**：不退出整体；列源缺失 / 字段缺失清单（让用户在决策.md 看到）
- **强制（v1.0）**：异常不退出整体流程

---

##### Step 2：单视频处理 + ASR（v1.1 拆为 2.1 + 2.2，ASR 优先）

###### Step 2.1：ASR 优先（批量转录所有需要 ASR 的视频）

- **输入**：操作清单 A 象限中 `voice != mute / bgm-only` 的项
- **处理**：faster-whisper 转录（`lib/asr.py`）
- **输出**：
  - `文字稿/视频_{idx}.md`（每个视频一份）
  - `文字稿/全部.md`（汇总）
- **跳过**：`voice == "mute"` 或 `"bgm-only"` 的视频不跑 ASR
- **行为**：每完成一个 ASR → 立即向用户汇报
- **目的**：让 Step 2.2 处理视频时 AI 已有文字稿可优化 ops（D2 片头叠加文字内容、D5 水词判定）

###### Step 2.2：单视频处理（基于 ASR 优化）

- **输入**：源 mp4 + ops（来自 intent）+ 文字稿（Step 2.1 产出，可能为空）
- **处理**：trim/cut/pin-range/speed + 可选基于文字稿调整 ops
  - 例 1：文字稿含水词 + `voice: keep-with-filler-removed` → 触发 `remove_fillers`
  - 例 2：文字稿内容 → AI 优化片头叠加文字内容（覆盖 D2 默认）
  - **音频同步（A）**：trim/cut/pin-range 后视频流用 `setpts=PTS-STARTPTS` 归零了 PTS（时间戳从 0 开始），但音频流原始 PTS 范围未归零，音画不同步。必须同步 trim 音频范围并重置 PTS（`atrim + asetpts=PTS-STARTPTS`）。
    - **mute 视频**：源视频无音频轨时 `[0:a]` 不存在，需用 `anullsrc` 生成等长空白音轨（`anullsrc=r=44100:cl=stereo[a];[a]apad=whole_dur=${输出时长}`），否则 filter graph 引用失败。
  - **旋转处理（A）**：rotation metadata = 0 → 不旋转；≠ 0 → 由 `transpose` 实现像素旋转
    - 0° → 空 filter
    - 90° → `transpose=1`
    - -90°/270° → `transpose=2`
    - ±180° → `transpose=1,transpose=1`
    旋转后清 metadata（见"后处理"字段）
   - **比例处理方式（来自 intent.output.aspect_handling）**：
     - `aspect-fit`（默认）：竖屏源 → counter-rotate（竖屏构图）+ 左右黑边；横屏源 → 不旋转（横屏构图）+ 上下黑边
       - 核心：rotation≠0 时 counter-rotate；rotation=0 时不旋转；再按目标比例加黑边适配
       - 实现：`rotation != 0` → counter-rotate（`transpose`）；`rotation == 0` → 不旋转；`scale:force_original_aspect_ratio=decrease + pad` 填黑边
     - `aspect-fill`：竖屏源 → counter-rotate（竖屏构图）+ 填满（可能裁切）；横屏源 → 不旋转（横屏构图）+ 填满
       - 核心：rotation≠0 时 counter-rotate；rotation=0 时不旋转；再按目标比例强制填满
       - 实现：`rotation != 0` → counter-rotate（`transpose`）；`rotation == 0` → 不旋转；`scale:force_original_aspect_ratio=increase` 填满
     - **counter-rotate 独立原则**：rotation≠0 时永远 counter-rotate（让像素变正确方向）；scale/pad 策略才区分 aspect-fill/fit
     - **四场景矩阵**：
       | 源显示 | 目标像素 | aspect-fill | aspect-fit |
       |---|---|---|---|
       | 竖屏（≠0） | 竖屏 | counter-rotate，填满 | counter-rotate，填满 |
       | 竖屏（≠0） | 横屏 | counter-rotate，填满 | counter-rotate，左右黑边 |
       | 横屏（=0） | 竖屏 | 不旋转，上下黑边 | 不旋转，横屏构图，左右黑边 |
       | 横屏（=0） | 横屏 | 不旋转，填满 | 不旋转，填满 |
- **输出**：
  - `单视频/video_{idx}.mp4`
  - `单视频/profile_{idx}.json`（格式见下方 schema）
- **跳过**：`exclude == true`
- **行为**：
  - 每处理完一个 → 立即向用户汇报（产物路径 + 摘要 + 异常）
  - 出现卡死 / 超时 → 立即向用户汇报
   - **应用 ops 顺序：counter-rotate → 用户 op → scale/pad（aspect-fill 或 aspect-fit）**
  - **ASR 触发条件**：与 Step 2.1 一致（`voice != mute / bgm-only`）
- **异常处理**：分两种，不退出整体
  - **命令失败**：ffmpeg return code ≠ 0 → 写入 `profile.error`，继续下一个视频
  - **产物无效**：ffmpeg 成功但输出 < 1KB → 写入 `profile.error`，继续下一个视频
- **后处理（B）**：ffmpeg 编码成功后必须调用 `patch_mp4_rotation`（`lib/patch_mp4_rotation.py`）直接改写 mp4 tkhd matrix atom，清除残留的 displaymatrix metadata。ffmpeg 的 `-bsf:v h264_metadata=rotate=0` 和 `-metadata:s:v:0 rotate=0` 对某些编码器不生效，必须二进制 patch 才可靠。
  - **patch 失败**：不影响 Step 2.2 成功判定；主产物（ffmpeg 写的 mp4）已存在且正确，patch 失败只记警告。
- **强制（v1.0）**：
  - 每处理完一个 → 立即向用户汇报，不得静默
  - 卡死 / 超时 → 立即向用户汇报，不得静默
  - 用户可随时叫停审查

**profile_{idx}.json schema**（v1.0）：

```json
{
  "index": 3,
  "source_file": "video_xxx.mp4",
  "source_resolution": "1080x1920",
  "has_rotation_metadata": true,
  "rotation_applied": -90,
  "applied_ops": ["cut-middle"],
  "output_resolution": "1920x1080",
  "output_duration": 6.4,
  "voice_mode": "keep",
  "output_path": "D:\\\\...\\\\单视频\\\\video_03.mp4"
}
```

**A 汇总报告**（Step 2.2 完成后，v1.0 强制）：
- AI 输出 markdown 摘要到聊天 + 写入 `中间产物/单视频汇总.md`
- 必须包含：每个视频的 applied_ops 列表、时长变化、有/无异常

---

##### Step 3：sequence 拼接（仅 sequence 内视频）

- **输入**：`单视频/` 里的成品 + `intent.json.sequences`
- **输出**：
  - `组合/seq_{name}.mp4`（每个 sequence 一段）
  - `中间产物/拼接日志.log`
  - `中间产物/自由素材清单.md`（v1.0 新增：列出**不在任何 sequence 内**的视频，留给模板阶段）
- **跳过**：不在任何 sequence 内的视频
- **行为**：每个 sequence 按内部顺序 xfade 链拼；跨 sequence 最后再拼一次
- **异常处理**：ffmpeg 失败 → 写入拼接日志，不退出整体
- **强制（v1.0）**：跨 sequence 最后再拼一次（一次性拼接全片）

---

##### Step 4：整体复核 + 模糊项兜底

- **输入**：操作清单 D 象限 + Step 2/3 实际产物
- **输出**：
  - `中间产物/模糊项处理记录.md`
  - （可能的）`单视频/video_xx.mp4` 更新
  - （可能的）`文字稿/video_xx.md` 更新
- **行为**：
  - 重新审视所有"模糊项"（意图对齐阶段没明确 + Step 1-3 没处理的）
  - 跟用户**逐条澄清** → 应用原子操作 → 更新产物
  - 每处理完一个模糊项 → 写入处理记录
- **强制（v1.0）**：
  - 模糊项**不闷头猜**：D 象限中标记"必须问"的项目，必须等用户回答
  - 已"建议问"的项目，AI 可提供默认假设 + 让用户否决

---

##### Step 5：决策报告 + 模板衔接

- **输入**：全量产物
- **输出**：`决策.md`
- **行为**：写决策报告 + 进入模板工作流

**决策.md** 必须包含：
- intent.json 整体要求摘要
- 异常情况报告（哪些源是竖屏、哪些有 rotation、哪些 op 可能出问题）
- 用户在粗加工过程中提的额外要求
- 模板加载建议（v1.0 新增：基于操作清单 + 关键帧 + ASR 文字稿）
- 进入模板工作流（阶段 3）

#### 阶段 3 ▸ 模板工作流

**AI 必读**：阶段 2 每一步都有对应 step 脚本，AI 不应自己写新逻辑，必须调用现有脚本。

| Step | 调哪个脚本 | 做什么 |
|---|---|---|
| Step 1 解析 + 自检 | `scripts/pipeline_step1_check.py` | 解析 intent.json → 写 `中间产物/自检报告.json` |
| Step 2.1 ASR 优先 | `scripts/pipeline_step2_asr.py` | 批量 Whisper 转录 → `文字稿/视频_{idx}.md` |
| Step 2.2 单视频处理 | `scripts/pipeline_step2_process.py` | 基于 ASR 优化 + 处理 → `单视频/video_{idx}.mp4` |
| Step 3 sequence 拼接 | `scripts/pipeline_step3_assemble.py` | xfade 链按 sequence 拼 → `组合/seq_<name>.mp4` |
| Step 4 模糊项兜底 | `scripts/pipeline_step4_review.py` | 跟用户逐条澄清 → `模糊项处理记录.md` |
| Step 5 决策报告 | `scripts/pipeline_step5_decide.py` | 写决策报告 + 模板建议 → `决策.md` |

**顶层编排入口**：AI 按 §AI 协作协议 v1.2 强制 加载顺序，**REQUIRED: 读 references/XX.md**，然后调 scripts/pipeline_step*.py。**v1.2 删除了 executor.py**——AI 不要一键跑完，要逐步调每步跟用户交互。

```
- AI 推荐模板（按操作清单 + 关键帧 + ASR）
- 用户确认
- 加载 模板/<name>.yaml
- 按 stage 一来一回（每 stage AI 提方案 → 用户点头 → 执行）
```

#### 阶段 4 ▸ 收尾成片

```
- 烧字幕（按 ASR 文字稿）
- BGM 混合
- 封面生成 → 00_智剪/成片/cover.jpg（按 cover.prompt，prompt 不明时 AI 必须问）
- 输出成片: 00_智剪/成片/vlog_final.mp4
```

### 操作清单 schema（v1.0 强制）

#### 触发条件

阶段 1 必须产出本清单，作为阶段 2 的执行契约。无清单不进入阶段 2。

#### Schema（6 象限）

```markdown
# 操作清单 v{ver}

> 状态：草稿 / 已确认 / 已变更
> 来源：<workspace>/intent.json（修订号 v{n}）

## A. per-video 操作
| # | 文件 | 源 ops | 隐含 ops（AI 推断） | 落地 step | 状态 |
|---|------|--------|-------------------|----------|------|

## B. project-level 操作
| 来源字段 | 拆解后操作 | 落地阶段 | 产物 | 状态 |
|---------|----------|---------|------|------|

## C. sequence 约束
| sequence 名 | 包含视频 | 转场配置 | 产物路径 |
|------------|---------|---------|---------|

未约束视频（自由素材）：[v...]
→ 不在 Step 3 处理，留给模板工作流 Stage 顺序阶段。

## D. 模糊项 / 待澄清
| # | 来源字段 | 模糊内容 | AI 默认假设 | 是否必须问 |
|---|---------|---------|------------|-----------|

## E. AI 推断 vs 用户明确
- ✅ 用户明确：videos[*].ops 中所有 on=true 的字段
- ⚠️ AI 推断：notes / overall_intent / cover.prompt / target_length
- ❓ 未提及：videos 中无 ops / intent / notes 的项

## F. 未覆盖字段（out-of-scope）
- 字段名 + 不处理的原因 + 如需处理 AI 该怎么问

## 版本
- v{n}: <变更摘要>
```

#### 使用规则

- A+B+C = 已落地的操作（阶段 2 可直接执行）
- D = 必须/建议问的（不闷头猜）
- E = 透明标记（用户一眼看出哪些是 AI 猜的）
- F = 明确说"我不处理这个"（防止误以为漏了）
- 每条都有状态列：pending / confirmed / n/a / info

#### G. op 白名单（AI 必读）

**目的**：videos[].ops 里的合法 op 名是固定的，AI 看到不在白名单的 op 必须问用户（不要瞎猜）。

**两层架构**：video 级 ops（§G.1）+ sequence 级 transitions（§G.2）

##### §G.1 video 级 ops（每个视频单独处理）

| op 名 | 大白话 | 对应 CLI | 参数语义 |
|---|---|---|---|
| `trim-head` | 剪头 N 秒 | `processing.py build_video_filter` | `{on: bool, sec: 数字}` |
| `trim-tail` | 剪尾 N 秒 | `processing.py build_video_filter` | `{on: bool, sec: 数字}` |
| `pin-range` | 强制保留某段时间 | `processing.py build_video_filter` | `{on: bool, start: "HH:MM:SS", end: "HH:MM:SS"}` |
| `cut-middle` | 切掉中间某段 | `processing.py build_video_filter` | `{on: bool, from: "HH:MM:SS", to: "HH:MM:SS"}` |
| `speed-up` | 加速 | `processing.py build_video_filter` | `{on: bool, factor: float}`（>1 加速） |
| `slow-down` | 减速 | `processing.py build_video_filter` | `{on: bool, factor: float}`（<1 减速） |
| `reverse` | 倒放 | `video_reverse.py` | `{on: bool}` |
| `mute` | 静音 | `processing.py build_video_filter` | `{on: bool}`（用 voice='mute'） |
| `fade-in` | 视频开头淡入 | `video_fade.py` / `processing.py` | `{on: bool, sec: 数字}` |
| `fade-out` | 视频结尾淡出 | `video_fade.py` / `processing.py` | `{on: bool, sec: 数字}` |
| `opening-text` | 视频前 N 秒叠场景文字 | `video_opening.py` | `{on: bool, text: str, duration: 秒, region: str}` |
| `insert-image` | 视频中插入静态图片 | `video_overlay.py` | `{on: bool, file: path, at: 秒, duration: 秒}` |
| `color` | 调色 | `video_color.py` | `{on: bool, preset: str}`（cinematic/warm/cool/vintage/bw/high-contrast） |
| `rotate` | 旋转 90/180/270 | `edit.py rotate` | `{on: bool, degrees: int}` |
| `scale` | 缩放 | `edit.py scale` | `{on: bool, width: int, height: int}` |
| `crop` | 裁剪 | `edit.py crop` | `{on: bool, x: int, y: int, width: int, height: int}` |
| `subtitle` | 自动字幕 | `video_subtitle.py` | `{on: bool, style: str, language: str}`（中文/英文/auto） |
| `audio` | 加 BGM | `audio_bgm.py` | `{on: bool, file: path, volume: float}` |
| `target-duration` | 成片时长上限 | `processing.py` | `{on: bool, sec: 数字}` |

##### §G.2 sequence 级 transitions（两段视频之间）

**字段位置**：`sequences[].transitions[].{type, duration}`

**9 种 intent.html type + 路由**：

| 意图 type（intent.html） | 含义 | AI 路由 | 底层 ffmpeg xfade |
|---|---|---|---|
| `none` | 不开转场 | 短路：ffmpeg concat 硬切 | — |
| `cut` | 直切 | 短路：ffmpeg concat 硬切 | — |
| `fade` | 淡入淡出 | `video_xfade.py --type fade` | `fade` |
| `dissolve` | 溶解 | `video_xfade.py --type dissolve` | `dissolve` |
| `wipe-left` | 左擦除 | `video_xfade.py --type wipe-left` | `wipeleft` |
| `wipe-right` | 右擦除 | `video_xfade.py --type wipe-right` | `wiperight` |
| `slide-up` | 上滑 | `video_xfade.py --type slide-up` | `slideup` |
| `zoom-in` | 推进 | `video_xfade.py --type zoom-in` | `zoomin` |
| `blur` | 模糊过渡 | `video_xfade.py --type blur` | `hblur` |

**关键规则**：

- AI 透传 intent.html 友好名（`wipe-left` / `slide-up` / `zoom-in` / `blur`），由 `video_xfade.py` 内部映射到 ffmpeg 合法名
- `none` 和 `cut` 都是"不调 xfade"——区别仅在语义（`none` = 用户没选，`cut` = 用户明确要硬切）
- `duration` 默认 0.5 秒（intent.html input value="0.5"）
- 完整 ffmpeg xfade 支持 60+ 种 transition，但本 SKILL 只声明 9 种意图类型；如需高级类型，AI 应询问用户

**AI 路由规则**：

```
看到 videos[i].ops.{op_name}
  ↓
在 §G.1 video 级 ops 白名单里？ → 是：调对应 CLI
                                  → 否：D 象限"必须问"
看到 sequences[j].transitions[k].type
  ↓
在 §G.2 sequence 级 9 种 type 里？ → 是：调 video_xfade.py(自动映射)
                                     → 否：D 象限"必须问"
```

### Jargon 大白话词典（v1.2 必读）

**目的**：操作清单 / 阶段 0-4 文档里大量技术术语，AI 提问给用户时必须翻译成人话。

| 术语 | 大白话 | 例 |
|---|---|---|
| **intent.json** | 用户的剪辑需求清单 | "把 intent.json 给 AI" → "把你的剪辑清单给 AI" |
| **ops（per-video ops）** | 每个视频要做的动作 | "视频 #3 的 ops" → "视频 #3 你要做哪些处理" |
| **pin-range** | 强制保留某段时间 | "0:30 到 1:00 必须保留" |
| **cut-middle** | 切掉中间某段 | "从 0:50 开始切 5 秒" |
| **insert-image** | 视频中插入静态图片 | "在 1:00 处放 3 秒封面" |
| **opening-text** | 视频前 N 秒叠场景文字 | "片头加 2 秒说明'DAY 1'" |
| **sequence** | 一组视频的强制播放顺序 | "3 段视频必须按 A→B→C 顺序播" |
| **per-video 操作** | 对单个视频的动作 | vs project-level（全局动作） |
| **project-level 操作** | 全项目统一动作 | "所有视频都加 BGM" |
| **ASR** | 把音频转成文字稿 | "Whisper 转录" → "把视频里说的话抄下来" |
| **D 象限（模糊项）** | 用户没说清楚的地方 | "视频 #5 你没说怎么处理 → 必须问你" |
| **E 象限（AI 推断）** | AI 自己猜的部分 | "我猜你希望加 BGM（你没明说）" |
| **F 象限（未覆盖）** | 字段没处理 | "duration 字段我没用 → 不会影响你" |
| **xfade / 转场** | 两段视频之间的过渡效果 | "两段视频之间来个 1 秒淡入淡出" |
| **fade-in / 淡入** | 单段视频开头从黑渐显 | "这段视频开头加 1 秒淡入" |
| **fade-out / 淡出** | 单段视频结尾渐黑 | "这段视频结尾加 1 秒淡出" |
| **none 转场** | 不开转场（硬切） | "我不用转场" → 直接拼接 |
| **cut 转场** | 直切（明确选"硬切"） | "我要硬切" → 同 none，但语义不同 |
| **dissolve / 溶解** | 上一段逐渐透明，下一段逐渐实 | "两段之间溶解一下" |
| **wipe / 擦除** | 一方向推开露出下一段（左/右/上/下） | "从左往右擦过去" |
| **slide / 滑动** | 一段滑出，下一段滑入 | "上滑过渡" |
| **zoom / 推进** | 推镜头进入下一段 | "推进到下一段" |
| **blur / 模糊过渡** | 模糊后清晰过渡 | "中间模糊一下" |
| **counter-rotate** | 像素反转（抵消 metadata） | "源是竖屏但像素是横的，需要反转" |
| **aspect-fill / aspect-fit** | 填满 vs 加黑边 | "填满"裁切；"加黑边"完整保留 |
| **target_length** | 项目目标时长（单位：**秒**，整数） | 用户填 `180` → "目标 3 分钟"；填 `90` → "目标 1 分 30 秒" |

### H. intent.json 字段枚举表（AI 必读）

**目的**：intent.json 各字段的可选值是枚举。AI 看到非法值必须问用户（不要瞎猜）。

| 字段 | 路径 | 类型 | 可选值 / 格式 | AI 必读说明 |
|---|---|---|---|---|
| `version` | 顶层 | string | `"v0.5"` / `"v1.0"` / `"v1.2"` | schema 版本，AI 不修改 |
| `_meta.revision` | 顶层 | int | `1`, `2`, `3`... | intent.json 修订号，每次保存 +1 |
| `project.name` | 顶层 | string | 任意 | vlog 项目名（"DAY 2 减脂日记"） |
| `project.overall_intent` | 顶层 | string | 任意自然语言 | E 象限：AI 推断（用户没结构化） |
| `project.target_length` | 顶层 | int | **秒** | 目标时长（如 `180` = 3 分钟） |
| `output.aspect_ratio` | 顶层 | string | `"9:16"` / `"16:9"` / `"1:1"` / `"4:3"` / `"custom"` | 输出宽高比 |
| `output.aspect_ratio_custom` | 顶层 | string | `"W:H"`（自定义比例） | aspect_ratio="custom" 时必填 |
| `output.aspect_handling` | 顶层 | string | `"aspect-fill"` / `"aspect-fit"` | 比例处理：填满 vs 加黑边 |
| `cover.type` | 顶层 | string | `"ai"` / `"text"` / `"image"` | 封面生成方式（推荐 `"ai"`） |
| `cover.prompt` | 顶层 | string | 英文 prompt 优先 | AI 生图 prompt（参考 `references/08-cover.md`） |
| `ending.type` | 顶层 | string | `"fade"` / `"freeze"` / `"next-day"` / `"text"` | 结尾风格 |
| `ending.prompt` | 顶层 | string | 英文/中文 | 结尾文字 / 主题（参考 §阶段 4 模板） |
| `videos[i].file` | 数组 | string | 文件名（如 `"video_01.mp4"`） | 源视频相对路径 |
| `videos[i].ops` | 数组 | object | 见 §G. op 白名单 | 每个视频的操作（多个 op 可组合） |
| `videos[i].notes` | 数组 | string | 任意自然语言 | E 象限：AI 推断（用户没结构化） |
| `sequences[i].videos` | 数组 | string[] | 文件名列表（顺序敏感） | 强制播放顺序（必须在 sequence 内） |
| `sequences[i].transitions` | 数组 | object[] | `{after, type, duration}` 列表 | sequence 内部转场（每段之间） |
| `sequences[i].transitions[j].after` | 数组元素 | int | video index | 表示"在 index 这段之后"的转场 |
| `sequences[i].transitions[j].type` | 数组元素 | string | `none` / `cut` / `fade` / `dissolve` / `wipe-left` / `wipe-right` / `slide-up` / `zoom-in` / `blur` | 9 种意图 type，详见 §G.2 |
| `sequences[i].transitions[j].duration` | 数组元素 | float | `≥0.5` 秒，默认 `0.5` | 转场时长 |

**字段不在表里怎么办？**

- 看 `references/01-XX.md` 的 §调用范式 + §参数 段——所有字段都有出处
- AI 路由时**严格按 op 白名单**调 CLI（不要瞎传参）
- 字段没 op 对应 → F 象限（明确说"这个字段我不处理"）

### AI 交互式采访触发条件（v1.0 强制）

| 触发条件 | 动作 |
|---------|------|
| intent.json 必填字段缺失 | **必须问**（阶段 0.4） |
| notes / overall_intent 含模糊动词但未指定参数 | **必须问** |
| 同一字段多个相互冲突的 ops | **必须问** |
| sequence 引用的视频不存在 / 被 exclude | **必须问** |
| cover.prompt / cover.type 信息不足 | **必须问** |
| target_length 与实际素材时长差距 >50% | **建议问**（给出估算） |
| videos[i] 完全无 ops / intent / notes | **建议问**（默认 keep 原样） |
| ops.factor / sec 在执行器校验范围外（如 90x） | **不必问**（执行器自己处理） |
| 跨 sequence 的视频顺序冲突 | **不必问**（模板阶段解决） |

**核心规则**：AI 主动问 > AI 闷头猜。任何"AI 默认假设"必须在 D 象限显式列出，让用户看到。

### 场景覆盖度自检（v1.0）

| 通用场景 | 已覆盖？ | 落地位置 |
|---------|---------|---------|
| 用户提供素材 + intent.json，全流程执行 | ✅ | 阶段 0-4 |
| 用户只提供素材，无 intent.json | ⚠️ AI 协助转 intent | 阶段 0.4 触发采访 |
| intent.json 有 v1/v2 历史版本 | ✅ | 阶段 1.1 自动 diff |
| 部分视频 exclude | ✅ | 阶段 2 Step 1 过滤 |
| 单视频多 ops 组合 | ✅ | Step 2 filter_complex 链 |
| 竖屏源 + rotation metadata | ✅ | Step 2 transpose + 清 side_data |
| 项目里有图片（封面/插图） | ✅ | insert-image + B 象限 |
| 用户需要 BGM / 字幕 / 封面 | ✅ | 阶段 4 收尾 |
| 素材是 LIVE Photo / GIF / 图片序列 | ❌ | **AI 必须采访** |
| 非标准字段命名（videos[] → segments[]） | ❌ | **AI 必须采访** |
| 实时同步到飞书 / 多端分发 | ❌ | **AI 必须采访**（提示用其他 skill） |
| 项目横跨多个 workspace | ❌ | **AI 必须采访** |

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
| 12 | **v1.0**：阶段 1 必走，输出「操作清单」作为阶段 2 执行契约 |
| 13 | **v1.0**：ASR 前置到 Step 2，与单视频处理同步产出 |
| 14 | **v1.0**：Step 4 是模糊项兜底环节，AI 不闷头猜 |
| 15 | **v1.0**：未约束视频不在 Step 3 处理，留给模板工作流 Stage 顺序阶段 |
| 16 | **v1.0**：Step 2 每处理完一个视频立即向用户汇报（产物路径 + 摘要 + 异常） |
| 17 | **v1.0**：不硬编码项目内容；所有流程描述用通用 schema |
| 18 | **v1.0**：AI 推断必须显式标记（操作清单 E 象限），不混淆用户明确项 |

