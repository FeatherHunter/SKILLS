# Grill-with-docs 移交清单 · 2026-07-29

> 本文件是 grill-with-docs 阶段的**收官文档**,供 to-spec 阶段直接消费。
> 包含 7 个已沉淀决策、待整合到 spec 的字段定稿清单、已知实现层偏移、移交清单。

---

## 阶段收官声明

**grill-with-docs(语言对齐)已完成,日期:2026-07-29**

输入:spec 蓝图 + HTML 实际产出 + SKILL.md/references 多份 md 文档,互相矛盾。
过程:对抗式审查,生成 5 份分析报告(mock JSON、对照报告、6 项差异深度分析、模板评审等)。
输出:**7 项已沉淀决策(D1-D7)** + 10 个 ending 模板 + CONTEXT.md 术语统一 + 已知实现层偏移清单(推到 implement 阶段)。

---

## D1-D7 决策汇总

| ID | 决策 | 影响 spec/HTML/md | 后续动作 |
|---|---|---|---|
| **D1** | 5 项 JSON 字段定稿 | spec §4 | HTML `collectFormData` 写入 + md 字段枚举表 |
| **D2** | ending 重构成 V4(`template` + `prompt`) | spec §4 ending 段 | HTML 新 select + md 协作协议 §3.1 改写 |
| **D3** | 10 个 ending 模板(标题 + 描述) | HTML UI 层(非 spec) | HTML 卡片设计 |
| **D4** | 只支持 v3.0,旧文件报错 | HTML + Python | HTML 加载时报错;`migrateLegacyIntent` 保留作参考但不启用 |
| **D5** | superpowers 移 `_archive/` | 文件系统 | 目录重命名动作(用户执行) |
| **D6** | md 优先(Layer 2A 在前) | 重构顺序 | to-spec 先写 md,再写 Python |
| **D7** | 5 个该消失的 op 严格删除 | spec §4 video_ops | HTML UI 移除 checkbox + Python 删解析逻辑 |

---

## D1 详解:5 项 JSON 字段定稿

| 字段 | 当前 spec | HTML 实际 | 修复动作 |
|---|---|---|---|
| `output.aspect_ratio` | "9:16 / 16:9 / custom" | "9:16 / 16:9 / 1:1 / 3:4 / 4:3 / custom" | spec 补 `1:1 / 3:4 / 4:3` |
| `output.aspect_ratio_custom` | 未列 | 有,写入 | spec 补:"W:H, aspect_ratio='custom' 时必填" |
| `output.aspect_handling` | "aspect-fit / aspect-fill" | "aspect-fit" 默认 | spec 补全 enum |
| `cover.type` | "ai / text / image" | 仅 "ai / text" | HTML select 加 `image` 选项 |
| `cover.prompt` | 自由文本 | 自由文本 | 不变 |
| `cover.images[]` | 未列 | 未列 | spec 新增:"仅 type='image' 时填写" |
| `_meta.schema_version` | 明确 `"3.0"` | **缺失**(collectFormData 不写) | HTML 必写入(强制) |
| `_meta.tool_version` | 可选 | `_meta.version: "0.7"` | HTML 改字段名;spec 明确"可选,与 schema_version 区分" |
| `_meta.history[]` | 不列 | 有,但无消费者 | HTML 删除(4864-4865 两行) |

---

## D2 详解:ending V4 重构

### V4 spec §4 字段

```jsonc
"ending": {
  "template": "<必填:选中的效果模板完整描述文本>",
  "prompt": "<可选:用户的额外补充说明>"
}
```

### V4 原理(写进 spec 注释)

1. **枚举退守** — 只在真正有限的离散空间保留 enum
2. **HTML 是 UX,不是 schema** — 模板的"种类"是 UX 层概念
3. **AI 路由推迟** — 让 AI 解析时再分类
4. **可演进 10 年** — 新 ending 创意只需加 HTML 模板

### 删除项(spec 不再列)

- `ending.type`(任何 enum 值)
- `ending.audio_strategy`(任何子字段)
- `ending.extras[]`(任何数组)
- `ending.kind`(任何分类)

### md 文档需要删除/改写的地方

| 文件 | 段落 | 动作 |
|---|---|---|
| `SKILL.md` | §4 ending.type 路由 | 整段删除 |
| `references/AI路由表-意图JSON字段枚举.md` | §1 ending.type 字段 | 删除整行 |
| `references/AI路由表-意图JSON字段枚举.md` | §3 ending.type 路由 | 整段改写(改成"读 template+prompt,按 §5 E 象限文本路由") |
| `references/AI协作协议-详细.md` | §3.1 ending.type 不在路由表 | 整段改写 |

---

## D3 详解:10 个 ending 模板

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

**注意**:这 10 个模板**不是 spec 字段**,只是 HTML UI 层的设计输入。

---

## D4 详解:兼容策略

- HTML 加载 v3.0 schema 文件 → 正常解析
- HTML 加载老 schema 文件 → 报错"请删除重填",**不做自动迁移**
- `migrateLegacyIntent` 函数保留在 HTML 中(作为参考文档),**不启用**

---

## D5 详解:superpowers 归档

**目录移动动作**(用户执行):
```
D:\2Study\StudyNotes\SKILLS\智剪工坊\
├── docs\superpowers\          ← 移到下面
│   ├── plans\
│   ├── specs\
│   └── (其他文件)
└── _archive\                  ← 新建(如果不存在)
    └── superpowers\           ← 目标位置
        ├── plans\
        ├── specs\
        └── (其他文件)
```

理由:`2026-07-25-video-time-segment-model.html` 等历史 spec 仍有参考价值,但不再作为生产指南。

---

## D6 详解:重构顺序

**先 md 文档层(Layer 2A),再 Python 编排层(Layer 2B)**。
理由:md 是 AI 行为的真实契约;Python 跟随 md 实现。

执行顺序:
1. 重写 `references/AI路由表-意图JSON字段枚举.md`(Layer 2A)
2. 重写 `references/AI协作协议-详细.md`(Layer 2A)
3. 重写 `SKILL.md`(Layer 2A)
4. 重写 `references/主流程-阶段编排.md`(Layer 2A)
5. 重写 `references/原子操作-14种基础剪辑指令.md`(Layer 2A)
6. **md 自洽后**,重写 `scripts/_internal/stage1_checklist.py`(Layer 2B)
7. 重写 `lib/video_processing.py`(Layer 2B)
8. 最后改 HTML `智剪工坊-意图编辑.html`(Layer 3,产出正确的 JSON)

---

## D7 详解:5 个该消失的 op

| op | HTML UI | video_ops JSON | 语义改由 |
|---|---|---|---|
| `trim-head` | 删除 checkbox | 永远不输出 | `time_segments[0].start_sec = N` |
| `trim-tail` | 删除 checkbox | 永远不输出 | `time_segments[last].end_sec = duration_sec - N` |
| `cut-middle` | 删除 checkbox | 永远不输出 | 创建相邻两个 time_segments,中间不进 JSON |
| `pin-range` | 删除 checkbox | 永远不输出 | 单个 time_segments 区间 |
| `target-duration` | 删除 checkbox | 永远不输出 | 拼接后时长 = 各段相加(无需声明) |

---

## 已知实现层偏移(implement 阶段处理)

以下 6 项**不阻塞 to-spec**,但 implement 阶段必须修:

| # | 偏移 | 文件位置 | 修复建议 |
|---|---|---|---|
| 1 | 拆段注入的 `user` op 污染段 ops | `智剪工坊-意图编辑.html` 5190 `SegmentState.addOrSplit` | 移除 `user` op 注入 |
| 2 | `collectFormData` 未过滤 excluded 段 | `智剪工坊-意图编辑.html` 4954-4960 | 加 `filter(s => !s.excluded)` |
| 3 | 段面板 `color` vs 校验白名单 `color-grade` | `智剪工坊-意图编辑.html` 5248 vs 5099 | 命名统一(待 grill 决定) |
| 4 | `_meta.tool_version` 写入 | `智剪工坊-意图编辑.html` 4867-4876 | 加 schema_version + 改 version 为 tool_version |
| 5 | 段 ID 格式 `seg_2_new_${ts}` | `智剪工坊-意图编辑.html` 5190 | 改为 `seg_${videoIdx}_${n}` |
| 6 | 加载老 schema 文件时报错信息 | `智剪工坊-意图编辑.html` 加载逻辑 | 实现 D4 报错 |

**注 3 仍需 grill 决策**:段内 op 的 `color` 究竟叫什么名字?需要与 D2 ending V4 一样的对抗式审查。

---

## To-spec 阶段启动指南

### 必备材料(已就绪)

- ✅ `CONTEXT.md` — 术语统一,所有阶段共享
- ✅ 本移交清单
- ✅ `2026-07-29-mock-spec-ideal.json` — V4 ending + D1 字段的样例输出
- ✅ `2026-07-29-deep-analysis-6-differences.md` — 决策背后的推理

### To-spec 阶段任务

1. 整合 D1-D7,产出 `intent.json v3.0` 字段定稿(spec §4 完整版)
2. 改写 `references/AI路由表-意图JSON字段枚举.md`(Layer 2A 优先)
3. 改写 `references/AI协作协议-详细.md`
4. 改写 `SKILL.md` 主文件
5. 改写其他 md 文档(主流程、原子操作、调用范式)
6. 准备 Python 编排层重写指引(给 implement 阶段)
7. 准备 HTML UI 改造清单(给 implement 阶段)

### 备注

**to-spec 阶段可以独立于本会话完成**。用户已声明"手动执行 to-spec",不需再开 grill-with-docs 会话延续。

---

## 移交声明

**grill-with-docs 阶段所有产物**:
- `CONTEXT.md` — 术语 + D1-D7 沉淀
- 本移交清单
- `2026-07-25-video-time-segment-model.html` — spec 主文件(已部分更新,D2 ending V4 已落地)
- `2026-07-29-json-audit-report.html` — 第一性原理审计
- `2026-07-29-mock-html-actual.json` + `2026-07-29-mock-spec-ideal.json` — 对比 mock
- `2026-07-29-mock-comparison-report.html` — mock 对比
- `2026-07-29-deep-analysis-6-differences.md` — 6 项深度分析

**下一步**:to-spec 阶段由用户手动执行(无需 grill-with-docs 续会)。

---

_Generated: 2026-07-29 · grill-with-docs 阶段收官 · D1-D7 全部沉淀_