# intent.json v3.0 重构 · Spec

> **状态**:ready-for-agent
> **创建日期**:2026-07-29
> **来源**:grill-with-docs 阶段(D1-D7 已沉淀)
> **目标 issue tracker**:本仓库 `.scratch/intent-v3-refactor/spec.md`

---

## Problem Statement

智剪工坊的 `intent.json` 是用户意图编辑器(`智剪工坊-意图编辑.html`)与 AI 流水线(`scripts/_internal/stage1_checklist.py` 等)之间的**唯一通信契约**。经过 7 项对抗式审查(grill-with-docs 2026-07-29),发现这份契约已经腐烂:

1. **JSON 字段结构混乱**:`_meta.version` / `_meta.schema_version` / 顶层 `version` 三种版本号并存,`_meta.history[]` 数组无人消费
2. **op 命名空间发散**:`videos[].ops` 平铺 22 个 op,5 个该消失的 op(`trim-head`/`trim-tail`/`cut-middle`/`pin-range`/`target-duration`) 仍进 JSON
3. **HTML 代码 bug**:5 个 HTML bug(下文"Implementation Decisions"详列)导致产出 JSON 不符合 spec
4. **ending 字段类型错误**:spec、AI 路由表、HTML select 三处枚举值互相矛盾(`ending.type` 应改 V4 设计)
5. **md 文档层失洽**:40+ 个 `references/*.md` 文件对字段语义、op 白名单、路由规则的描述不一致

**用户视角**:
- vlog 作者用 HTML 编辑器填表,产出 intent.json,希望 AI 能稳定解析
- AI 流水线读 intent.json,希望看到一份**没有矛盾、版本清晰、字段语义自洽**的契约
- 任何人(包括 6 个月后的自己)读 `references/*.md`,希望看到**和实际代码一致的描述**

**当前痛点**:
- HTML 写出的 JSON 经常让 AI 误判(`cover.type=image` 路由表说"不支持",但 SKILL.md 实装支持)
- 5 个该消失的 op 仍在 JSON 里,导致下游 Python 解析时多了一层 switch-case
- 文档与代码不一致,AI 必须"猜"

---

## Solution

**单一 seam 测试 boundary**:`intent.json` 字段契约(Schema v3.0)。

围绕这单一 seam,做三件事:

1. **协议层(Layer 1)**:定稿 `intent.json v3.0` 字段,删除矛盾字段,统一版本号语义
2. **语义层(Layer 2A → 2B)**:`references/*.md` 与 Python 编排逻辑按 md 优先顺序重写
3. **产出层(Layer 3)**:`智剪工坊-意图编辑.html` 按 spec 产出 JSON

**核心设计哲学**(grill-with-docs 沉淀):
- **枚举退守**:只在真正有限的离散空间保留 enum,无限空间用文本
- **HTML 是 UX 不是 schema**:模板/选项是 UX 层概念,不污染 spec
- **AI 路由推迟**:让 AI 解析时再分类,spec 不硬塞 enum
- **可演进 10 年**:新创意只需加 HTML 模板,spec 永远不动

---

## User Stories

### 数据契约层(Layer 1)

1. 作为 AI 流水线,我读到 `_meta.schema_version = "3.0"` 时能立即识别这是新 schema,不再误判为老 schema
2. 作为 AI 流水线,我希望 `ending` 字段只有 `template` 和 `prompt` 两个文本字段,不再有矛盾的 `ending.type` enum
3. 作为 AI 流水线,我希望 `output.aspect_ratio_custom` 字段存在(用户选 custom 时),不再需要 fallback 到 16:9
4. 作为 AI 流水线,我希望 `cover.type` 是 `ai/text/image` 三选项,且 `cover.images[]` 在 `type=image` 时存在
5. 作为 AI 流水线,我希望 `videos[].video_ops` 不再包含 5 个该消失的 op(`trim-head`/`trim-tail`/`cut-middle`/`pin-range`/`target-duration`)
6. 作为 AI 流水线,我希望 `videos[].time_segments` 不包含 `user` op(spec 不允许的内部标记)
7. 作为 AI 流水线,我希望已删段(`excluded=true`)不出现于 `time_segments`
8. 作为 AI 流水线,我希望 `_meta.history[]` 不再存在(无消费者、spec 不要求)
9. 作为 AI 流水线,我希望看到清晰的段内 op 白名单(`mute`/`speed-up`/`slow-down`/`reverse`/`color-grade`)

### 编辑器层(Layer 3)

10. 作为 vlog 作者,我希望 HTML 编辑器写入的 `_meta.schema_version` 永远是 `"3.0"`,无论新老项目
11. 作为 vlog 作者,我希望 HTML 的 `ending` select 提供 10 个效果模板(BGM 渐出/末帧定格/切黑 等),每个都有标题 + 描述让我心里有数
12. 作为 vlog 作者,我希望在 HTML 上选 `cover.type=image` 时能看到图片上传器,不再报错
13. 作为 vlog 作者,我希望在 HTML 上不能用旧版 5 个 op 的 checkbox(它们已被 timeline 框选取代)
14. 作为 vlog 作者,我希望在 HTML 上误删段后能保存(已删段不入 JSON,但恢复区可见)

### 语义层(Layer 2A · md)

15. 作为 AI 流水线,我希望 `references/AI路由表-意图JSON字段枚举.md` §3(ending.type 路由)整段改写,因为旧 enum 已废除
16. 作为 AI 流水线,我希望 `references/AI协作协议-详细.md` §3.1(ending.type fallback)改写,因为不存在 fallback 概念了
17. 作为 AI 流水线,我希望 `SKILL.md` §4(ending.type 路由表)整段删除,因为不再有 enum
18. 作为 AI 流水线,我希望 `references/原子操作-14种基础剪辑指令.md` 改名 / 重写(因 op 数量变化)
19. 作为 AI 流水线,我希望 md 文档对每段 op 的描述与 spec §4 一致(`color` vs `color-grade` 命名统一)
20. 作为 AI 流水线,我希望 md 文档描述的字段枚举与 HTML select 选项一一对应

### 编排层(Layer 2B · Python)

21. 作为 AI 流水线,我希望 `scripts/_internal/stage1_checklist.py` 读新 schema(`video_ops` + `time_segments`),不再读老的 `videos[].ops`
22. 作为 AI 流水线,我希望 `lib/video_processing.py` 删掉 5 个 op 的解析逻辑(218-234, 508-509)
23. 作为 AI 流水线,我希望 atomic CLI(`scripts/audio/*.py` 等)继续稳定,只调整被调用方(`stage1_checklist.py`)
24. 作为 AI 流水线,我希望加载老 schema 的 intent.json 时报"请删除重填",不静默迁移(D4)

### 兼容性层

25. 作为 vlog 作者,我加载老 intent.json 时看到明确报错信息,告诉我哪里格式不对
26. 作为维护者,我看到 `.scratch/intent-v3-refactor/` 里有完整的 spec、移交清单、issue 列表

---

## Implementation Decisions

### D1 · 5 项 JSON 字段定稿

**决策摘要**:以下 5 项字段在 spec §4 中明确定义。

```jsonc
"_meta": {
  "schema_version": "3.0",     // 必须,字符串
  "tool_version": "2.135",     // 可选,字符串
  "revision": 7,               // 必须,int
  "created": "ISO 8601",       // 必须
  "updated": "ISO 8601",       // 必须
  "workspace": "string"        // 必须
  // history[]:不存在
}
"output": {
  "aspect_ratio": "9:16 | 16:9 | 1:1 | 3:4 | 4:3 | custom",
  "aspect_ratio_custom": "W:H",           // aspect_ratio="custom" 时必填
  "aspect_handling": "aspect-fit | aspect-fill"
}
"cover": {
  "type": "ai | text | image",
  "prompt": "string",
  "images": ["path", "..."]              // 仅 type="image"
}
```

**理由**:
- `schema_version` 是 AI 必备版本锚点
- `tool_version` 区分产品版本与 schema 版本(命名冲突避免)
- `history[]` 无消费者、自引用陷阱,删除
- `aspect_ratio_custom` AI 路由表已要求、normalize.py 依赖
- `cover.images[]` 多图拼版场景需要

**接口影响**:
- HTML `collectFormData` 写入 `_meta.schema_version` + 删除 `history[]`
- Python 编排读 `output.aspect_ratio_custom` 而非只 fallback 16:9

---

### D2 · ending V4 重构

**决策摘要**:`ending` 字段重构成两个文本字段,抛弃 6 选 1 enum。

```jsonc
"ending": {
  "template": "<必填:HTML 选中的效果模板完整描述文本>",
  "prompt": "<可选:用户的额外补充说明>"
}
```

**原理(写进 spec 注释)**:
1. 枚举退守
2. HTML 是 UX 不是 schema
3. AI 路由推迟
4. 可演进 10 年

**接口影响**:
- HTML `ending` select 改 10 个效果模板(UX 层),每个存完整人话描述
- AI 读 `template + prompt` 按 `references/AI路由表 §5 E 象限` 文本路由
- 删 `SKILL.md` §4 / `references/AI协作协议 §3.1` / `references/AI路由表 §3` 三处老 enum 描述

**已定稿 10 个 ending 模板**(D3):

| # | 标题 | template |
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

---

### D4 · 兼容策略

**决策摘要**:**只支持 v3.0 intent.json**,加载老 schema 文件时报错"请删除重填",**不做自动迁移**。

```text
加载流程:
  intent.json detected
    → 检查 _meta.schema_version
       → "3.0" → 正常解析
       → 缺失或非 "3.0" → 报错:
          "intent.json schema_version=<x> 不被支持,
           请删除该文件后重新用 HTML 编辑器创建"
```

`migrateLegacyIntent` 函数保留在 HTML 中作为参考文档(注释明确标"未启用")。

---

### D5 · superpowers 归档

**决策摘要**:`docs/superpowers/` 全部移到 `_archive/superpowers/`(目录重命名动作)。

理由:`2026-07-25-video-time-segment-model.html` 等历史 spec 仍有参考价值,但不再作为生产指南。

---

### D6 · Layer 2A vs Layer 2B 重构顺序

**决策摘要**:**md 文档层(Layer 2A)优先,Python 编排层(Layer 2B)跟随**。

执行顺序:
1. 重写 `references/AI路由表-意图JSON字段枚举.md`(Layer 2A)
2. 重写 `references/AI协作协议-详细.md`(Layer 2A)
3. 重写 `SKILL.md`(Layer 2A)
4. 重写 `references/主流程-阶段编排.md`(Layer 2A)
5. 重写 `references/原子操作-14种基础剪辑指令.md`(Layer 2A)
6. md 自洽后,重写 `scripts/_internal/stage1_checklist.py`(Layer 2B)
7. 重写 `lib/video_processing.py`(Layer 2B)
8. 最后改 HTML `智剪工坊-意图编辑.html`(Layer 3)

理由:md 是 AI 行为的真实契约;Python 是机器实现。AI 看 md 实现代码。

---

### D7 · 5 个该消失的 op 严格删除

**决策摘要**:`trim-head`、`trim-tail`、`cut-middle`、`pin-range`、`target-duration` 这 5 个 op **从 HTML UI checkbox 移除**,从 `video_ops` JSON 字段消失。

| op | 旧语义 | 新语义(由 time_segments 表达) |
|---|---|---|
| `trim-head sec=N` | 剪头 N 秒 | `time_segments[0].start_sec = N` |
| `trim-tail sec=N` | 剪尾 N 秒 | `time_segments[last].end_sec = duration_sec - N` |
| `cut-middle from=X to=Y` | 删中间 | 创建相邻两个 time_segments,中间不进 JSON |
| `pin-range from=X to=Y` | 只保留一段 | 单个 time_segments 区间 |
| `target-duration sec=N` | 目标时长 | 拼接后时长 = 各段相加(无需声明) |

**接口影响**:
- HTML UI 删除 5 个 checkbox + 渲染模板
- HTML `legacyOps` 数组剔除这 5 个
- HTML `collectVideoOpsForVideo` 不再尝试收集
- Python `lib/video_processing.py` 218-234, 508-509 删解析逻辑
- Python `stage1_checklist.py` 删 switch case

---

### Spec §4 完整版(Layer 1 协议定稿)

完整 schema 草案(从 D1+D2+D7 整合):

```jsonc
{
  "_meta": {
    "tool": "智剪工坊",                  // 必须
    "schema_version": "3.0",              // 必须,字符串
    "tool_version": "2.135",              // 可选,字符串
    "revision": 7,                        // 必须,int,每次保存 +1
    "created": "<ISO 8601>",              // 必须
    "updated": "<ISO 8601>",              // 必须
    "workspace": "<folder name>"          // 必须
  },

  "project": {
    "name": "<项目名,可选>",
    "title": "<成片标题,可选>",
    "overall_intent": "<总调性,可选>"
  },

  "output": {
    "aspect_ratio": "9:16 | 16:9 | 1:1 | 3:4 | 4:3 | custom",
    "aspect_ratio_custom": "<W:H>",       // aspect_ratio="custom" 时必填
    "aspect_handling": "aspect-fit | aspect-fill"
  },

  "cover": {
    "type": "ai | text | image",
    "prompt": "<封面描述,可选>",
    "images": ["<路径>"]                  // 仅 type="image"
  },

  "ending": {
    "template": "<必填:效果模板完整描述文本>",
    "prompt": "<可选:用户的额外补充说明>"
  },

  "sequences": [
    {
      "title": "<链标题,可选>",
      "videos": [1, 2, 3],               // entry.index 序列
      "transitions": [
        { "after": 1, "type": "fade | none | ...", "duration": 0.5 }
      ]
    }
  ],

  "videos": [
    {
      "file": "<filename.mp4>",
      "index": 1,                          // 1-based stable ID
      "duration_sec": 60,
      "exclude": false,
      "summary": "<一句话简介>",
      "intent": "<剪辑意图>",

      "video_ops": {                       // 整段视频的 op(整段生效)
        "speed-up": { "on": true, "factor": 1.5 },
        "slow-down": { "on": true, "factor": 0.7 },
        "reverse": { "on": true },
        "mute": { "on": true },
        "fade-in": { "on": true, "sec": 1 },
        "fade-out": { "on": true, "sec": 1 },
        "color": { "on": true, "style": "warm" },
        "add-bgm": { "on": true, "file": "...", "volume": 0.4 },
        "replace-audio": { "on": true, "file": "..." },
        "opening-text": { "on": true, "text": "...", "duration": 3 },
        "insert-image": { "on": true, "file": "...", "at": "0:02", "duration": 4 },
        "asr-transcribe": { "on": true, "model": "medium" },
        "asr-burn": { "on": true, "font_size": 24 },
        "asr-speaker": { "on": true },
        "audio-denoise": { "on": true },
        "audio-separate": { "on": true, "model": "htdemucs_ft" },
        "audio-diarize": { "on": true },
        "voice-filler-removed": { "on": true },
        "voice": { "on": true, "mode": "keep | keep-with-filler-removed | mute | bgm-only" },
        "voice_note": "<自由文本>",
        "notes": "<视频整体备注>",
        "duration": { "on": true, "sec": 3 }  // 图片专属
      },

      "time_segments": [                   // 片段保留(可空 = 整段保留)
        {
          "id": "seg_1_1",
          "label": "<用户可改>",
          "start_sec": 2.0,
          "end_sec": 31.0,
          "ops": {                          // 段内 op(白名单:mute/speed-up/slow-down/reverse/color-grade)
            "mute": { "on": true },
            "speed-up": { "on": true, "factor": 2.0 }
          },
          "note": "<段级备注>"
        }
      ]
    }
  ]
}
```

---

### 已知实现层偏移(implement 阶段处理)

以下 6 项**不阻塞本 spec**,但 implement 阶段必须修:

| # | 偏移 | 修复点 |
|---|---|---|
| 1 | 拆段注入的 `user` op 污染段 ops | HTML `SegmentState.addOrSplit` 移除 user 注入 |
| 2 | `collectFormData` 未过滤 excluded 段 | HTML `collectFormData` 加 filter |
| 3 | 段面板 `color` vs 校验白名单 `color-grade` 命名 | HTML 命名统一(待 grill 决定方向) |
| 4 | `_meta.tool_version` 写入 | HTML 字段名重命名 |
| 5 | 段 ID 格式 `seg_2_new_${ts}` | HTML 改为 `seg_${videoIdx}_${n}` |
| 6 | 加载老 schema 报错信息 | HTML 加载逻辑实现 D4 |

---

## Testing Decisions

### 单一 seam = `intent.json v3.0` Schema 校验

按 to-spec 原则"the ideal number is one",本次测试只围绕**一个 seam**:`intent.json` 字段契约。

### 测试层级

| 层级 | 测试对象 | 工具 |
|---|---|---|
| **HTML 写入校验** | `collectFormData` 输出 JSON 符合 spec §4 | HTML 内置 `validateIntent` |
| **Python 读取校验** | `stage1_checklist.py` 能解析新 schema | Python jsonschema |
| **端到端 fixture** | 一份样例 JSON 通过所有消费方 | `intent_v3_minimal.json` + `intent_v3_full.json` |

### 测试原则

- **只测外部行为**,不测实现细节
- 例:测试"输入含 5 个该消失的 op 时,validateIntent 拒绝",不测试"是哪个 switch-case 拒绝"
- 例:测试"加载老 schema 时报错",不测试"具体报错文案逐字"

### 必备测试用例

1. **HTML validateIntent 通过用例**:符合 spec §4 的最小完整 JSON 必须通过
2. **HTML validateIntent 拒绝用例**:
   - `_meta.schema_version` 缺失或非 "3.0"
   - `videos[].video_ops` 含 `trim-head` 等 5 个 op
   - `time_segments[].ops` 含白名单外 op(如 `color`、`user`)
   - `time_segments[].ops` 含 `color-grade`(目前 HTML 用 `color`,spec §7 白名单用 `color-grade` — 命名待定)
   - `cover.type=image` 但 `cover.images[]` 缺失
3. **HTML 加载老 schema 报错用例**:加载 v1.x 老 JSON 时明确报错
4. **Python 解析用例**:`stage1_checklist.py` 读新 schema 应产出符合 §A-F 6 象限的操作清单
5. **Python 删除解析用例**:`stage1_checklist.py` 不再尝试读 `trim-head` 等 5 个 op

### Prior art(代码库现有测试模式)

- `scripts/ai/cover_compose/tests/test_cover_compose.py` — pytest 模式
- HTML 内置 `validateIntent`(5079-5119)— JS 函数模式

---

## Out of Scope

本 spec **不**包含以下内容(明示排除):

1. **5 个该消失的 op 的 UI 翻译层**:虽然 B 选项(UI 保留 checkbox,内部转换)能减少用户上手成本,但 D7 选择 A 严格删除。本 spec 不为"老用户习惯"提供兼容路径。
2. **ending 模板的视觉设计**:10 个模板的内容已定稿(D3),但具体 UI 卡片样式(图标、配色、布局)不在本 spec 范围。
3. **stage1_checklist.py 的 6 象限重设计**:本 spec 只要求它能读新 schema,不要求改变输出格式。
4. **atomic CLI 重构**:本 spec 只要求 atomic CLI 被正确调用,不要求 atomic CLI 自身改动。
5. **AI 行为日志协议**:`references/AI行为日志协议.md` 不在本 spec 范围。
6. **封面合成多图拼版的具体拼版算法**:`cover_compose/` 子模块已有,不重构。
7. **流水线模板(`模板/*.yaml`)**:`SKILL.md` 提到的 `健身vlog.yaml` 等模板,不在本 spec 范围。
8. **封面/ending 的 AI 生成能力(`ai_cover.py` 等)**:`scripts/ai/` 不重构。
9. **文档归档动作**:D5(superpowers 移到 `_archive/`)是文件系统操作,不在 spec 测试 seam 内。
10. **历史意图迁移**:`migrateLegacyIntent` 函数保留作参考但不启用(D4 明确不支持迁移)。

---

## Further Notes

### Spec 是协议蓝图,**不是实现文档**

本 spec 只规定 **intent.json v3.0 字段契约**。HTML/Python/md 如何实现是 implement 阶段的事,本 spec 不指定具体文件路径或代码片段。

### 唯一权威来源

`intent.json v3.0` 字段定稿(见 "Implementation Decisions" § "Spec §4 完整版")是本 spec 的**唯一权威**。如果其他文档(md、代码注释)与本 spec 冲突,以本 spec 为准。

### md 重构顺序(D6)

实施时,**先 md 后 Python**:
1. md(Layer 2A) — AI 看到的契约
2. Python(Layer 2B) — 机器实现
3. HTML(Layer 3) — 编辑器产出

理由:md 是 AI 行为契约;Python 跟随 md 实现。

### 与 superpowers 技能的边界

本 spec **不**使用 superpowers 流程(plan/spec/ticket 三段式)。改用 `/ask-matt` 总线的 grill-with-docs → to-spec → to-tickets → implement。

旧 `docs/superpowers/` 下的产物作为**事实记录**归档到 `_archive/`,参考用。

### 用户后续动作

按用户口径:
1. 本 spec 完成后进入 **to-tickets** 阶段
2. 工单按 Layer 顺序拆解:
   - 工单组 A:Layer 2A md 重写(5 个 md 文件)
   - 工单组 B:Layer 2B Python 重写(2 个核心文件)
   - 工单组 C:Layer 3 HTML 修改(详见"已知实现层偏移"6 项)
3. 每个工单标 `ready-for-agent`,独立 execute

### 引用文档(全在仓库内)

- `CONTEXT.md` — 术语统一 + D1-D7 沉淀
- `docs/superpowers/specs/2026-07-29-grill-with-docs-handoff.md` — grill 阶段移交清单
- `docs/superpowers/specs/2026-07-25-video-time-segment-model.html` — 原 spec(已部分被本 spec 替代)
- `2026-07-29-mock-spec-ideal.json` — V4 ending + D1 字段的样例输出

---

_Generated: 2026-07-29 · to-spec 阶段 · ready-for-agent_