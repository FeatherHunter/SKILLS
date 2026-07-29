# AI路由表 - 意图JSON字段枚举

> **何时加载**: AI 读 智剪工坊-意图编辑.html / intent.json 后,开始 §阶段 1 字段解析时
> **目的**: 列出所有字段的可选值,AI 看到非法值必须问用户（不要瞎猜）

---

## 1. intent.json 字段枚举表（AI 必读）

**目的**: intent.json 各字段的可选值是枚举。AI 看到非法值必须问用户（不要瞎猜）。

| 字段 | 路径 | 类型 | 可选值 / 格式 | AI 必读说明 |
|---|---|---|---|---|
| `_meta.schema_version` | `_meta` 下 | string | **`"3.0"`(D1 强制)** | JSON 协议版本(D1)。AI 解析时凭它决定用 v3.0 schema 解析逻辑。**缺失或非 `"3.0"` = 报错**(D4) |
| `_meta.tool_version` | `_meta` 下 | string | 字符串(如 `"2.135"`)(D1 可选) | HTML 编辑器产品版本号(D1)。**与 schema_version 区分**——前者是产品发布号,后者是契约号 |
| `_meta.revision` | `_meta` 下 | int | `1`, `2`, `3`... | intent.json 修订号,每次保存 +1 |
| `_meta.workspace` | `_meta` 下 | string | 文件夹名 | 工作区名称 |
| ~~`_meta.history[]`~~ | ~~已删除(D5)~~ | — | ~~不存在~~ | 无消费者、spec 不要求、自引用陷阱。审计走 `.scratch/` 而非 intent.json 自指 |
| `project.name` | 顶层 | string | 任意 | vlog 项目名("DAY 2 减脂日记") |
| `project.title` | 顶层 | string | 任意 | vlog 成片最终标题(成片文件名来源) |
| `project.overall_intent` | 顶层 | string | 任意自然语言 | E 象限:AI 文本解析 → 路由表匹配 → 用户确认 |
| `project.target_length` | 顶层 | int | **秒** | 目标时长(如 `180` = 3 分钟) |
| `output.aspect_ratio` | 顶层 | string | `"9:16"` / `"16:9"` / `"1:1"` / `"3:4"` / `"4:3"` / `"custom"` | 输出宽高比 |
| `output.aspect_ratio_custom` | 顶层 | string | **`"W:H"` 格式(D1)** | aspect_ratio="custom" 时必填 |
| `output.aspect_handling` | 顶层 | string | `"aspect-fit"` / `"aspect-fill"` | 比例处理:加黑边 vs 旋转填满 |
| `output.fps` | 顶层 | int | **默认 30**(v1.3 写死) | 输出帧率 |
| `output.video_codec` | 顶层 | string | **默认 `h264`** | 视频编码 |
| `output.audio_codec` | 顶层 | string | **默认 `aac`** | 音频编码 |
| `output.bgm_match_mode` | 顶层 | string | `loop` / `truncate` / `silence-end` / `ask`(默认 `loop`) | BGM 与视频时长不匹配时的处理策略 |
| `cover.type` | 顶层 | string | **`"ai"` / `"text"` / `"image"`(D1 扩到 3)** | 封面生成方式。`image` 路由到 `cover_compose/`(见 §4) |
| `cover.prompt` | 顶层 | string | 英文 prompt 优先 | AI 生图 prompt(参考 `references/AI封面-生图叠字两步法.md`) |
| `cover.images[]` | `cover` 下 | string[] | 图片路径列表(D1 新增) | **仅 `cover.type="image"` 时必填**。多图拼版素材 |
| `ending.template` | 顶层 | string | **必填(D2)** | HTML 选中的效果模板完整描述文本(人话)。AI 按 §5 E 象限文本路由 |
| `ending.prompt` | 顶层 | string | 可选(D2) | 用户的额外补充说明 |
| ~~`ending.type`~~ | ~~已删除(D2)~~ | — | ~~不存在 enum~~ | V4 重构:抛弃 6 选 1 enum,改 `template` + `prompt` 两文本字段。详见 §5 |
| `videos[i].file` | 数组 | string | 文件名(如 `"video_01.mp4"`) | 源视频相对路径 |
| `videos[i].index` | 数组 | int | 1-based | 1-based stable ID,跨工单引用锚点 |
| `videos[i].duration_sec` | 数组 | number | 秒 | 视频时长(HTML 加载时算出) |
| `videos[i].video_ops` | 数组 | object | 见 §2 路由表 | 整段视频 op(D1:替代原 `ops` 平铺) |
| `videos[i].video_ops.voice.mode` | 数组 | string | `keep` / `keep-with-filler-removed` / `mute` / `bgm-only` | 音轨处理策略(D1:从原 `voice` 顶层移到 video_ops) |
| `videos[i].video_ops.voice_note` | 数组 | string | 任意 | 音轨补充说明 |
| `videos[i].video_ops.notes` | 数组 | string | 任意自然语言 | 视频整体备注 |
| `videos[i].time_segments[]` | 数组 | object | 见 §2 段内 op | 片段保留(可空 = 整段保留) |
| `videos[i].time_segments[].ops` | 数组 | object | `mute` / `speed-up` / `slow-down` / `reverse` / `color-grade`(白名单) | 段内 op。**不在白名单 = 报错**(HTML `validateIntent` 拒绝) |
| ~~`videos[i].ops` 平铺 22 op~~ | ~~已废弃(D7)~~ | — | ~~不存在~~ | D7:22 个 op 已迁入 `video_ops` 顶层或 `time_segments[].ops`,5 个该消失的 op(`trim-head`/`trim-tail`/`cut-middle`/`pin-range`/`target-duration`)完全删除 |
| `sequences[i].videos` | 数组 | int[] | entry.index 序列(D1:从 string[] 改为 int[]) | 强制播放顺序 |
| `sequences[i].transitions` | 数组 | object[] | `{after, type, duration}` 列表 | sequence 内部转场 |
| `sequences[i].transitions[j].after` | 数组元素 | int | video.index | 表示"在 index 这段之后"的转场 |
| `sequences[i].transitions[j].type` | 数组元素 | string | 9 种意图 type(`fade`/`fade-black`/`fade-white`/`wipe-left`/`wipe-right`/`slide-up`/`zoom-in`/`blur`/`none`) | 转场类型 |
| `sequences[i].transitions[j].duration` | 数组元素 | float | `≥0.1` 秒,默认 `0.5` | 转场时长 |

## 2. 路由表(AI 必读, 字段 → atomic CLI)

> **2026-07-29 修订(D7)**:以下 5 个该消失的 op **已从 schema 删除**,语义改由 `time_segments` 边界表达。**AI 不要再路由它们**:
> - `trim-head` ≡ `time_segments[0].start_sec = sec`
> - `trim-tail` ≡ `time_segments[last].end_sec = duration_sec - sec`
> - `cut-middle` / `pin-range` ≡ 创建对应 time_segments
> - `target-duration` ≡ 拼接后时长 = 各段相加
>
> **路径前缀说明**:v3.0 schema 下,op 在 **`videos[i].video_ops.<op>`**(整段)或 **`videos[i].time_segments[j].ops.<op>`**(段内)。

| intent.json 路径(D7 修订) | atomic CLI | 触发条件 | 参数语义 |
|---|---|---|---|
| `videos[i].video_ops.speed-up` | `video_speed.py` | `on=true, factor>1` | `{on: bool, factor: float}` |
| `videos[i].video_ops.slow-down` | `video_speed.py` | `on=true, factor<1` | `{on: bool, factor: float}` |
| `videos[i].video_ops.reverse` | `video_reverse.py` | `on=true` | `{on: bool}` |
| `videos[i].video_ops.mute` | `audio_bgm.py --video-volume 0` 或 `video_ops.voice.mode='mute'` | `on=true` | `{on: bool}` |
| `videos[i].video_ops.fade-in` | `video_fade.py` | `on=true` | `{on: bool, sec: 数字}` |
| `videos[i].video_ops.fade-out` | `video_fade.py` | `on=true` | `{on: bool, sec: 数字}` |
| `videos[i].video_ops.opening-text` | `video_opening.py` | `on=true` | `{on: bool, text: str, duration: 秒}` |
| `videos[i].video_ops.insert-image` | `video_overlay.py` | `on=true` | `{on: bool, file: path, at: 秒, duration: 秒}` |
| `videos[i].video_ops.color` | `video_color.py` | `on=true` | `{on: bool, preset: str}`(13 种预设) |
| `videos[i].video_ops.asr-transcribe` | `asr/transcribe.py` | `on=true` | `{on: bool, model: tiny/base/small/medium/large-v3, lang: zh/en/auto}` |
| `videos[i].video_ops.asr-burn` | `asr/burn_subtitle.py` | `on=true` | `{on: bool, font_size: 数字, 默认 22}` |
| `videos[i].video_ops.asr-speaker` | `asr/speaker_srt.py` | `on=true` | `{on: bool}`(前提 asr-transcribe + audio-diarize) |
| `videos[i].video_ops.audio-denoise` | `audio/denoise.py` | `on=true` | `{on: bool}` |
| `videos[i].video_ops.audio-separate` | `audio/separate.py` | `on=true` | `{on: bool, model: htdemucs/htdemucs_ft/mdx_q}` |
| `videos[i].video_ops.audio-diarize` | `audio/diarize.py` | `on=true` | `{on: bool}`(需 HF token) |
| `videos[i].video_ops.voice-filler-removed` | **`ai/fillers.py`(2026-07-29 已实装)** | `on=true` | `{on: bool}` |
| `videos[i].video_ops.add-bgm` | `audio/mix.py` | `on=true` | `{on: bool, file: path, volume: 0-2, match_mode: loop/truncate/silence-end/ask}` |
| `videos[i].video_ops.replace-audio` | `audio/mix.py` | `on=true` | `{on: bool, file: path}` |
| `videos[i].video_ops.duration` | `image_to_video.py` | `on=true`(图片专属) | `{on: bool, sec: 数字}` |

**段内 op(白名单)** —— 必须在 `videos[i].time_segments[j].ops` 下:

| intent.json 路径 | atomic CLI | 触发条件 | 参数语义 |
|---|---|---|---|
| `videos[i].time_segments[j].ops.mute` | `audio_bgm.py --video-volume 0` | `on=true` | `{on: bool}` |
| `videos[i].time_segments[j].ops.speed-up` | `video_speed.py` + `trim` | `on=true, factor>1` | `{on: bool, factor: float}`(应用到该段) |
| `videos[i].time_segments[j].ops.slow-down` | `video_speed.py` + `trim` | `on=true, factor<1` | `{on: bool, factor: float}` |
| `videos[i].time_segments[j].ops.reverse` | `video_reverse.py` + `trim` | `on=true` | `{on: bool}` |
| `videos[i].time_segments[j].ops.color-grade` | `video_color.py` + `trim` | `on=true` | `{on: bool, preset: str}` |

**不在白名单的段内 op** = 校验拒绝(HTML `validateIntent` + JSON Schema)。常见误用:
- `color` (无 `-grade` 后缀) → 拒绝,应改为 `color-grade`
- `user` (HTML 拆段内部标记) → 拒绝,不应出现
- 其他(opening-text 等) → 拒绝,应改在 `video_ops` 顶层

**多个 op 在同一视频上**:AI 串联调多次 CLI,或 import `lib/video_processing.py` 用 `build_video_filter()` 一次拼。

**sequence 与 ending 不再走 §2 路由**(已迁移到 §5):见 §3 ending 文本路由 + §5 E 象限。

**其它不再路由的旧字段**:
- ~~`videos[i].ops` 平铺 22 op~~ → 已废弃,迁移到 video_ops / time_segments[].ops
- ~~`videos[i].voice` 顶层 string~~ → 已移到 `videos[i].video_ops.voice.mode`
- ~~`videos[i].notes` 顶层 string~~ → 已移到 `videos[i].video_ops.notes`
- ~~`videos[i].voice_note` 顶层 string~~ → 已移到 `videos[i].video_ops.voice_note`
- ~~`videos[i].rotate` / `videos[i].scale` / `videos[i].crop`~~ → v3.0 未列入 `video_ops`,留待后续工单决定
- ~~`videos[i].subtitle` / `videos[i].audio`~~ → 同上
- ~~`sequences[i].photos[i]`~~ → v3.0 不再走独立 photos 路径,改由 `time_segments` 表达
- ~~`videos[i].ops.target-duration`~~ → D7 已废弃

## 3. ending 文本路由(阶段 4, AI 必读 · D2 V4 重构)

> **2026-07-29 重大变更**:不再有 `ending.type` enum。`ending` 字段由两个文本字段构成:
> - `ending.template`(**必填**)—— HTML 选中的效果模板完整描述文本
> - `ending.prompt`(**可选**)—— 用户补充说明

**AI 处理流程**:

1. **读 `ending.template`**(必读)
2. **读 `ending.prompt`**(可选,补充)
3. **用 §5 E 象限文本路由规则** 把 template + prompt 翻译为执行步骤
4. **典型模板语义分类**(仅供 AI 参考,不是 enum):

| template 含... | 推荐 CLI |
|---|---|
| 「淡出」「渐弱」「BGM 渐弱」 | `video_fade.py --fade-out N` + `audio/mix.py --bgm-fade-out` |
| 「定格」「末帧停留」 | `video_freeze.py --freeze N` |
| 「切黑」「黑屏」 | `video_freeze.py --padding-mode black` |
| 「烧字」「字幕打」「文字停留」 | `asr/burn_subtitle.py` 或 `video_opening.py add` |
| 「下期」「明天见」「预告」 | `video_opening.py add`(黑屏源 + 文字) |
| 「倒计时」 | 多段 `video_opening.py add`(数字 5-4-3-2-1) |
| 「口播」「声音说」 | `audio/mix.py`(叠加口播音频层) |
| 「BGM 渐弱 + 黑屏 + 烧字」 | 串联上述多个 CLI |

**反例**(AI 必避):
- ❌ 不再读 `ending.type` 字段 —— **该字段已不存在**
- ❌ 不再"fallback 到 `next-day`" —— 不存在 fallback 概念
- ❌ 不手写 ffmpeg drawtext 命令 —— 踩转义陷阱,用 `video_opening.py add` 替代
- ❌ 看到 `ending.template` 就直接复制整个文本到视频 —— **AI 必须解析语义,选 CLI**

**特殊字符处理**:
- `\n` → 用 ffmpeg textfile + 多 drawtext,或多段 drawtext
- emoji / 繁体 / 特殊符号 → 用 `escape_drawtext()`(`video_opening.py` 已实现)

## 4. cover.type 路由(阶段 4, AI 必读 · D1 修订)

| 值 | 路由 | 备注 |
|---|---|---|
| `ai`(推荐) | `scripts/ai/cover.py` + `cover.prompt` | atomic CLI:按 `cover.prompt` AI 生图。详见 `references/AI封面-生图叠字两步法.md` |
| `text` | `scripts/ai/cover.py --text-only` | atomic CLI:纯文字封面 |
| `image` | **`scripts/ai/cover_compose/`(D1 实装)** | 多图拼版。**必须**有 `cover.images[]` 字段(D1)。详见 `references/封面合成-多图拼版PIL.md` |

**`cover.type='image'`**(2026-07-29 修订) ~~当前不支持~~ → **已实装**:
- HTML 编辑器已增加 `<select>` 的 `image` 选项(D1)
- HTML 编辑器已增加 `cover.images[]` 多图上传器
- AI 看到 `cover.type='image'` 时,**必须**读 `cover.images[]` 取图片路径列表
- 缺 `cover.images[]` = 校验失败(HTML `validateIntent` + JSON Schema 都拒绝)

## 5. AI 文本解析 → 路由表匹配 → 用户确认(E 象限, v1.3 改 · D2 强化)

**关键原则**: 自由文本字段(`videos[i].video_ops.notes` / `project.overall_intent` / **`ending.template` + `ending.prompt`** 等)必须先匹配路由表:

1. **读**: AI 读 `videos[i].video_ops.notes` / `project.overall_intent` / **`ending.template` + `ending.prompt`**
2. **匹配**: AI 在路由表里找匹配
   - 匹配成功: 用对应 CLI 处理
   - 匹配失败: **不假装支持**,明确告诉用户"智剪工坊当前不支持 X"
3. **确认**: AI 必须**先告知用户**匹配结果,等用户确认再调 CLI

**ending 是典型 E 象限场景**(2026-07-29 强化,D2):
- `ending.template` 是用户选中的效果模板完整描述文本(人话)
- `ending.prompt` 是用户补充说明
- AI **必须把 template + prompt 解析为 CLI 步骤**,不能直接复制到视频
- **典型示例**:
  - template="BGM 渐弱到静音,画面同步淡出" → `video_fade.py --fade-out N` + `audio/mix.py --bgm-fade-out`
  - template="切黑屏后烧『下期见』停留 3 秒" → `video_freeze.py --padding-mode black` + `video_opening.py add`
  - template="倒计时数字 5-4-3-2-1" → 多次 `video_opening.py add`(分段烧数字)

**反例**: 用户说"加个转场", AI 直接默认 `fade` → 错(用户可能想要 `zoom-in`)
**正例**: 用户说"加个转场", AI 列出 9 种 type 让用户选 → 对

**反例(新增,ending 场景)**: template="BGM 渐弱", AI 直接在视频最后贴一行"BGM 渐弱" 文字 → 错(应解析为音频淡出 + 视频淡出)
**正例(新增)**: template="BGM 渐弱", AI 推荐 `video_fade.py --fade-out 5` + `audio/mix.py --bgm-fade-out 5`,等用户确认后执行

## 6. 字段不在表里怎么办?

- 看对应子技能 references 的 §调用范式 + §参数 段——所有字段都有出处（如 audio 字段查 `音频配乐-BGM循环淡入淡出节拍.md`）
- AI 路由时**严格按 op 白名单**调 CLI（不要瞎传参）
- 字段没 op 对应 → F 象限（明确说"这个字段我不处理"）

## 7. 模糊项 / 待澄清（D 象限, AI 必读）

AI 看到模糊需求时**必须问用户**,不擅自决定。常见模糊:

- "想要动感" → 问：配 BGM？转场？调色？速度？
- "视频太长了" → 问：保留哪几段(time_segments 框选)？还是删掉首尾(time_segments 边界)?
- "加滤镜" → 问：color preset 选哪个？
- "开头加段音乐" → 问：什么音乐？音量多少？全段还是开头？

## 8. 相关参考

- **SKILL.md §AI 协作协议**: 路由总规则
- **SKILL.md §阶段 1**: 解析 intent 流程
- **references/主流程-阶段编排.md**: 阶段 2-5 详细编排
