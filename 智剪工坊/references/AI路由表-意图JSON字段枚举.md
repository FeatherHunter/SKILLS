# AI路由表 - 意图JSON字段枚举

> **何时加载**: AI 读 intent.html / intent.json 后,开始 §阶段 1 字段解析时
> **目的**: 列出所有字段的可选值,AI 看到非法值必须问用户（不要瞎猜）

---

## 1. intent.json 字段枚举表（AI 必读）

**目的**: intent.json 各字段的可选值是枚举。AI 看到非法值必须问用户（不要瞎猜）。

| 字段 | 路径 | 类型 | 可选值 / 格式 | AI 必读说明 |
|---|---|---|---|---|
| `version` | 顶层 | string | `"v0.5"` / `"v1.0"` / `"v1.2"` | schema 版本，AI 不修改 |
| `_meta.revision` | 顶层 | int | `1`, `2`, `3`... | intent.json 修订号，每次保存 +1 |
| `project.name` | 顶层 | string | 任意 | vlog 项目名（"DAY 2 减脂日记"） |
| `project.title` | 顶层 | string | 任意 | vlog 成片最终标题（成片文件名来源,例 "DAY 2 减脂日记" → `DAY_2_减脂日记.mp4`） |
| `project.overall_intent` | 顶层 | string | 任意自然语言 | E 象限：AI 文本解析 → 路由表匹配 → 用户确认 |
| `project.target_length` | 顶层 | int | **秒** | 目标时长（如 `180` = 3 分钟） |
| `output.aspect_ratio` | 顶层 | string | `"9:16"` / `"16:9"` / `"1:1"` / `"4:3"` / `"custom"` | 输出宽高比 |
| `output.aspect_ratio_custom` | 顶层 | string | `"W:H"`（自定义比例） | aspect_ratio="custom" 时必填 |
| `output.aspect_handling` | 顶层 | string | `"aspect-fill"` / `"aspect-fit"` | 比例处理：填满 vs 加黑边 |
| `output.fps` | 顶层 | int | **默认 30**（v1.3 写死，html UI 暂不允许配置） | 输出帧率（v1.3 默认 30，未来启用 html UI 可配） |
| `output.video_codec` | 顶层 | string | **默认 `h264`**（v1.3 写死） | 视频编码 |
| `output.audio_codec` | 顶层 | string | **默认 `aac`**（v1.3 写死） | 音频编码 |
| `output.audio_sample_rate` | 顶层 | int | **默认 44100**（v1.3 写死） | 音频采样率 |
| `output.audio_channels` | 顶层 | int | **默认 2**（v1.3 写死） | 音频声道数（1=mono, 2=stereo） |
| `output.pixel_format` | 顶层 | string | **默认 `yuv420p`**（v1.3 写死） | 像素格式（兼容性最好） |
| `output.bgm_match_mode` | 顶层 | string | `loop` / `truncate` / `silence-end` / `ask`（**默认 `loop`**） | v1.3 新增：BGM 与视频时长不匹配时的处理策略 |
| `cover.type` | 顶层 | string | `"ai"` / `"text"` / `"image"` | 封面生成方式（推荐 `"ai"`） |
| `cover.prompt` | 顶层 | string | 英文 prompt 优先 | AI 生图 prompt（参考 `references/AI封面-生图叠字两步法.md`） |
| `ending.type` | 顶层 | string | `"fade"` / `"freeze"` / `"next-day"` / `"text"` | 结尾风格（详见下方 ending.type 路由说明） |
| `ending.prompt` | 顶层 | string | 英文/中文 | 结尾文字 / 主题（参考 §阶段 4 模板） |
| `videos[i].file` | 数组 | string | 文件名（如 `"video_01.mp4"`） | 源视频相对路径 |
| `videos[i].voice` | 数组元素 | string | `keep` / `keep-with-filler-removed` / `mute` / `bgm-only` / `original-with-bgm` | 音轨处理策略：保留 / 保留并去水词 / 静音 / 只留 BGM / 原声+BGM混合 |
| `videos[i].ops` | 数组 | object | 见 §G. op 白名单 | 每个视频的操作（多个 op 可组合） |
| `videos[i].notes` | 数组 | string | 任意自然语言 | E 象限：AI 文本解析 → 路由表匹配 → 用户确认 |
| `sequences[i].videos` | 数组 | string[] | 文件名列表（顺序敏感） | 强制播放顺序（必须在 sequence 内） |
| `sequences[i].transitions` | 数组 | object[] | `{after, type, duration}` 列表 | sequence 内部转场（每段之间） |
| `sequences[i].transitions[j].after` | 数组元素 | int | video index | 表示"在 index 这段之后"的转场 |
| `sequences[i].transitions[j].type` | 数组元素 | string | `none` / `cut` / `fade` / `dissolve` / `wipe-left` / `wipe-right` / `slide-up` / `zoom-in` / `blur` | 9 种意图 type，详见 §G.2 |
| `sequences[i].transitions[j].duration` | 数组元素 | float | `≥0.5` 秒，默认 `0.5` | 转场时长 |
| `sequences[i].photos[i].file` | 数组 | string | 文件名 | v1.3 新增：图片素材文件名（.jpg/.png/.webp/.bmp） |
| `sequences[i].photos[i].duration` | 数组 | float | **秒**，默认 `3.0` | v1.3 新增：图片作为片段的时长（默认 3 秒） |
| `sequences[i].photos[i].effect` | 数组 | string | `static` / `ken-burns-in` / `ken-burns-out`，默认 `static` | v1.3 新增：Ken Burns 效果（命名用 ken-burns 前缀避免和 transitions[].type='zoom-in' 混淆） |

## 2. 路由表（AI 必读, 字段 → atomic CLI）

| intent.json 路径 | atomic CLI | 触发条件 | 参数语义 |
|---|---|---|---|
| `videos[i].ops.trim-head` | `video_trim.py` | `on=true` | `{on: bool, sec: 数字}` |
| `videos[i].ops.trim-tail` | `video_trim.py` | `on=true` | `{on: bool, sec: 数字}` |
| `videos[i].ops.pin-range` | `video_trim.py` | `on=true` | `{on: bool, from: "HH:MM:SS", to: "HH:MM:SS"}`（**v1.3 multi-range**: `ranges: [{from, to}, ...]`）|
| `videos[i].ops.cut-middle` | `video_trim.py` | `on=true` | `{on: bool, from: "HH:MM:SS", to: "HH:MM:SS"}`（**v1.3 multi-range**: `ranges: [{from, to}, ...]`）|
| `videos[i].ops.speed-up` | `video_speed.py` | `on=true, factor>1` | `{on: bool, factor: float}` |
| `videos[i].ops.slow-down` | `video_speed.py` | `on=true, factor<1` | `{on: bool, factor: float}` |
| `videos[i].ops.reverse` | `video_reverse.py` | `on=true` | `{on: bool}` |
| `videos[i].ops.mute` | `audio_bgm.py --video-volume 0` | `on=true` | `{on: bool}`（用 voice='mute'）|
| `videos[i].ops.fade-in` | `video_fade.py` | `on=true` | `{on: bool, sec: 数字}` |
| `videos[i].ops.fade-out` | `video_fade.py` | `on=true` | `{on: bool, sec: 数字}` |
| `videos[i].ops.opening-text` | `video_opening.py` | `on=true` | `{on: bool, text: str, duration: 秒, region: str}` |
| `videos[i].ops.insert-image` | `video_overlay.py` | `on=true` | `{on: bool, file: path, at: 秒, duration: 秒}` |
| `videos[i].ops.color` | `video_color.py` | `on=true` | `{on: bool, preset: str}`（13 种预设: warm/cool/cinematic/vintage/bw/high-contrast/noir/comic/sketch/faded/punchy/vhs/dream/sharpen）|
| `videos[i].ops.rotate` | `edit.py rotate` | `on=true` | `{on: bool, degrees: int}`（90/180/270）|
| `videos[i].ops.scale` | `edit.py scale` | `on=true` | `{on: bool, width: int, height: int}` |
| `videos[i].ops.crop` | `edit.py crop` | `on=true` | `{on: bool, x: int, y: int, width: int, height: int}` |
| `videos[i].ops.subtitle` | `video_subtitle.py` | `on=true` | `{on: bool, style: str, language: str}`（中文/英文/auto）|
| `videos[i].ops.audio` | `audio_bgm.py` | `on=true` | `{on: bool, file: path, volume: float, start: 秒, end: 秒, bgm_fade_in: 秒, bgm_fade_out: 秒, match_mode: str}`（match_mode v1.3 新增，4 种: loop/truncate/silence-end/ask）|
| `videos[i].ops.target-duration` | `processing.py` | `on=true` | `{on: bool, sec: 数字}`（成片时长上限）|
| `sequences[i].photos[i]` | `image_to_video.py` | **v1.3 新增** | `{file: path, duration: 秒, effect: static/ken-burns-in/ken-burns-out}` |
| `sequences[i].transitions[j]` | `video_xfade.py` | type≠none/cut | `{after: int, type: 9 种, duration: 秒}` |
| `sequences[i].transitions[j]` | `concatenate_simple` (硬切) | type=none/cut | 同上 |

**多个 op 在同一视频上**: AI 串联调多次 CLI,或 import `lib/processing.py` 用 `build_video_filter()` 一次拼。

## 3. ending.type 路由（阶段 4，AI 必读）

| 值 | 路由 | 备注 |
|---|---|---|
| `fade` | `video_fade.py --fade-out N` | atomic CLI：视频结尾淡出 + 音轨淡出 |
| `freeze` | `video_freeze.py --freeze N --padding-mode {clone\|black}` | atomic CLI：最后一帧定格 N 秒（clone=克隆 / black=黑屏）|
| `next-day` | `video_opening.py` + 黑屏源视频 | atomic CLI：黑屏 + "DAY N+1 即将开始" 文字 |
| `text` | `video_subtitle.py` + srt | atomic CLI：烧结尾文字 |

## 4. cover.type 路由（阶段 4，AI 必读）

| 值 | 路由 | 备注 |
|---|---|---|
| `ai`（推荐）| `ai_cover.py` | atomic CLI：按 cover.prompt AI 生图 |
| `text` | `ai_cover.py --text-only` | atomic CLI：纯文字封面（v1.3 已支持 `cover/cover_text.py` 子目录）|
| `image` | （**当前不支持**）| AI 必须告知用户"当前不支持 type=image，请改用 ai 或 text" |

**`cover.type='image'` 当前不支持**（intent.html 没字段承载图片路径）—— AI 必须告知用户"当前不支持 type=image，请改用 ai 或 text"。

## 5. AI 文本解析 → 路由表匹配 → 用户确认（E 象限, v1.3 改）

**关键原则**: 自由文本字段（`notes` / `overall_intent` / `ending.prompt` 等）必须先匹配路由表：

1. **读**: AI 读 `videos[i].notes` / `project.overall_intent`
2. **匹配**: AI 在路由表里找匹配
   - 匹配成功: 用对应 CLI 处理
   - 匹配失败: **不假装支持**,明确告诉用户"智剪工坊当前不支持 X"
3. **确认**: AI 必须**先告知用户**匹配结果,等用户确认再调 CLI

**反例**: 用户说"加个转场", AI 直接默认 `fade` → 错（用户可能想要 `zoom-in`）
**正例**: 用户说"加个转场", AI 列出 9 种 type 让用户选 → 对

## 6. 字段不在表里怎么办?

- 看对应子技能 references 的 §调用范式 + §参数 段——所有字段都有出处（如 audio 字段查 `音频配乐-BGM循环淡入淡出节拍.md`）
- AI 路由时**严格按 op 白名单**调 CLI（不要瞎传参）
- 字段没 op 对应 → F 象限（明确说"这个字段我不处理"）

## 7. 模糊项 / 待澄清（D 象限, AI 必读）

AI 看到模糊需求时**必须问用户**,不擅自决定。常见模糊:

- "想要动感" → 问：配 BGM？转场？调色？速度？
- "视频太长了" → 问：剪头剪尾？cut-middle？target-duration？
- "加滤镜" → 问：color preset 选哪个？
- "开头加段音乐" → 问：什么音乐？音量多少？全段还是开头？

## 8. 相关参考

- **SKILL.md §AI 协作协议**: 路由总规则
- **SKILL.md §阶段 1**: 解析 intent 流程
- **references/主流程-阶段编排.md**: 阶段 2-4 详细编排
