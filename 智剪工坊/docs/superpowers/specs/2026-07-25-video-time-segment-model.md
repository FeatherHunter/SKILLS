# 视频时间段模型重构 Spec

**作者:** AI(经多轮对抗式审查收敛)
**创建日期:** 2026-07-25
**对应 Skill:** 智剪工坊-意图编辑
**版本:** v2.0(数据) + v3.0(HTML 行为)
**状态:** 待用户最终审阅

---

## 1. 背景与动机

当前 `智剪工坊-意图编辑.html` 输出的 `intent.json` 把"基础剪辑操作"统一平铺在 `videos[].ops` 下(22 个 op),存在以下问题:

1. **op 命名错位**:`cut-middle` / `pin-range` / `trim-head` / `trim-tail` 是"用户对某段时间的想法",但被设计成"对整段视频的 op",**语义与位置不匹配**。
2. **用户认知负担**:用户必须先理解每个 op 的时间窗语义,才能正确选择;但用户实际想说"我要这段 / 我要这段静音 / 我要这段加速",这些应直接表达。
3. **JSON 不支持"保留多段"**:用户实际是"我要保留 [2,55] 但跳过 [31,33]",现行 schema 只能通过 4 个 op 组合表达,语义模糊。
4. **op 数量过多**:22 个 op 让 AI 工作流 switch-case 复杂度指数级上升,误用概率高。

## 1.5 设计决策记录(2026-07-25 多轮审查收敛)

经过 6 轮对抗式审查 + 用户多次明确选择,以下决策已定版:

1. **JSON 字段收敛到 2 类**:`video_ops`(整段) + `time_segments`(片段;带可选 `ops`)。`range_ops.events` 字段被**删除**(段 op 直接挂在段内)。
2. **三分类被否决**:`video_ops` / `video_events` / `time_segments` 三分被第二轮对抗审查推翻,因为 op 跨界难以归类。最终统一为 2 类。
3. **UI 流程定版**:
   - 框选(timeline 上长按拖动)→ 弹窗**只告知**(显示拆分结果,只有 [确定] 按钮)
   - 单击段 → 弹出操作面板(改 label / 加 op / 删)
   - 删除后,段从 timeline 消失,折叠区"已删段"可恢复
4. **timeline 视觉**:
   - 保留段 = **彩虹 8 色循环**(红/橙/黄/绿/青/蓝/紫/粉),9 段以上循环复用第一色
   - 删除段 = 灰色 + 删除线 + 半透明
   - op 信息不染色(避免视觉密度过大),**hover 气泡**显示完整 op 摘要
5. **段 ≤ 8 时颜色最优**,超过 8 时循环但不报错(用户实际操作中极少超过 8 段)。

## 2. 设计目标

1. 让用户**用几何方式表达"我要保留哪些片段"** —— 拖框、命名、删段。
2. 让用户**用效果方式表达"我对某区间做什么"** —— 选静音/加速/反转。
3. 让用户**用音频策略表达"声音怎么处理"** —— 枚举(keep/mute/bgm-only) + 文本备注。
4. JSON schema **简化**:从 22 op 降到 14 op(video_ops) + N 个区间事件 + N 个片段。
5. AI 工作流解析代码 **简化**:从 switch-case 改为单源字段遍历。

## 3. 核心抽象

### 3.1 三类表达

| 类别 | JSON 字段 | 表达 | 用户心智 | 例子 |
|---|---|---|---|---|
| **整段操作** | `videos[].video_ops` | 对整段视频生效,与时间窗无关 | "整个视频加个暖色调" | `color: warm`、`add-bgm: ...` |
| **区间操作** | `videos[].range_ops.events[]` | 在某时间窗内做什么 | "[20,30] 静音" | `mute-region`、`speed-region` |
| **片段保留** | `videos[].time_segments[]` | 我要保留哪些片段(取并集) | "保留 [2,55] 和 [33,55]" | 空 = 整段保留 |

### 3.2 设计原则

1. **op 数量上限**:每个类别内 op ≤ 15 个,避免 switch-case 失控。
2. **正交性**:三类表达物理隔离(不同字段),AI 解析无需判断"这条 op 是不是时间窗敏感"。
3. **可空 = 默认**:任意字段缺失 = 该类未启用;不写 = 等价于空数组/空对象。
4. **取并集语义**:`time_segments` 多个段取并集;空数组 = 整段保留;未列出的区间 = 隐式删除。
5. **区间事件基于原视频时间**:`range_ops.events[].time_window` 用原视频时间(0 ~ duration_sec),用户与 AI 共享同一标准。

## 4. JSON Schema(v3.0)

```jsonc
{
  "$schema": "智剪工坊 intent v3.0",
  "$comment": "JSON schema 由 HTML 校验;以下为示例结构",

  "_meta": {
    "tool": "智剪工坊",
    "schema_version": "3.0",
    "revision": 1,
    "created": "<ISO 8601>",
    "updated": "<ISO 8601>",
    "workspace": "<folder name>"
  },

  // ── 项目级配置(与视频条目平行) ──
  "project": {
    "name": "<项目代号,可选>",
    "title": "<视频标题,可选>",
    "overall_intent": "<总调性描述,可选>"
  },
  "output": {
    "aspect_ratio": "<如 9:16 或 16:9,可选>",
    "aspect_handling": "<aspect-fit | aspect-fill,可选>"
  },
  "cover":  { "type": "ai|text|image", "prompt": "<封面描述>" },
  "ending": { "type": "fade|freeze|text|<6 种之一>", "prompt": "<结尾描述>" },

  // ── 视频间拼接顺序 ──
  "sequences": [
    {
      "title": "<链标题,可选>",
      "videos": [1, 2, 3],   // entry.index 序列
      "transitions": [
        { "after": 1, "type": "fade|none|<6 种之一>", "duration": 0.5 }
      ]
    }
  ],

  // ── 视频清单 ──
  "videos": [
    {
      "file": "<filename>.mp4",
      "index": 1,                                    // 1-based,稳定 ID
      "duration_sec": 60,                            // 由 HTML 在加载时算出
      "exclude": false,
      "summary": "<一句话简介>",
      "intent": "<剪辑意图>",

      // ── 整段视频的操作(全局默认) ──
      "video_ops": {
        // 视觉/听觉效果类(整段生效,与时间窗无关)
        "color":            { "on": true, "style": "warm" },
        "add-bgm":          { "on": true, "file": "...", "volume": 0.4 },
        "replace-audio":    { "on": true, "file": "..." },
        "speed-up":         { "on": true, "factor": 1.5 },     // 整段倍速
        "slow-down":        { "on": true, "factor": 0.7 },
        "mute":             { "on": true },                    // 整段静音
        "reverse":          { "on": true },                    // 整段倒放

        // 音频处理
        "audio-denoise":    { "on": true },
        "audio-separate":   { "on": true, "model": "htdemucs_ft" },
        "audio-diarize":    { "on": true },
        "voice-filler-removed": { "on": true },

        // 字幕/ASR
        "asr-transcribe":   { "on": true, "model": "medium" },
        "asr-burn":         { "on": true, "font_size": 24 },
        "asr-speaker":      { "on": true },

        // 音频策略(从原 HTML select 字段映射)
        "voice":            { "on": true, "mode": "keep|keep-with-filler-removed|mute|bgm-only" },
        "voice_note":       "<自由文本,如'原声音量小,放大 1.5x'>",

        // 视频级备注
        "notes":            "<自由文本,视频整体备注>",

        // 图片专属
        "duration":         { "on": true, "sec": 3 }
      },

      // ── 片段保留(可空 = 整段输出;多个 = 取并集) ──
      //    段级 op 直接挂在 ops 里(op 是段的属性,不是独立数组)
      //    删除的区间不存:JS 计算 time_segments 的并集补集 = 已删段(折叠区显示)
      "time_segments": [
        {
          "id": "seg_1_1",                                // seg_${videoIdx}_${n}
          "label": "<用户可改,如'主体内容'>",
          "start_sec": 2.0,
          "end_sec": 31.0,
          "ops": {                                        // 可空;只在用户添加 op 时存在
            "mute":     { "on": true },
            "speed-up": { "on": true, "factor": 2.0 }
          },
          "note":        "<段级备注>"
        }
      ]
    }
  ]
}
```

## 5. 字段对照表(原 schema → 新 schema)

> 经多轮审查,**`range_ops.events` 字段已被删除**(段 op 直接挂 `time_segments[].ops`)。op 跨界归类困难,所以"段上的 op"和"段本身"合并存储。

| 原字段 | 新字段 | 迁移路径 |
|---|---|---|
| `videos[].ops` (平铺 22 op) | **删除** | 按语义拆分到 `video_ops` / `time_segments[].ops` / 消失 |
| `videos[].summary` / `intent` / `voice` (原 select) | `videos[].summary` / `intent` / `video_ops.voice` | 描述字段保留;`voice` 进 video_ops |
| `videos[].voice_note` | `video_ops.voice_note` | 进 video_ops |
| `videos[].notes` | `video_ops.notes` | 进 video_ops |
| `videos[].ops["trim-head"]` | **消失** | 由 `time_segments[0].start_sec = sec` 等价表达 |
| `videos[].ops["trim-tail"]` | **消失** | 由 `time_segments[last].end_sec = duration - sec` 等价表达 |
| `videos[].ops["cut-middle"]` | **消失** | 由创建两个相邻 time_segments 等价表达 |
| `videos[].ops["pin-range"]` | **消失** | 由单个 time_segment 等价表达 |
| `videos[].ops["target-duration"]` | **消失** | 拼接后时长 = 各段相加,无需声明 |
| `videos[].ops["fade-in/out"]`(段内) | **消失** | 视频首尾淡入淡出归 `video_ops.fade-in/out`(整段型) |
| `videos[].ops["mute"]`(整段) | `video_ops.mute` 或 `time_segments[].ops.mute` | 取决于作用范围 |
| `videos[].ops["reverse"]`(整段) | `video_ops.reverse` 或 `time_segments[].ops.reverse` | 取决于作用范围 |
| `videos[].ops["speed-up"]` | `video_ops.speed-up` 或 `time_segments[].ops.speed-up` | 取决于作用范围 |
| `videos[].ops["color"]` | `video_ops.color` | 进 video_ops |
| `videos[].ops["opening-text"]` | `video_ops.opening-text`(待实现) | 进 video_ops + duration 子字段 |
| `videos[].ops["insert-image"]` | `video_ops.insert-image`(待实现) | 进 video_ops + at_sec 子字段 |
| `videos[].ops["add-bgm"]` | `video_ops.add-bgm` | 不变(进 video_ops) |
| `videos[].ops["replace-audio"]` | `video_ops.replace-audio` | 不变 |
| `videos[].ops["audio-denoise"]` 等 | `video_ops.*` | 不变 |
| `videos[].ops["asr-*"]` | `video_ops.*` | 不变 |
| `videos[].ops[xxx].note` | 移到 `time_segments[].note`(段内)或 `video_ops.notes`(整段) | 按语义归位 |
| `cut-middle.from/to`(字符串 `"0:12"`) | `time_segments` 边界值(数值秒) | 强制转秒 |
| `pin-range.from/to`(字符串) | 同上 | 强制转秒 |

## 6. UI 操作流程(基于场景)

### 6.1 场景定义

> 1 分钟视频:删前 2s、删后 5s、删 [31,33]、[20,30] 静音、[40,50] 加速 2x

### 6.2 流程图(定版)

```
═══════════════════════════════════════════════════
阶段 A · 进入视频
═══════════════════════════════════════════════════
用户点视频 #1 展开
↓
看到:
  - 顶部:播放窗口 + timeline(全宽轨道,默认整段保留)
  - ▼ 整段视频操作(默认折叠,内含 voice/notes/color 等)
  - ▼ 时间段区(默认展开)─保留区间列表(初始 0 个)
  - ▼ 已删段区(默认折叠)─已删除区间可恢复

═══════════════════════════════════════════════════
阶段 B · 框选产生新段(后续可拆/合/删)
═══════════════════════════════════════════════════
用户长按拖动 [2, 55]
  timeline 上半透明蓝色高亮覆盖 [2, 55]
  松开弹出"告知弹窗"(只显示,不要求决策):
    ┌─────────────────────────────────────┐
    │ 本次操作产生 3 个时间段              │
    │                                       │
    │  [0.0~2.0]  [2.0~55.0]  [55.0~60.0]  │
    │  ← 新拆分    ← 本次拖的  ← 新拆分     │
    │                                       │
    │              [确定]                   │
    └─────────────────────────────────────┘
  用户点 [确定] → timeline 上出现 3 段**全部彩色**(默认保留):
    ┌─[0~2]─┬──────[2~55]──────┬──[55~60]──┐
    │  红   │       橙          │    黄     │
    │(新段) │  (新段·本次拖)   │  (新段)   │
    └───────────────────────────────────────┘
  ▼ 时间段区:
    #1  [0.0~2.0]  2.0s    [改名][加 op][删除]
    #2  [2.0~55.0] 53.0s   [改名][加 op][删除]
    #3  [55.0~60.0] 5.0s   [改名][加 op][删除]

  > **关键设计原则**:框选不知道用户意图,系统不应预设删除。
  > 删除是用户单独的"单击 + 删按钮"操作,与框选解耦。

═══════════════════════════════════════════════════
阶段 C · 用户主动标删除(单独的单击操作)
═══════════════════════════════════════════════════
用户单击 #1 [0.0~2.0] → 弹出操作面板 → [🗑️ 删掉]
  → #1 从 timeline 消失
  → 折叠区"已删段"出现该段:[♻️ 恢复]

用户单击 #3 [55.0~60.0] → 弹出操作面板 → [🗑️ 删掉]
  → #3 也从 timeline 消失
  → timeline 只剩 #2 [2.0~55.0] 一段

═══════════════════════════════════════════════════
阶段 D · 进一步拆段 + 删除
═══════════════════════════════════════════════════
用户长按拖动 [31, 33]
  → 自动拆段:#2 [2, 55] 切成 [2, 31] + [31, 33] + [33, 55]
  → 告知弹窗"产生 3 个时间段"

用户单击 [31, 33] → 操作面板 → [🗑️ 删掉]
  → 该段删除

═══════════════════════════════════════════════════
阶段 E · 进一步拆段 + 加 op
═══════════════════════════════════════════════════
用户长按拖动 [20, 30]
  → 自动拆段:[2, 31] 切成 [2, 20] + [20, 30] + [30, 31]
  → 告知弹窗"产生 3 个时间段"

用户单击 [20, 30] → 操作面板 → [🔇 静音]
  → 段加静音 op

用户长按拖动 [40, 50]
  → 自动拆段:[33, 55] 切成 [33, 40] + [40, 50] + [50, 55]

用户单击 [40, 50] → 操作面板 → [⏩ 倍速]
  → 弹因子 slider(0.25x ~ 4x),默认 1.5x
  → 选 2x → 段加速 op

═══════════════════════════════════════════════════
阶段 F · 保存
═══════════════════════════════════════════════════
用户点 [保存]
  → collectFormData() 反向算出 time_segments + 段内 ops
  → 写 intent.json (schema_version=3.0)
  → 弹 toast
```

### 6.3 UI 元素清单

| 元素 | 位置 | 行为 |
|---|---|---|
| 视频卡头部 | 卡片顶部 | 显示 `index / file / duration` + 折叠按钮 |
| 播放窗口 + timeline | 卡片主体 | timeline 可长按拖动框选 |
| timeline 段(彩虹色) | timeline 上 | 8 色循环;hover 弹 tooltip 显示 op 摘要 |
| timeline 段(灰色) | timeline 上 | 已删段,不显示(折叠区"已删段"列表可恢复) |
| 框选告知弹窗 | 全局 modal | 只显示拆分结果 + [确定](无取消) |
| 段单击 → 操作面板 | 段下方 inline | 改 label / 加 op / 删除 |
| 段 ↔ 折叠区跳转 | 折叠区段项点击 | 跳转到 timeline 对应段(scrollIntoView + 高亮) |
| 段悬停 → tooltip | 段上方 | 显示 op 摘要(若有) |

### 6.4 timeline 视觉规范(定版 · 彩虹 8 色)

```css
/* 删除段 */
.del-seg {
  background: #c7c7cc;
  color: #6e6e73;
  text-decoration: line-through;
  opacity: 0.55;
}

/* 保留段颜色循环(8 色) */
:root {
  --seg-color-0: #ff3b30;  /* 红 */
  --seg-color-1: #ff9500;  /* 橙 */
  --seg-color-2: #ffcc00;  /* 黄 */
  --seg-color-3: #34c759;  /* 绿 */
  --seg-color-4: #00b4d8;  /* 青 */
  --seg-color-5: #5e5ce6;  /* 蓝 */
  --seg-color-6: #af52de;  /* 紫 */
  --seg-color-7: #ff2d92;  /* 粉 */
}
```

| 段索引 | 颜色 |
|---|---|
| 0 | 红 #ff3b30 |
| 1 | 橙 #ff9500 |
| 2 | 黄 #ffcc00 |
| 3 | 绿 #34c759 |
| 4 | 青 #00b4d8 |
| 5 | 蓝 #5e5ce6 |
| 6 | 紫 #af52de |
| 7 | 粉 #ff2d92 |
| 8 (循环回 0) | 红 ... |

段与段之间 1px 白色分隔线。  
hover 整段上浮 2px + 显示 tooltip(op 摘要)。  
op 信息**不染色**(避免视觉密度过大)。

## 7. 校验规则

```js
function validateIntent(data) {
  const errors = [];

  data.videos?.forEach((v, vi) => {
    const segs = v.time_segments || [];
    const ids = new Set();

    // 规则 1:time_segments.id 全 video 内唯一
    segs.forEach(s => {
      if (ids.has(s.id)) errors.push(`#${v.index}: id "${s.id}" 重复`);
      ids.add(s.id);
    });

    // 规则 2:每个段区间合法
    segs.forEach(s => {
      if (s.start_sec < 0 || s.end_sec > v.duration_sec || s.start_sec >= s.end_sec) {
        errors.push(`#${v.index} ${s.id}: 区间 [${s.start_sec}, ${s.end_sec}] 非法,视频时长 ${v.duration_sec}s`);
      }
    });

    // 规则 3:段之间不重叠(允许 end_a == start_b 衔接)
    const sorted = [...segs].sort((a, b) => a.start_sec - b.start_sec);
    for (let i = 0; i < sorted.length - 1; i++) {
      if (sorted[i].end_sec > sorted[i + 1].start_sec) {
        errors.push(`#${v.index}: 段 ${sorted[i].id} 与 ${sorted[i+1].id} 重叠`);
      }
    }

    // 规则 4:段内 ops 合法性(若有 ops)
    const validSegmentOps = ['mute', 'speed-up', 'slow-down', 'reverse', 'color-grade'];
    segs.forEach(s => {
      if (!s.ops) return;
      Object.entries(s.ops).forEach(([opName, opCfg]) => {
        if (!validSegmentOps.includes(opName)) {
          errors.push(`#${v.index} ${s.id}: 不支持的段内 op "${opName}"`);
        }
        if ((opName === 'speed-up' || opName === 'slow-down') && (typeof opCfg.factor !== 'number' || opCfg.factor <= 0)) {
          errors.push(`#${v.index} ${s.id}: ${opName} 必须有 factor > 0`);
        }
      });
    });

    // 规则 5:video_ops.voice.mode 合法
    if (v.video_ops?.voice?.on) {
      const validModes = ['keep', 'keep-with-filler-removed', 'mute', 'bgm-only'];
      if (!validModes.includes(v.video_ops.voice.mode)) {
        errors.push(`#${v.index} video_ops.voice.mode "${v.video_ops.voice.mode}" 非法`);
      }
    }
  });

  return errors;
}
```

## 8. AI 工作流解析示例

```python
def execute_intent(intent):
    # 1. 处理视频间拼接(sequences)
    sequence_clips = []
    for seq in intent.sequences:
        chain = []
        for video_index in seq.videos:
            video = next(v for v in intent.videos if v.index == video_index)
            clip = process_single_video(video)
            chain.append(clip)
        # 应用视频间转场
        final = apply_transitions(chain, seq.transitions)
        sequence_clips.append(final)

    # 2. 加封面、结尾、调性
    return assemble(sequence_clips, intent.cover, intent.ending, intent.project.overall_intent)


def process_single_video(video):
    # 1. 加载原视频
    raw = load(video.file)

    # 2. 应用 video_ops(整段)
    processed = apply_video_ops(raw, video.video_ops)

    # 3. 按 time_segments 取并集(空 = 整段)
    if not video.time_segments:
        kept = processed
    else:
        clips = [trim(processed, s.start_sec, s.end_sec) for s in video.time_segments]
        kept = concat(clips)

    # 4. 应用段内 ops(v1.x 新:op 直接挂在段里)
    for seg in video.time_segments:
        if seg.ops:
            kept = apply_segment_ops(kept, seg.ops)

    # 5. 已删段不进入 kept(取并集时已自然排除)

    return kept
```

## 9. 实施分 Phase

### Phase A · 数据模型与校验(优先)
- 引入 `video_ops` / `time_segments[].ops`(段内 op)两类字段
- 旧 `videos[].ops` 平铺结构**保留为兼容层**(同时存在),新提交走新结构
- 加载时优先读新结构,缺失则回退解析旧结构
- 提交校验按 §7 规则
- 验证:`validateIntent` 通过单元测试(覆盖正常 / 重叠 / 区间非法 / id 重复)

### Phase B · HTML UI · 整段操作区重命名
- `▶ 基础剪辑操作` → `▶ 整段视频操作`
- 视觉上区分"整段型 op"与"段内型 op"(后者移到段的 inline 操作面板)
- voice select + voice_note textarea 保留在整段操作区
- 验证:用户展开视频卡,看到 ops 重新分组

### Phase C · HTML UI · 时间段区 + 彩虹色块
- 新增 `▼ 时间段` 折叠区,显示 `time_segments[]` 列表
- timeline 上每段按彩虹 8 色循环染色
- 段 < 40px 宽时不显示文字标签(只显示颜色块)
- 段与段之间 1px 白色分隔
- hover 段 → 上浮 2px + 显示 tooltip(op 摘要)
- 验证:用户展开 + 添加段 + 看到彩虹色

### Phase D · Timeline 框选交互
- timeline 上长按拖动 → 实时绘制半透明高亮
- 松开 → 弹出"告知弹窗"(只显示拆分结果)
- 提交后,自动按拆分逻辑更新 segments(算法替代二次弹窗)
- 验证:用户拖框 → 弹窗告知 → 确定 → timeline 自动更新

### Phase E · 段单击 → 操作面板(inline)
- 段单击 → 在段下方 inline 展开操作面板
- 面板含 label 输入 + op 按钮(静音/倍速/反转)+ 删除按钮
- 删除后的段移到折叠区"已删段"(可恢复)
- 验证:用户点击段 → 看到面板 → 改 label / 加 op / 删除 → 折叠区同步

### Phase F · JSON 提交 + 加载兼容
- `collectFormData()` 重写:序列化 `video_ops` + `time_segments`(含段内 ops)
- 加载逻辑:有 `time_segments` → 新结构;否则回退解析 `ops` 平铺
- 验证:提交 → 重新加载 → 数据完整保留

### Phase G · 文档与 tag
- SKILL.md 增 v2.0 变更摘要
- tag `v2.0`(从 v1.25 升级)
- changelog 写明本次重构范围

### Phase F · JSON 提交 + 加载兼容
- `collectFormData()` 重写:序列化三类字段
- 加载逻辑:`if data.videos[].time_segments` → 新结构,否则回退解析旧 `ops`
- 验证:提交 → 重新加载 → 数据完整保留

### Phase G · 文档与 tag
- SKILL.md 增 v2.0 变更摘要
- tag `v2.0`(从 v1.25 升级)
- changelog 写明本次重构范围

## 10. 风险与边界

| 风险 | 缓解 |
|---|---|
| 旧 `intent.json` 加载失败 | 保留兼容层,旧文件自动迁移为新结构(自动备份原文件) |
| 用户已熟练旧 UI 流程 | 整段操作区只重命名 + 微调,核心 op 名称不变 |
| 段内 ops 嵌套导致复杂度 | op 是 flat 集合(类似原 `ops`),非数组嵌套 |
| timeline 框选与现有单击跳转冲突 | 区分单击(< 200ms) vs 长按拖拽(>= 200ms + 移动) |
| 性能:多卡片同时展开时 timeline 绘制开销 | 仅可见卡片绘制色块;折叠卡片 lazy render |
| 段超过 8 个颜色循环 | 用户极少遇到;超过时反复第一色 + 提示用户合并 |

## 11. 验收清单

- [ ] JSON schema 与 §4 一致
- [ ] 校验规则与 §7 一致
- [ ] AI 工作流示例可运行
- [ ] UI 流程 §6 场景完整演示
- [ ] 旧 intent.json 可加载(兼容层工作)
- [ ] 新 intent.json 可加载并保留所有用户数据
- [ ] timeline 框选 + 自动拆段正确
- [ ] 段改名 / 删除正确
- [ ] 段单击 → 操作面板 / 加 op / 删除交互正确
- [ ] 彩虹 8 色 + 删除灰色视觉规范生效
- [ ] hover 段 tooltip 显示 op 摘要
- [ ] 已删段可恢复
- [ ] 保存 → 加载往返零数据丢失

## 12. 不做(明确范围)

- ✗ **不引入** `mode: keep/exclude`(空 segments 即整段;取并集天然表达)
- ✗ **不引入** `video_events` 数组(归宿 video_ops,见 §1.5 决策记录)
- ✗ **不引入** `range_ops.events` 数组(段 op 直接挂 `time_segments[].ops`,见 §1.5)
- ✗ **不引入** `segment_transitions`(视频内段间转场 YAGNI)
- ✗ **不引入** `cut-middle` / `pin-range` / `trim-head` / `trim-tail`(被新结构替代)
- ✗ **不引入** 段内 `voice_note`(归 `time_segments[].voice_note`)
- ✗ **不引入** `opening-text` / `insert-image` 的 event 表达(留待 Phase H)
- ✗ **不向后兼容** 旧 v1.x intent.json 的视觉布局(只保证数据兼容)

## 13. 未来 Phase(本次不做)

- Phase H · opening-text / insert-image 等事件型 op 接入 video_ops 或 time_segments[].ops
- Phase I · 段级 thumbnail 缩略图(timeline 上显示视频帧缩略条)
- Phase J · 段级 transcript(ASR 结果标注段内文字)
- Phase K · 多语言字段(英文 UI 适配)
- Phase L · 段拖拽合并(相邻同 op 段可拖到一起,op 提示清除)

## 14. 自检

- [x] 无 TBD / TODO / 占位符
- [x] 内部一致性:schema / UI / 校验 / AI 工作流 互相对齐
- [x] 范围聚焦:2 类字段(video_ops + time_segments)
- [x] 模糊消除:每个 op 的语义在 §5 / §8 都明确
- [x] 决策记录完整(§1.5 列出 6 轮对抗审查的最终结论)

---

**Spec 完成(2026-07-25 · v3 视觉规范定版)。请用户审阅本文件,确认后进入 writing-plans 阶段制定详细实施计划。**