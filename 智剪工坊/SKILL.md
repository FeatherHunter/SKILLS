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
  包含 30 个原子脚本 + 主体流程(阶段 0-4:项目初始化 / 意图对齐 / 粗加工 / 模板 / 收尾)。
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

## 入口模板

加载本技能后，直接输出以下内容给用户，然后在用户答复后进入对应流程：

---

> ⚠️ 开始之前，请把要处理的**所有视频、图片、BGM** 放到**同一个文件夹**里。

### 你今天想做什么？

**① 从零开始做一个完整的视频**（有多个素材，想拼成一个成片）
→ 回答几个问题后，我会帮你规划完整流程

**② 只做一个操作**（比如只剪一刀、只加字幕、只调色）
→ 告诉我你想做什么：
  - "剪掉开头/结尾"
  - "去掉中间一段"
  - "加字幕"
  - "调色/加滤镜"
  - "加背景音乐"
  - "做封面"
  - 其他需求直接说

**③ 多个视频批量处理**（统一剪、统一调色等）
→ 告诉我哪些视频 + 要做什么操作

**④ 用文字生成视频**（没有素材，想用 AI 生成）
→ 说"文字成片"或"AI 生成视频"

**⑤ 数字人讲解**（AI 主播口播）
→ 说"数字人"或"AI 讲解"

---

## v1.3 协议层（核心变化）

**v1.3 架构核心**: **AI 是编排者，原子 CLI 是工具，step 脚本已删除**。

- 阶段 0-4 端到端流程（项目初始化 / 意图对齐 / 粗加工 / 模板 / 收尾）
- 阶段 1 必走：**操作清单 schema**（6 象限）作为阶段 2 执行契约
- 阶段 2-4：**AI 按 SKILL.md + references/ 自己编排原子 CLI**（不再调 step 脚本）
- 三原则：**零硬编码 / 零遗漏 / 零猜测**

---

## 📂 文件地图（v1.3 渐进式披露版）

**AI 第一件事**：只读 SKILL.md（本文）。**按需加载 references/**——不要一次性全读。

| 文件 | 作用 | 何时读 |
|---|---|---|
| **SKILL.md**（本文件）| 工具契约 + 路由表 + 路由总规则 | **必读第一份**（~400 行）|
| `references/剪切拼接-帧级剪切与多段合并.md` | 帧级剪切trim与多段合并concat | 路由命中裁剪时 |
| `references/转场-9种转场类型.md` | 9种转场类型 | 路由命中转场时 |
| `references/AI路由表-意图JSON字段枚举.md` | intent.json字段枚举 | **阶段1必读** |
| `references/视觉特效-慢动作推镜头模糊.md` | 调色/字幕/文字叠加 | 路由命中effects时 |
| `references/主流程-阶段编排.md` | 阶段0-4主体流程 | **选①时必读** |
| `references/电影感剪辑-变速倒放多机位.md` | 推镜头/慢动作/倒放 | 路由命中cinematic时 |
| `references/精剪-剪头剪尾保留段切中间.md` | pin-range/cut-middle多段 | 路由命中cut时 |
| `references/调色预设-18种预设LUT风格迁移.md` | 13种color preset | 路由命中color时 |
| `references/图片转视频-静态图KenBurns效果.md` | image_to_video+KenBurns | 路由命中photo时 |
| `references/字幕文字-Whisper烧字幕片头变声.md` | 字幕/文字叠加/opening-text | 路由命中text时 |
| `references/音频配乐-BGM循环淡入淡出节拍.md` | audio_bgm 4mode+时间段+淡入淡出 | 路由命中audio时 |
| `references/AI封面-生图叠字两步法.md` | 封面生成（ai/text/image）| 路由命中cover时 |
| `references/AI智能剪辑-抠图金句去水词蒙版.md` | AI抠图/去水词/翻唱 | 路由命中AI features时 |
| `references/AI交互式采访触发条件.md` | 8条必问/建议问/不必问触发条件 | **阶段0.4 + 阶段1 + 阶段4必读** |
| `references/场景覆盖度自检.md` | 12条场景支持情况 | 阶段0.4决定是否要问用户时 |
| `references/批量处理-多视频统一操作.md` | 批量处理 | 路由命中批量时 |
| `references/美颜-四种人脸美化.md` | 美颜/磨皮/瘦脸/大眼 | 路由命中美颜时 |
| `references/改词翻唱-文案改写TTS替换音轨.md` | 改词/配音/换声 | 路由命中改写时 |
| `references/文字成片-mmx免key生成6秒片段.md` | 文字成片/AI生成视频 | 路由命中text-to-video时 |
| `references/数字人-AI主播头像说话.md` | 数字人/AI讲解 | 路由命中数字人时 |
| `references/原子操作-14种基础剪辑指令.md` | rotate/scale/crop/mute | 路由命中edit时 |
| `scripts/*.py` | 30+ 个原子 CLI（参数 `-i` `-o` `--start` `--output`）| AI 调脚本时 |
| `lib/common.py` | ffmpeg 包装 + 错误 + 日志 + safe_run | 共享逻辑，**勿重写** |
| `lib/processing.py` | 视频滤镜 + 转场 + rotation | 阶段 2/3 |
| `lib/filename.py` | sanitize_filename + get_output_path | 阶段 4 命名 |
| `intent.html` | 唯一前端：填表 → intent.json | 阶段 0 项目初始化 |

> **不读**：`.archive/`（CHANGELOG / HANDOFF / README / 架构 / docs/ 历史沉淀），开发者面向，AI 不读。

---

## 🚀 一句话目标

**读 intent.json → 调原子 CLI → 出成片**。AI 自己编排，自己决定调什么、怎么调。

---

## 📞 调用范式

### 单技能调用

```bash
# 例: 加 BGM
python scripts/audio_bgm.py --video v.mp4 --bgm bgm.mp3 --volume 0.18 --output out.mp4
```

### AI 增强（agent-driven 流程）

AI 在 §阶段 2-4 按 SKILL.md 路由表自己编排。详见 `references/主流程-阶段编排.md`。

### 大流程（主体阶段 0-4）

```
阶段 0 项目初始化 → 阶段 1 意图对齐 → 阶段 2 粗加工 → 阶段 3 模板 → 阶段 4 收尾
```

详细 AI 编排步骤见 `references/主流程-阶段编排.md`。

---

## 📁 工作区（<workspace>/）

**v1.3 工作区约定**（AI 必读）：

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
    │   ├── 中间产物/          ← log / profile / 自检报告
    │   ├── cover/             ← AI 封面草稿（v1.3 新增，可放多个候选）
    │   │   ├── cover_draft_1.jpg
    │   │   └── cover_final.jpg  ← 用户选定后复制到成片/cover.jpg
    │   └── 决策.md            ← 整体要求 + 用户新增
    └── 成片/
        ├── vlog_final.mp4     ← 模板工作流深度加工后
        └── cover.jpg          ← 最终封面（从粗加工/cover/cover_final.jpg 复制）
```

**AI 必读规则**：
- **不动源视频**：`video_*.mp4` 永远只读
- **唯一配置文件**：`intent.json` 跟源混居，其他 AI 文件全部进 `00_智剪/`
- **粗加工 5 类产物**：单视频/组合/文字稿/中间产物/cover/决策.md（v1.0 强制）
- **成片必须按 `project.title` 命名**：见 `references/AI路由表-意图JSON字段枚举.md` §B 项目级

---

## 🎬 阶段 0 ▸ 项目初始化（v1.3 强制）

```
0.1  AI 提示用户用 intent.html 填表
     (路径由用户在首问时提供；
      AI 必须主动用 shell 命令帮用户打开文件(如 Start-Process 或 xdg-open)，
      不得仅告知路径让用户自己找)
0.2  用户填表 → 生成 intent.json
0.3  用户把 intent.json 给 AI
0.4  [可选] 若 intent.json 缺失必填字段
       → AI 触发交互式采访补全
       → 不允许 AI 自己编默认值
```

**AI 必读规则**：
- **0.1 主动用 shell 打开**：Mavis/AI 必须用 `Start-Process`（Windows）/ `xdg-open`（Linux）/ `open`（macOS）帮用户打开 intent.html，**不得仅告知路径让用户自己找**（v1.3 强制）
- **0.4 缺失必填字段时必须问**：AI 不得自编默认值（v1.0 强制）
- 详细必填字段清单见 `references/AI交互式采访触发条件.md`

**后续阶段详见 `references/主流程-阶段编排.md`**（阶段 1-4 详细契约：输入/输出/跳过/异常/强制）

---

## 🧰 子技能索引（按维度分类，14 个）

**维度划分**：维度 = 技能大类，每个子技能都有 `references/XX-xxx.md` 详细文档。

| 维度 | 触发词 | 路由 | references |
|---|---|---|---|
| 01 cutting | 剪头/剪尾/裁切/分段/pin-range/cut-middle | `processing.py` / `video_trim.py` | `01-cutting.md`, `04-cut.md` |
| 02 transitions | 转场/淡入/擦除/滑动 | `video_xfade.py` | `02-transitions.md` |
| 03 effects | 调色/字幕/文字叠加 | `video_color.py` / `video_subtitle.py` / `video_opening.py` | `03-effects.md`, `05-color.md`, `06-text.md` |
| 04 cinematic | 推镜头/慢动作/倒放 | `processing.py` | `04-cinematic.md` |
| 05 image | 图片转视频/Ken Burns | **`image_to_video.py`**（v1.3 新增）| `05-image.md` |
| 06 text | 字幕/封面文字/数字人 | `video_subtitle.py` / `video_opening.py` | `06-text.md` |
| 07 audio | BGM/混音/淡入淡出/4 mode | `audio_bgm.py` | `07-audio.md` |
| 08 cover | 封面生成（ai/text/image）| `ai_cover.py` | `08-cover.md` |
| 09 ai-features | 美颜/磨皮/瘦脸/AI 增强 | `video_beauty.py` / `video_color.py` | `09-ai-features.md`, `12-beauty.md` |
| 10 batch | 批量剪辑/流水线 | 组合调用 | `10-batch.md` |
| 12 beauty | 美颜/磨皮/瘦脸/大眼 | `video_beauty.py` | `12-beauty.md` |
| 13 rewrite-audio | 改词/配音/换声/翻唱 | `video_rewrite.py` | `13-rewrite-audio.md` |
| 14 text-to-video | 文字成片/AI 生成视频 | `text_to_video.py` | `14-text-to-video.md` |
| 15 digital-human | 数字人/AI 讲解/虚拟人 | `digital_human.py` | `15-digital-human.md` |
| 16 edit | 旋转/缩放/裁剪/静音 | `edit.py` | `16-edit.md` |

**注意**：维度 11 不存在（v1.0 删了"智能封面"独立维度，并入 08 cover）。

---

## ⚙️ 通用参数（所有子技能共享）

| 参数 | 短选项 | 说明 |
|---|---|---|
| `--input` / `--video` | `-i` | 输入视频（部分脚本接受图片 / 音频）|
| `--output` | `-o` | 输出路径 |
| `--start` | — | 起始时间（秒）|
| `--duration` | — | 时长（秒，部分脚本支持）|

**所有原子 CLI 必须支持 `-h/--help`**，不确定时调 `--help` 看参数。

---

## 🤖 AI 协作协议（v1.2 强制，v1.3 修订）

### 1. 路由第一原则

**AI 拿到 intent.json / 用户需求后, 第一件事是查路由表**（`references/AI路由表-意图JSON字段枚举.md`）。

- 命中 → 调对应 atomic CLI
- 不命中 → F 象限（明确说"智剪工坊当前不支持 X"）

**禁止**: AI 不查表直接调 CLI / 凭印象调参 / 静默不支持的功能

### 2. AI 文本解析 → 路由表匹配 → 用户确认（E 象限，v1.3 改）

**自由文本字段**（`notes` / `overall_intent` / `ending.prompt` 等）必须先匹配路由表：

1. 读字段
2. 在路由表里找匹配
   - 匹配成功 → 用对应 CLI
   - 匹配失败 → **不假装支持**, 告诉用户"智剪工坊当前不支持 X"
3. **先告知用户匹配结果, 等用户确认再调 CLI**

**反例**: 用户说"加个转场", AI 直接默认 `fade` → 错
**正例**: 用户说"加个转场", AI 列出 9 种 type 让用户选 → 对

### 3. 模糊项 / 待澄清（D 象限, AI 必问）

AI 看到模糊需求时**必须问用户**, 不擅自决定。常见模糊:

- "想要动感" → 问: 配 BGM？转场？调色？速度？
- "视频太长了" → 问: 剪头剪尾？cut-middle？target-duration？
- "加滤镜" → 问: color preset 选哪个？
- "开头加段音乐" → 问: 什么音乐？音量多少？全段还是开头？

### 4. 速度范围 (speed-up / slow-down factor)

- `factor > 1.0` → 加速（如 2.0 = 2 倍速）
- `factor < 1.0` → 减速（如 0.5 = 半速）
- 推荐范围: 0.25 ~ 4.0（ffmpeg atempo 链能堆叠）

### 5. 时间字段解析规则 (pin-range / cut-middle / insert-image)

- `from` / `to` 接受 `HH:MM:SS` / `MM:SS` / `N分M秒` / `N分钟` / 纯数字
- `parse_time()` 自动识别（详见 `lib/processing.py`）

### 6. 序列（sequences）是**部分约束**, 不是全连接

- `sequences[i].videos` 强制该 sequence 内部的视频顺序
- 但**不强制** sequence 间的视频不重复
- AI 必须读 `project.overall_intent` 决定 sequence 间的拼接方式

### 7. 自动读版本文件 diff

新增/修改 atomic CLI 时, AI 必须:
1. 改 `scripts/<name>.py`
2. 同步改 `references/XX-xxx.md`
3. 在 `.archive/CHANGELOG.md` 加变更记录

### 8. 真实照片 vs 插画

**封面图 / 内容图**都用 `cover_ai.py` 或 `matrix_generate_image` **生成插画**, **不放真实照片**。

### 9. 新增 ops（v0.6+）

加新 op 必须:
1. 在 `lib/processing.py` 加 build filter
2. 加到 §G.1 video 级 ops 表
3. 在 §H 路由表加字段定义
4. 在 references/精剪-剪头剪尾保留段切中间.md 或新建 references/ 加详细文档

---

## ⚠️ AI 必读（v1.0 强制, v1.3 修订）

### 0. **AI 是编排者, 不是 step 脚本的调用者**（v1.3 关键变化）

- ❌ **不要**调 `pipeline_step*.py`（v1.3 已删 6 个 step 脚本）
- ✅ **要**直接调 atomic CLI（`scripts/video_*.py` / `scripts/audio_*.py` / `lib/processing.py`）

### 1. **触发锚点：选①时必读 references/主流程-阶段编排.md**

选①（从零开始做完整视频）→ **立即加载** `references/主流程-阶段编排.md`（主体流程骨架）

阶段 2-4 的具体步骤在 `references/主流程-阶段编排.md`，SKILL.md 只给总览。

### 2. **per-video 音频同步是必须, 不是可选**

`trim` / `pin-range` / `cut-middle` 后视频流 `setpts=PTS-STARTPTS` 归零了 PTS, **但音频流原始 PTS 范围未归零, 音画不同步**。必须同步 trim 音频并 `asetpts=PTS-STARTPTS`。

### 3. **video_normalize 是自动, 不是手动**

`process_video` 末尾自动调 `video_normalize`, 输出统一 30fps / yuv420p / aac 44100 stereo。

### 4. **ending.type 路由**（v1.3 修订）

| 值 | 路由 | 备注 |
|---|---|---|
| `fade` | `video_fade.py --fade-out N` | 视频结尾淡出 |
| `freeze` | `video_freeze.py --freeze N --padding-mode {clone\|black}` | 最后一帧定格 |
| `next-day` | `video_opening.py` + 黑屏源 | 黑屏 + 文字 |
| `text` | `video_subtitle.py` + srt | 烧结尾文字 |

### 5. **cover.type 路由**

| 值 | 路由 | 备注 |
|---|---|---|
| `ai`（推荐）| `ai_cover.py` | 按 cover.prompt AI 生图 |
| `text` | `ai_cover.py --text-only` | 纯文字封面 |
| `image` | （**当前不支持**）| 告诉用户"改用 ai 或 text" |

### 6. **B. project-level 操作**（v1.3 新增）

`output.bgm_match_mode` 路由到 `audio_bgm.py --match-mode <mode>`（4 种: loop/truncate/silence-end/ask）。

### 7. **C. sequence 约束**（v1.3 新增）

- 视频+图片混合 sequence: 图片必须先转视频（`image_to_video.py`）
- 转场 type 必须从 9 种 type 选
- `duration` 默认 0.5s, 建议 ≥ 0.5s

### 8. **D. 模糊项 / 待澄清**

详见上文"AI 协作协议"§3。

### 9. **E. AI 文本解析**

详见上文"AI 协作协议"§2。

### 10. **F. 未覆盖字段（out-of-scope）**

- 智剪工坊**不**做的事: 实时流剪辑 / 直播剪辑 / 复杂多轨音频混音
- 用户提这类需求 → 明确说"智剪工坊当前不支持, 推荐 XXX 工具"

---

## 📊 操作清单 schema（v1.0 强制, v1.3 修订）

**6 象限**（AI 阶段 1 必走, 作为阶段 2 执行契约）:

| 象限 | 内容 | 例子 |
|---|---|---|
| A. per-video 操作 | 每个视频单独处理 | trim-head / pin-range / cut-middle / color / fade-in / fade-out |
| B. project-level 操作 | 项目整体 | target-length / output.bgm / output.bgm_match_mode |
| C. sequence 约束 | 视频播放顺序 | sequences[].videos / sequences[].transitions |
| D. 模糊项 / 待澄清 | 必须问用户 | 动感是什么意思？滤镜哪个？ |
| E. AI 文本解析 | 自由文本 → 路由 | notes / overall_intent / ending.prompt |
| F. 未覆盖字段 | 明确说不支持 | 直播 / 多轨音频 / 实时 |

---

## 🎨 模板工作流

AI 阶段 3 按 yaml 模板编排（`模板/健身vlog.yaml` 等）。每模板含 4 stage:
1. **rhythm**（差异化节奏：开头慢、主体快、结尾慢）
2. **order**（时间线驱动：按 sequence 顺序拼）
3. **transitions**（统一转场策略：所有 segment 用同一种 type）
4. **data_overlay**（开头目标 + 结尾达成：基于 intent 字段）

**模板命名规则**: `<类别>vlog.yaml`（如 `健身vlog.yaml` / `教程vlog.yaml`）。

---

## 🔤 Jargon 大白话词典

| 用户说的 | 实际指 | 路由 |
|---|---|---|
| "剪头/剪尾" | trim-head / trim-tail | `processing.py` |
| "去掉中间" | cut-middle | `processing.py` |
| "保留某段" | pin-range | `processing.py` |
| "加转场" | sequences[].transitions | `video_xfade.py` |
| "加 BGM" | audio | `audio_bgm.py` |
| "配字幕" | subtitle | `video_subtitle.py` |
| "做封面" | cover | `ai_cover.py` |
| "调色" | color | `video_color.py` |
| "推镜头" | speed-up / cinematic-zoom | `processing.py` |
| "加文字" | opening-text / ending.text | `video_opening.py` / `video_subtitle.py` |
| **counter-rotate** | 像素反转（抵消 metadata）| `processing.py` 自动处理 |
| **aspect-fill / aspect-fit** | 填满 vs 加黑边 | `processing.py` |

---

## 📜 License

MIT（智剪工坊 © 2024-2026 帅猎羽）

---

## 🗂 目录结构

```
智剪工坊/
├── SKILL.md                      # 本文件
├── intent.html                   # 唯一前端（项目初始化）
├── references/                   # 19 个子技能文档
│   ├── 剪切拼接-帧级剪切与多段合并.md
│   ├── AI路由表-意图JSON字段枚举.md
│   ├── 转场-9种转场类型.md
│   ├── 视觉特效-慢动作推镜头模糊.md
│   ├── 主流程-阶段编排.md               # 选①必读（主体流程骨架）
│   ├── 电影感剪辑-变速倒放多机位.md
│   ├── 精剪-剪头剪尾保留段切中间.md
│   ├── 调色预设-18种预设LUT风格迁移.md
│   ├── 图片转视频-静态图KenBurns效果.md
│   ├── 字幕文字-Whisper烧字幕片头变声.md
│   ├── 音频配乐-BGM循环淡入淡出节拍.md
│   ├── AI封面-生图叠字两步法.md
│   ├── AI智能剪辑-抠图金句去水词蒙版.md
│   ├── 批量处理-多视频统一操作.md
│   ├── 美颜-四种人脸美化.md
│   ├── 改词翻唱-文案改写TTS替换音轨.md
│   ├── 文字成片-mmx免key生成6秒片段.md
│   ├── 数字人-AI主播头像说话.md
│   └── 原子操作-14种基础剪辑指令.md
├── scripts/                      # 30+ 个原子 CLI
│   ├── video_*.py
│   ├── audio_*.py
│   ├── image_to_video.py         # v1.3 新增
│   └── ...
├── lib/                          # 共享逻辑
│   ├── common.py                 # ffmpeg + 错误 + 日志 + safe_run
│   ├── processing.py             # 视频滤镜 + 转场 + rotation
│   ├── filename.py               # v1.3 新增
│   └── ...
├── 模板/                         # AI 阶段 3 编排模板
│   └── 健身vlog.yaml
└── .archive/                     # 开发者面向（AI 不读）
    ├── CHANGELOG.md
    ├── HANDOFF.md
    └── ...
```

---

## 📅 版本

- **v1.3**（2026-07）：AI 编排 + 路由表 + 11 个优化（详见 `.archive/CHANGELOG-v1.3.md`）
- v1.2（2026-06）：精简 step 脚本 + 操作清单 schema
- v1.0（2026-05）：阶段 0-4 端到端
- v0.7（2026-04）：早期版本
