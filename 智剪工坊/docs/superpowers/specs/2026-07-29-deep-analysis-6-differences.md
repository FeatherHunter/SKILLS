# 对抗式分析报告:6 项 spec 差异的根源

> **第一性原则**: 不"哪边对哪边错",而是问"这个字段的语义是什么?消费者需要什么?"

---

## 真相图景:三份相互矛盾的 spec/路由表

仓库里有**三个独立的事实源**,对同一组字段的定义不一致:

| 事实源 | 角色 | 权威性 |
|---|---|---|
| `智剪工坊-意图编辑.html` | 实际生产者 | ✅ **最高**(现实是它产出的 JSON) |
| `references/AI路由表-意图JSON字段枚举.md` | 给 AI 看的运行时白名单 | 🟡 运行时权威(AI 解析时凭此判断) |
| `docs/superpowers/specs/2026-07-25-video-time-segment-model.html` | v3.0 结构性 spec | 🟢 设计意图(蓝图,未对齐实现) |
| `SKILL.md` §4/§5 | 历史路由表 | ⚫ 已被 AI 路由表吸收 |

**三份表格相互矛盾,这是仓库当下最大的熵源。**

---

## 差异 #1:`output.aspect_ratio_custom` 是否纳入 spec

### 事实

```yaml
AI 路由表 §1 (权威):
  字段: output.aspect_ratio_custom
  路径: 顶层
  类型: string
  可选值: "W:H"(自定义比例)
  AI 必读说明: aspect_ratio="custom" 时必填

HTML 实际 (2045 行):
  - 用户选 "custom" 时显示的文本框
  - 写入 JSON 的 output.aspect_ratio_custom
  - HTML 自己 4572 行用它: `aspectVal = o.aspect_ratio === 'custom' ? o.aspect_ratio_custom : o.aspect_ratio`
  - HTML 自己 4776 行总览展示也用它
  - video_normalize.py 86 行 fallback 16:9 兜底

Spec §4:
  - 未列出此字段
```

### 消费者需求分析

| 消费者 | 是否需要 | 怎么用 |
|---|---|---|
| `video_normalize.py` | ✅ | 把任何比例归一化到 16:9(默认),如果 a_custom 存在应该用 |
| HTML 总览(4776) | ✅ | 展示给用户看 |
| `stage1_checklist.py` | ❌ | 没读 |
| `video_processing.py` | ❌ | 没读 |

### 第一性原理

`aspect_ratio_custom` 的语义 = **"用户选 custom 时填具体 W:H 字符串"**。它是 `aspect_ratio` 的"扩展槽"。

设计上有三种可能:
1. **单一字符串**:`aspect_ratio` 容纳所有值,包括 `"21:9"`(无 _custom)
2. **二元组**:`aspect_ratio: "custom"` + `aspect_ratio_custom: "21:9"`(HTML 现状)
3. **列表**:`aspect_ratio: ["16:9", "9:16", "21:9"]` 自由组合

HTML 现状(方案 2)是最**安全的**——如果用户选了预设值(custom),_custom 才生效,不需要额外校验。这是表单驱动的设计。

### ✅ 对抗式结论

**应当纳入 spec**。理由:
1. AI 路由表已把它列为"必读"(权威事实源)
2. 三处消费者依赖它(HTML 总览、normalize.py fallback、未来可能的 AI 解析)
3. 排除会导致 AI 看到 `aspect_ratio=custom` 时不知道比例是多少 → 问用户或瞎猜(spec 反对)

### 推荐 spec 改法

在 spec §4 `output` 块中加:
```jsonc
"output": {
  "aspect_ratio": "9:16 | 16:9 | 1:1 | 3:4 | 4:3 | custom",
  "aspect_ratio_custom": "W:H",     // 当 aspect_ratio="custom" 时必填
  "aspect_handling": "aspect-fit | aspect-fill"
}
```

---

## 差异 #2:`cover.type` 枚举(HTML vs spec)

### 事实

```yaml
Spec §4:
  cover.type: "ai | text | image"

AI 路由表 §1:
  cover.type: "ai" / "text" / "image"
  AI 必读: "image 当前不支持(智剪工坊-意图编辑.html 没字段承载图片路径)"

HTML select (2069-2073):
  选项: "" | "ai" | "text"
  ⚠️ 没有 "image" 选项

HTML 总览 (4576 行):
  c.type === 'image' 时标记 invalid
HTML 健康检查 (4706 行):
  c.type === 'image' → 报红"不支持,请改 ai 或 text"

cover_compose 模块 (SKILL.md 950 行):
  cover.type='image' 实际上**由 cover_compose/ 子模块处理**(多图拼版)
  → AI 路由表 98-100 行说"不支持"是错的(SKILL.md 944-950 证明它被支持)
```

### 真相

`cover.type='image'` **已被实现**(cover_compose/),AI 路由表描述过时。HTML 下拉选项**少一个**(HTML 没设计 image 选项)。

### 第一性原理

封面有三种生成方式:
- **AI 生图**: 基于 prompt 生成新图(`ai`)
- **纯文字**: 用 PIL 画一张纯文字(`text`)
- **多图拼版**: 几张已有图拼成一张(`image`)

这是**三个完全不同的渲染路径**,必须清楚区分。HTML 漏 image 是 UI bug,不是 spec 错。

### 对抗式审查

| 选项 | spec 选 | AI 路由表选 | HTML 选 | 我的推荐 |
|---|---|---|---|---|
| `ai` | ✅ | ✅ | ✅ | 三者一致 ✅ |
| `text` | ✅ | ✅ | ✅ | 三者一致 ✅ |
| `image` | ✅ | ❌("不支持") | ❌(无选项) | **正确选项**(`cover_compose/` 已实现) |

**注意矛盾**: AI 路由表和 HTML 都认为 `image` 不支持,但 SKILL.md `cover_compose/` 子模块明确说支持。这是一份路由表的描述错误。

### ✅ 对抗式结论

**按 spec 来**:`cover.type` 应是 `ai/text/image` 三选项。理由:
1. SKILL.md 已证明 `image` 路径实装(`cover_compose/`)
2. HTML 漏掉 `image` 是 UI 实现 bug,需要在 HTML select 添加 `<option value="image">多图拼版</option>`
3. AI 路由表的"不支持"描述是**过时的**,需要更新说明 `image` → `cover_compose/` 子模块

### 后续工作

- HTML 2069-2073 增 `<option value="image">多图拼版 — 需几张原图(详见 cover_compose)</option>`
- AI 路由表 §4 把 `image` 行从"不支持"改为"路由 cover_compose/(多图拼版)"
- HTML `cover_compose/` 处理时需要 `cover.images[]` 字段(目前 spec 没列,需要新增)

---

## 差异 #3:`ending.type` 枚举(HTML vs spec 谁更合理)

### 事实

```yaml
Spec §4:
  ending.type: "fade | freeze | text | <6 种之一>"
  (spec 没完全列出来,留了"<6 种之一>"占位)

AI 路由表 §3:
  ending.type: "fade" / "freeze" / "next-day" / "text"
  → 4 种
  → 第 5 种 next-episode-promo/next-week 是 v1.10 扩展(SKILL.md 940-941 行)

HTML select (2087-2093):
  选项: "" | "voice-narration" | "music-fade" | "cut-to-black" | "next-episode-promo"
  → 4 种(html 的是 music-fade/cut-to-black/voice-narration + next-episode-promo)

HTML 校验白名单 (4579 + 4708 行):
  endingValid = ['fade', 'freeze', 'next-day', 'next-episode-promo', 'next-week', 'text']
  → 6 种
  → 与 AI 路由表不完全一致(多了 next-episode-promo/next-week)
```

### 真相

**spec、AI 路由表、HTML 三者枚举不统一**:

- spec: 模糊的"<6 种之一>"
- AI 路由表: 4 种(`fade/freeze/next-day/text`)
- HTML 校验白名单: 6 种(`fade/freeze/next-day/next-episode-promo/next-week/text`)
- HTML select 选项: 4 种(`music-fade/cut-to-black/voice-narration/next-episode-promo`)

### 第一性原理:用户在说"我想要结尾 X"时,语义是什么?

结尾的**用户心智**大概有这几类:
- **结束感**:渐渐变淡消失(music-fade/fade)
- **悬停感**:停在最后一帧(freeze)
- **预告感**:留个钩子(next-day/next-episode-promo/next-week)
- **信息感**:硬切文字(text/cut-to-black)
- **对话感**:口播(voice-narration)

设计上有两种思路:

#### 思路 A:按"动作类型"枚举(spec/AI 路由表风格)
```
fade | freeze | next-day | text | voice-narration | music-fade | cut-to-black | next-episode-promo | next-week
```
优点:动作动词清晰,AI 易解析。
缺点:用户选"淡出 + BGM 减弱"时一个 `fade` 不够,需要 `music-fade` 单独枚举。

#### 思路 B:按"动作"+"效果"分两层(JSON 多字段)
```jsonc
{ "type": "fade", "audio_handling": "music-fade", "duration": 5 }
```
优点:灵活组合。
缺点:AI 解析时要看两层。

### 哪家更合理?

**思路 A 的现状**: HTML select 4 选项 + 校验白名单 6 选项,意味着 HTML 表单**只有 4 个具体选项,用户被强迫选其一,但提交后还要被校验白名单二次过滤**——出现"用户在 HTML 选 X,保存后 AI 校验发现 X 不在白名单"的鬼故事。

实际上 HTML 2087-2093 的 select 给出的选项是不可执行的: 如果用户选 `music-fade`,保存进 JSON 后,AI 校验说 `music-fade` 不在白名单——这就分裂了。

### ✅ 对抗式结论

**AI 路由表 + HTML 校验白名单的"动作类型枚举"组合更合理**,即:
```yaml
ending.type: fade | freeze | next-day | next-episode-promo | next-week | text
```

理由:
1. **AI 路由表 + SKILL.md + HTML 校验白名单三处一致指向"动作动词"**枚举(spec 反而是最模糊的)
2. HTML select 的 4 个具体选项(`music-fade`/`cut-to-black`/`voice-narration`/`next-episode-promo`)**设计过度**——`music-fade` 实际是 `fade` 的子类型,`cut-to-black` 实际是 `freeze` 加 black padding mode
3. spec 给的"`<6 种之一>`"是设计阶段的占位,不是真正的设计意图

### 推荐 spec 改法

在 spec §4 中明确:
```jsonc
"ending": {
  "type": "fade | freeze | next-day | next-episode-promo | next-week | text",
  "prompt": "<结尾描述>"
}
```
**`music-fade`/`cut-to-black`/`voice-narration` 应该被规范化为:**
- `music-fade` → `fade` + audio 策略交由 `audio/audio_fadeout` 处理(归到 audio_ops)
- `cut-to-black` → `freeze` + padding-mode=`black`(作为 freeze 的子参数)
- `voice-narration` → `text`(用 voice-over 内容)

同时 HTML 的 select 选项需要**重新设计**为这 6 个:

```html
<select data-path="ending.type">
  <option value="">— 待定 —</option>
  <option value="fade">淡出</option>
  <option value="freeze">定格</option>
  <option value="next-day">下期预告</option>
  <option value="next-episode-promo">下期预告(详版)</option>
  <option value="next-week">下周预告</option>
  <option value="text">字幕文字</option>
</select>
```

### 后续工作

- HTML 2087-2093 select 重写为 6 选项
- spec §4 明确 `ending.type` 6 选 1
- AI 路由表 / SKILL.md / HTML 校验白名单 / HTML select 四处统一

---

## 差异 #4:`_meta.version` 字段(spec 是否需要新增)

### 事实

```yaml
AI 路由表 §1 (权威):
  version: 顶层 string "v0.5" / "v1.0" / "v1.2"  schema 版本, AI 不修改

注意: AI 路由表把 version 放在**顶层**,不是 _meta 下!
```

```yaml
HTML 实际 (4866-4876):
  _meta: {
    tool: '智剪工坊',
    version: '0.7',  // ⚠️ 硬编码,无 v 前缀,位置在 _meta 下
    ...
  }
```

```yaml
Spec §4:
  _meta: {
    tool, schema_version, revision, created, updated, workspace
  }
  ⚠️ spec 同时列了 schema_version 和 未列 version(实际上 spec 只列了 schema_version)
```

### 命名空间分析

这里有**两组互斥的版本概念**:

1. **`schema_version`(v3.0)**: JSON 结构的版本号(影响如何解析)
2. **`version`(v0.5/v1.0/v1.2)**: HTML/工具产品的版本号(影响 UI 体验)

这两个完全不同:
- `schema_version=2.0` → AI 走"v2.0 schema 解析逻辑"(对 ops 平铺)
- `schema_version=3.0` → AI 走"v3.0 schema 解析逻辑"(对 video_ops/time_segments)
- `version=v1.0` → HTML 显示 v1.0

AI 路由表第 14 行写的是 `version`,语义是 schema 版本(从枚举值 `v0.5/v1.0/v1.2` 看)。所以**两份 spec 实际上指向同一概念,只是叫法不同**。

### 真相:这是个**命名迁移**问题

AI 路由表(老)的 `version` 概念迁移到新 spec(2026-07-25)时改名为 `schema_version`,但**位置错了**——老版放在顶层,新版放在 `_meta` 下。

### 第一性原理

版本号**必须**:
1. AI 能读到一个稳定字段名,以此判断用哪套解析逻辑
2. HTML 写文件时正确写入
3. 不要重复——一个文件只有一个 schema 版本

### 命名空间争论

位置之争:
- 顶层 `version`(AI 路由表习惯)
- `_meta.schema_version`(v3.0 spec 习惯)

**`_meta` 是更好的位置**,因为:
- schema_version 是 metadata,JSON 的 metadata 应该收拢
- 顶层 `version` 易和"项目版本"混淆(可能有 `project.version`)
- v3.0 spec 已经用 `_meta.schema_version` 而且 `migrateLegacyIntent` 也用它作为版本判断锚点(5147 行)

### ✅ 对抗式结论

**需要在 spec 中明确**:`_meta.schema_version = "3.0"`(spec 已经有,但需要正式明确且 HTML 写入)

具体修复:

1. **HTML 必须写入**: `collectFormData` 4867 行加 `schema_version: '3.0'`(代替当前的 `version: '0.7'`)
2. **AI 路由表更新**: 把第 14 行的"version"改为 `_meta.schema_version`,枚举值改成 `"3.0"`(跟新 spec 一致);或者把第 14 行整行删除(因为 `_meta.schema_version` 已经是新 spec 的字段)
3. **HTML 4868 的 `version: '0.7'` 干什么的**:这是 HTML/工具产品的版本号,如果要保留,改名为 `_meta.tool_version`(避免和 schema_version 混淆);如果不需要,直接删

### 我的推荐

**同时保留两个,语义清晰分工**:
```jsonc
"_meta": {
  "schema_version": "3.0",   // JSON 结构版本(影响 AI 解析)
  "tool_version": "2.135",   // 智剪工坊 HTML 版本(影响 UI/产品,与 AI 无关)
  "revision": 7,             // 修订号
  "created": "...",
  "updated": "...",
  "workspace": "..."
}
```

理由:
- schema_version = JSON 结构契约的版本
- tool_version = 工具(HTML 编辑器)本身的版本号
- 两者语义不同,合并会让 AI 解析时混乱

如果 HTML 实际不需要"工具版本号",就把 `_meta.version` 删掉,只留 `schema_version`。**这是个收尾决定**,看 HTML 产品有没"显示当前版本号"的 UI 需求。

---

## 差异 #5:`_meta.history[]` 数组的语义

### 事实

```yaml
HTML 实际 (4864-4865 行):
  const oldHistory = Array.isArray(existingIntent?._meta?.history) ? existingIntent._meta.history : [];
  const newHistory = [...oldHistory, { revision: newRev, timestamp: now }];
  // _meta.history: 数组,每条 {revision: int, timestamp: ISO 8601}
```

```yaml
Spec §4:
  _meta: { tool, schema_version, revision, created, updated, workspace }
  ⚠️ spec 没列 history

AI 路由表 §1:
  列了 _meta.revision,但没列 _meta.history
```

### 第一性原理:`history[]` 解决什么问题?

`history[]` 是 **append-only 修订日志**: `[rev1, rev2, rev3...]`,每次保存 append 一条 `{revision, timestamp}`。

它解决的问题:
- 用户问"我昨天改了什么?"——能审计所有改动时间戳
- AI 想看修改轨迹——能推断哪些字段是最近改的
- 自动同步/备份——能识别"哪个版本最后同步到云端"

**为什么不直接用 `_meta.updated`?**
- `_meta.updated` 只有一个时间戳(总是最新),没法看历史
- `_meta.revision` 是 monotonic 计数,但也没法看历史

### 评估:`history[]` 是否真的需要?

**正方**(保留):
- 给审计/同步/回滚留余地
- schema 设计成本极低(append 数组)
- 修订号 + 时间戳 是有用的元信息

**反方**(删除):
- 当前没有任何代码读它(`grep -r "history"` 没找到消费者)
- spec 不要求
- 文件体积膨胀(每次保存多一条)
- 如果将来要做"回滚"功能,应该专门设计一个 audit log,而非塞在 _meta

### 真相:这是一个**"自我引用"陷阱**

`_meta.history[]` 是**自我引用**——它记的是"自己存自己的过程"。它有可被篡改、无法脱锚验证、可被恢复导致的事件循环等问题。

更稳妥的设计:
- **真正的审计日志**:由 `.scratch/某功能/issues/NN-xxx.md` 承载(本地 markdown issue 跟踪)
- **文件元数据**:最多保留 `revision` + `updated` 两个字段

### ✅ 对抗式结论

**建议从 HTML 中移除 `history[]`**,理由:
1. spec 没要求(不在权威事实源中)
2. 当前没有任何代码读它(死代码)
3. _meta 应该极简(放真正影响解析的字段)
4. 审计能力应交给 issue tracker 而非 intent.json 自引用

如果一定要保留,改成更明确的命名 + 在 spec 中规定:
```jsonc
"_meta": {
  "schema_version": "3.0",
  "revision": 7,
  "created": "...",
  "updated": "...",
  "workspace": "..."
  // 不要写 history[]
}
```

**HTML 修法**: 删除 4864-4865 行(2 行)。`_meta` 只保留 `tool/schema_version/revision/created/updated/workspace` 6 字段。

### 推论:本次重构最大的"熵减"

`_meta.history[]` 是本次最容易被"因为有就留着"惯性影响而忽视的字段。**对抗式思维要求:每个字段都要被显式选择保留**,无消费者 = 删除。

---

## 汇总:6 项差异的最终建议

| # | 字段 | HTML 现状 | 推荐 spec | HTML 修法 | 备注 |
|---|---|---|---|---|---|
| 1 | `aspect_ratio_custom` | 有 | **新增** | 不变 | AI 路由表已要求 |
| 2 | `cover.type` | ai/text | ai/text/**image** | 加 image 选项 + 文件上传 | SKILL.md 已支持 image |
| 3 | `ending.type` | music-fade 等 4 项 | **6 项**(fade/freeze/next-day/next-episode-promo/next-week/text) | select 重写 | 与 AI 路由表对齐 |
| 4 | `version` / `schema_version` | `version: "0.7"` | `_meta.schema_version: "3.0"` + 可选 `_meta.tool_version` | 改字段名 + 写入 | 命名清晰分工 |
| 5 | `history[]` | 有 | **删** | 删 4864-4865 | spec 不要求,无消费者 |

### 后续 3 个必做项(本次重构要落实的)

1. **HTML `collectFormData` 加 `schema_version: "3.0"`** + 删 `version`/`history`(根本修复 #1、#4、#5)
2. **HTML `cover.type` select 增 `image` 选项** + 新增 `cover.images[]` 文件选择器(#2)
3. **HTML `ending.type` select 重写为 6 项统一枚举**(#3)

### spec 必须更新的三处

- spec §4 `output` 增 `aspect_ratio_custom`
- spec §4 `cover.type` 明确 image + 新增 `cover.images[]`
- spec §4 `ending.type` 明确 6 选 1 枚举

---

## 附录:对抗式方法学说明

| 思维陷阱 | 在本次的表现 | 克服方式 |
|---|---|---|
| "spec 是新写的,它对" | spec 模糊写"<6 种之一>" | 对照 AI 路由表/HTML 校验白名单 |
| "HTML 跑起来了,它对" | HTML `cover.type` 漏 image | 对照 SKILL.md 实装模块 |
| "AI 路由表是 AI 的圣经,它对" | AI 路由表说 `cover.type=image` 不支持 | 对照 SKILL.md 实装证明 |
| "大家都对,选个就行" | 三份 spec 都说 `ending.type` 但数值不同 | 不"投票",按**消费者需求**反推 |
| "没消费者就保留字段" | `history[]` 是个数组但谁都不读 | 显式选择"删" |
| "现在不用考虑将来的 AI" | 字段命名要兼顾下游解析 | 命名是一次性成本,改起来贵 |
