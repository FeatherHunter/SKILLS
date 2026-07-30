# 智剪工坊 · CONTEXT.md

> 本文件是仓库的**单一上下文源**。所有工程类技能(grill-with-docs / to-spec / implement / code-review)开始前必须先读此文件。
> 它定义的术语是项目内**唯一的事实**。

---

## 项目定位

**智剪工坊** 是一个本地运行的视频剪辑工作台。对标剪映(图形化)+ 扩展(AI 能力)。

**核心资产**:
- `智剪工坊-意图编辑.html` — 浏览器端用户编辑器(Layer 3)
- `intent.json` — 编辑器产出的 JSON 协议(Layer 1)
- `references/` `SKILL.md` — **人类语言描述**的 AI 操作契约(Layer 2A)
- `scripts/` `lib/` — **机器执行**的 atomic CLI + 编排(Layer 2B)
- `_archive/` — 旧 superpowers 技能流产物(已归档)

---

## Language(术语)

### 资产分层术语

**Layer 1 · 协议(JSON)**
intent.json 字段结构与字段语义的权威蓝图。本次重构目标:三层(Layer 1/2A/2B/3)产出与消费对齐。

**Layer 2 · 语义层**
SKILL 的"语义"部分,人类语言 + 机器实现并列:
- **Layer 2A**(md 文档):AI 解析时的真实契约,人也能读。
- **Layer 2B**(Python 代码):机器执行的编排。

**Layer 3 · 编辑器**
`智剪工坊-意图编辑.html` 浏览器端编辑器。负责产出 Layer 1 JSON,消费 Layer 2A 的 UX 指引。

_Avoid_: 把 Layer 2A 和 Layer 2B 视为同质——md 是契约,Python 是实现,两者必须对齐但不是同一个东西。

### 重构迭代术语

**v2.0 数据 + v3.0 HTML 行为**:
v2.0 是 intent.json 数据结构的版本号。v3.0 是 HTML 编辑器行为的版本号。
_Avoid_: 文档里谈"v3"含糊指代。

**intent.json**:
浏览器编辑后保存的 JSON 协议文件,作为 AI 流水线的输入契约。命名固定 `intent.json`(workspace 根目录)。
_Avoid_: 翻译成"意图文档"/"剪辑描述"——前者用了文档领域词,后者用了业务领域词,不如直用文件名。

**spec**:
intent.json 字段结构与字段语义的权威蓝图。
_Avoid_: spec 与代码/HTML 不一致时,不要默认"代码改就好"——spec 本身也可能在迭代。

**路由表(AI 路由表)**:
`references/AI路由表-意图JSON字段枚举.md` 中列出的字段枚举值与 atomic CLI 映射表。AI 解析 intent.json 时凭它判断合法值。
_Avoid_: 与 spec 混淆。spec 是数据契约蓝图;路由表是 AI 运行时白名单。

### 重构期间的核心决策术语

**v3.0 双字段分离(videos[].video_ops + videos[].time_segments)**:
intent.json 的 `videos[]` 下,操作分两类存放。
- `video_ops`:对整段视频生效的 op(与时间窗无关)。
- `time_segments[].ops`:对某具体时间区间生效的 op(段内 op)。

_Avoid_: 把"段内 op"塞回 `video_ops`、把"整段 op"塞到段内——这是本次要修的偏移。

**段(segment)**:
一个**具体时间区间**(由 `start_sec`/`end_sec` 界定)。是用户用 timeline 框选产生的几何单位。
_Avoid_: 把"段"等同于"视频"或"剪过的视频"。

**op(operation)**:
对视频或段做的一件事。多个 op 可叠加。op 有两种作用域:
- **整段型**(video_ops 顶层):影响整段视频,与时间无关。
- **段内型**(time_segments[].ops):只对某个段生效。

_Avoid_: 概念混用导致代码嵌套 switch-case。

**消失的 op**:
本次重构**不再出现在 intent.json 中的 op**:`trim-head`、`trim-tail`、`cut-middle`、`pin-range`、`target-duration`。语义改由 `time_segments` 的边界表达。
_Avoid_: HTML UI 仍保留这些 checkbox(老用户习惯),保存时由 UI 层处理。

**保留段 vs 删除段**:
- 保留段:`SegmentState.segments[]` 内的段。
- 删除段:用户标删除的段(`.excluded=true`),**不应**进 JSON(spec §6.2 阶段 G)。

### ending 子系统术语(V4 设计)

**ending**:
intent.json 顶层字段,描述视频**最后一波处理**(画面结束 + 预告/字幕/口播打包)。V4 结构:

```jsonc
"ending": {
  "template": "<必填:HTML 选中的效果模板完整描述文本>",
  "prompt": "<可选:用户的额外补充说明>"
}
```

_Avoid_: `template` 不是 spec enum 值,只是 HTML UI 模板的人话描述文本。

**template(ending.template)**:
用户在 HTML select 中选中的某个效果模板的**完整描述文本**(人话,不是 ID)。
_Avoid_: 用 enum-like 值(如 "music-fade")——本字段只存人话。

**prompt(ending.prompt)**:
用户在 template 之外追加的自由文本。空字符串合法。

### 元数据字段(_meta)

**schema_version**:
intent.json 结构的版本号。当前为 `"3.0"`。AI 解析时凭它决定用 v3.0 schema 解析逻辑。
_Avoid_: HTML `_meta.version: "0.7"` 老字段——本次重构后删除或改名为 `tool_version`。

**tool_version**:
HTML 编辑器自身的产品版本号(与 intent.json 结构无关)。可选。
_Avoid_: 与 schema_version 合并——前者是产品发布号,后者是契约号,语义不同。

**history[]**:
老版本 HTML 在 `_meta.history` 数组中追加每次保存的 `{revision, timestamp}` 记录。本次重构**删除**(无消费者、spec 不要求、自引用陷阱)。
_Avoid_: 把审计/同步信息塞进 intent.json 自指——这块交给 `.scratch/` 本地 markdown issue tracker。

### 项目工具链术语

**atomic CLI**:
`scripts/` 下的单个 Python 脚本,每个负责一个原子操作。
_Avoid_: 把 atomic CLI 当成中间件/库调用——它们是 CLI。

**md 文档层(Layer 2A)**:
SKILL 中的人类语言层。包括 AI 路由表、协作协议、调用范式、阶段编排等。
_Avoid_: 把 md 当成"自动生成的文档"——它是 AI 行为的真实契约。

**Python 编排层(Layer 2B)**:
`scripts/_internal/` `lib/` 中的编排代码。它读 intent.json,决定调哪些 atomic CLI。
_Avoid_: 把 atomic CLI 和编排层混为一谈——前者是"做什么",后者是"什么时候做"。

### 流程术语

**grill-with-docs**:
第一阶段:对抗式审查 spec 与代码的偏移,沉淀共识。无代码改动,只产文档与决策。

**to-spec / to-tickets / implement**:
后续阶段。grill-with-docs 阶段确认后,会进入 to-spec(把 consensus 整合成可构建的 spec)、to-tickets(拆工单)、implement(逐工单实现)。每个阶段都要新建会话(`/handoff` 原则)。
_Avoid_: 在同一会话跨阶段——会爆上下文窗口,且违反流程纪律。

**归档(_archive/)**:
旧(superpowers)技能流产物的归位。`docs/superpowers/` 全部移到 `_archive/`(已决定,待执行)。
_Avoid_: 误以为还能用 superpowers——本次重构用 `/ask-matt` 总线。

---

## 当前已确认的决策(Pre-ADRs)

### D1 · intent.json 的 5 项字段定稿(2026-07-29)

| 字段 | 决策 |
|---|---|
| `output.aspect_ratio_custom` | **纳入 spec §4** |
| `cover.type` | 扩到 `ai/text/image` 三选项 |
| `cover.images[]` | 新增,仅 `type=image` 时填写 |
| `_meta.schema_version` | spec 明确为 `"3.0"`,HTML 必须写入 |
| `_meta.tool_version` | 可选,HTML 硬编码"0.7"改名至此 |
| `_meta.history[]` | **从 HTML 中删除** |

### D2 · ending 子系统重构(V4,2026-07-29)

| 决策 | 内容 |
|---|---|
| 抛弃 `ending.type` 6 选 1 enum 设计 | 历史 spec 互相矛盾,enum 设计本身不成立 |
| 新结构:`ending = {template, prompt}` | 两个文本字段,无任何 enum |
| HTML select = UX 层模板(5-10 个) | 模板内容已定稿,见下方 |
| 预告/字幕/口播不再进任何字段 | 全部并入 prompt 自由文本 |

**V4 原理**:枚举退守 / HTML 是 UX 不是 schema / AI 路由推迟 / 可演进 10 年。

### D3 · ending 模板 10 个(已定稿,2026-07-29)

UX 规则:**用户既要看到标题,也要看到描述,心里有数**。

| # | 标题 | template 文本 |
|---|---|---|
| 1 | 🎵 音乐淡出 | BGM 渐弱到静音,画面同步淡出,平稳收尾 |
| 2 | 🖼️ 末帧定格 | 画面停在最后一帧 3 秒,声音拉长同步,像定调 |
| 3 | ⬛ 突然切黑 | 画面 0.5 秒内切黑屏,声音同步静音,干脆利落 |
| 4 | 🎵💬 淡出 + 烧字 | 画面 + BGM 同步淡出 5 秒,烧一行字(如『下次见』)|
| 5 | ⬛💬 切黑 + 预告卡片 | 切黑屏后烧预告文字(如『下期见』),停留 3 秒 |
| 6 | 🖼️💬 定格 + 烧字 | 末帧定格 3 秒,同步烧 1-2 行主题字(电影感)|
| 7 | ⏱️ 倒计时钩子 | 切黑屏后烧倒计时数字 5-4-3-2-1(综艺/悬念感) |
| 8 | 📋 自由预告卡 | 切黑屏 + 烧你写的预告文字(下期/明天见/明年回归等)|
| 9 | 🎙️ 站外口播收尾 | 画面自然结束,叠加口播音频(如『今天到这儿,明天见』)|
| 10 | 🙏 感谢观看 | 画面自然结束,烧『感谢观看 · 点赞关注』停留 2 秒 |

### D4 · 兼容策略(2026-07-29)

**只支持 v3.0 intent.json**。HTML 加载旧 schema 文件时报错"请删除重填",**不做自动迁移**。
理由:简单明确。`migrateLegacyIntent` 函数保留作为参考但不启用。

### D5 · superpowers 归档(2026-07-29)

**`docs/superpowers/` 全部移到 `_archive/superpowers/`**(中间路线)。
理由:`2026-07-25-video-time-segment-model.html` 等历史 spec 仍有参考价值,但不再作为生产指南。

### D6 · Layer 2A vs Layer 2B 重构顺序(2026-07-29)

**md 文档层(Layer 2A)优先**,Python 编排层(Layer 2B)跟随。
理由:md 是 AI 行为的真实契约;Python 是机器实现。AI 看 md 实现代码——先让 md 自洽,再让 Python 实现对齐 md。

### D7 · 5 个该消失的 op 的处置(2026-07-29)

**A · 严格删除**:`trim-head`、`trim-tail`、`cut-middle`、`pin-range`、`target-duration` 这 5 个 op **从 HTML UI checkbox 移除**,从 `video_ops` JSON 字段消失。
语义改由 `time_segments` 边界表达:
- `trim-head sec=N` ≡ `time_segments[0].start_sec = N`
- `trim-tail sec=N` ≡ `time_segments[last].end_sec = duration_sec - N`
- `cut-middle from=X to=Y` ≡ 创建相邻两个 time_segments,中间不进 JSON
- `pin-range from=X to=Y` ≡ 单个 time_segments 区间
- `target-duration` ≡ 拼接后时长 = 各段相加(无需声明)

下游 Python(`lib/video_processing.py` 218-234, 508-509)删掉这 5 个 op 的解析逻辑。

### D8 · 段内调色 op 命名:`color` 而非 `color-grade`(2026-07-29 grill 第 1 题)

**段内 op 调色命名统一为 `color`**(不带 `-grade` 后缀)。理由:
1. HTML `SEGMENT_OPS_SCHEMA.color` 现状生产 `color`,改 HTML 改 1 行 vs 改 spec + JSON Schema 改 2 行 + HTML 验证全链路 — 成本最低
2. `color-grade` 的 `grade` 后缀语义模糊(中文读者第一反应"等级"而非"调色"),违反 **SPEC 是给人看的**原则
3. 命名统一后:HTML / spec / JSON Schema 三方零冲突
4. 统一真相源 = `color`,spec §7 白名单同步改为 `color`

**迁移**:
- spec §7 `validSegmentOps` 从 `['mute', 'speed-up', 'slow-down', 'reverse', 'color-grade']` 改 `['mute', 'speed-up', 'slow-down', 'reverse', 'color']`
- `references/intent_v3.schema.json` `time_segments[].ops.additionalProperties: false` 白名单同步:`color-grade` 改 `color`
- `lib/video_processing.py` `build_video_filter` 不受影响(读 `ops.color`,不读 op 名)
- HTML `SEGMENT_OPS_SCHEMA` 不动(已写 `color`)

### D9 · 段 ID 格式:`seg_${videoIdx}_${n}`(2026-07-29 grill 第 2 题)

**段 ID 格式统一为 `seg_${videoIdx}_${n}`**(v 1-based 视频索引,n 是段在该视频内的序号,从 1 递增)。理由:
1. spec §4 已有推荐格式,JSON Schema pattern 强制 `^seg_[0-9]+_[0-9]+$`(D4 老 schema 拒绝 → 无历史负担)
2. `seg_2_3` 比 `seg_2_new_1753796400000` 易读、AI 友好、天然排序
3. JSON 恢复流程只 spread 整个对象,id 原样保留,**格式不影响恢复**
4. 实现:HTML `SegmentState` 加 `nextN` 计数器,`addOrSplit` 用 `seg_${videoIdx}_${nextN}` 取代 `${baseId}new_${Date.now()}`

**迁移**:
- `references/intent_v3.schema.json` `time_segments[].id.pattern` 从 `^seg_[0-9]+_[0-9_a-zA-Z]+$` 加强制 `^seg_[0-9]+_[0-9]+$`
- HTML `SegmentState.addOrSplit`:新段 id 改为 `seg_${videoIndex+1}_${nextN}`(v 是 videoEntries index +1,与 `seg_${videoIdx}` 习惯一致)
- HTML `SegmentState` 初始化加 `nextN: 1` 字段,从已有 segments 的最大 n + 1 继续
- 下游 Python `lib/video_processing.py` 不受影响(只读 id,不解析格式)

**JSON 恢复验证**(无需改任何代码):
- JSON `[{id: "seg_1_1", ...}, {id: "seg_1_2", ...}]` 加载 → HTML 直接 spread 进 SegmentState → 后续 UI 渲染/编辑按 id 查 segments
- 格式与新增完全无关,只关心 id 字符串本身

---

## 当前项目路线(2026-07-29,用户口径)

按用户原话:
1. **综合 SKILL 各 md/spec/HTML → 定稿 JSON 真正包含的字段**(Layer 1)
2. **设计 SKILL md 修改方案**(Layer 2A 子集)
3. **设计 HTML 修改方案**(Layer 3)
4. **SKILL 语义层(md + Python)开发好**(Layer 2A + 2B 整体)

**4 个想法的真实协作关系**:
```
       想法 1(协议) 
            ↓
   ┌────────┴────────┐
   ↓                 ↓
想法 3(HTML)   想法 4(SKILL 语义层)
                       ↓
                  ┌────┴────┐
                  ↓         ↓
              md 文档     Python 编排
                  ↓         ↓
                  └────┬────┘
                       ↓
                  想法 2(让 md 自洽)
```

**关键**:想法 2 是想法 4 的子任务,不是顶层。

---

## 当前阶段状态

**grill-with-docs 阶段已完成**(2026-07-29)。

**D1-D7 全部沉淀**:
- D1(5 项字段定稿)
- D2(ending V4 重构)
- D3(10 个模板定稿)
- D4(兼容策略)
- D5(superpowers 归档)
- D6(Layer 2A 优先)
- D7(5 个该消失的 op 严格删除)

**实现层待办**(已识别,推到 implement 阶段处理):
- `SegmentState.addOrSplit` 注入的 `user` op 污染段 ops
- `collectFormData` 未过滤 excluded 段
- 段面板 `color` vs 校验白名单 `color-grade` 命名
- `voice-filler-removed` 连字符 vs `voice_filler_removed` 下划线(D7 后部分 obsolete)
- `_meta.tool_version` vs `_meta.schema_version` HTML 实际写入(D1 已决定)
- 段 ID 格式 `seg_2_new_${ts}` vs 推荐格式
- `docs/superpowers/` → `_archive/superpowers/` 实际目录移动动作

**当前阶段 → 下一阶段**:
- ✅ grill-with-docs(语言对齐)收官
- ⏭️ to-spec(把 D1-D7 整合成可构建的 spec,**用户手动执行**)
- ⏭️ to-tickets / implement(后续)

---

## 后续约定

1. **新术语出现时**:更新本文件(domain-modeling 技能驱动),不要在 issue 中解释术语。
2. **决策转正**:当 D1-D5 等"待转正决策"完成 ADR 评审,移到 `docs/adr/000X-name.md`,并在此处删除对应"Pre-ADR"。
3. **2 个上下文**:本文件是仓库级(单上下文);大模块若需独立术语,创建 `src/<module>/CONTEXT.md` + 根 `CONTEXT-MAP.md`(当前不需要)。

---

_Last updated: 2026-07-29 · grill-with-docs 第一性原理阶段 · D1-D5 沉淀完成_