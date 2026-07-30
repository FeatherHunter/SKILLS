# 02 — ADR 撰写:D1-D7 + D8 + D9 转正式 ADR + D11 纲领

**What to build:**
8 个 D 决策(D1-D7 + D8 + D9)转正式 ADR,新建 `docs/adr/` 目录并写入 9 个 markdown 文件(0001-0009)。完成后,任何工程师查阅 `docs/adr/` 都能理解 v3.0 决策的"为什么",无需翻 git history 或 CONTEXT.md。

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

### 验收标准

- [ ] 创建 `docs/adr/` 目录(目录不存在,本工单首次创建)
- [ ] 写入 9 个文件:
  - [ ] `0001-v3-schema-version.md`(D1)
  - [ ] `0002-ending-v4-template.md`(D2)
  - [ ] `0003-only-v3-schema.md`(D4)
  - [ ] `0004-archive-superpowers.md`(D5)
  - [ ] `0005-md-first.md`(D6)
  - [ ] `0006-trim-cuts-deprecated.md`(D7)
  - [ ] `0007-color-op-no-grade.md`(D8)
  - [ ] `0008-segment-id-format.md`(D9)
  - [ ] `0009-v3-principles.md`(D11,纲领)
- [ ] 每篇 ADR 正文 1-3 句话,可选 `Status: accepted` frontmatter
- [ ] 每篇 ADR 第一句话**清楚说明"什么决策 + 为什么"**(ADR 模板核心)
- [ ] 引用 CONTEXT.md 中对应 D 决策作为依据
- [ ] 无 TBD / 占位 / "TODO: 补充"
- [ ] D3(10 个模板)是 UX 决策,**不入 ADR**(spec §3 即可)
- [ ] **不重写 CONTEXT.md**(留给后续工单;本次只在 ADR 沉淀)

### 实现细节(供 agent 参考)

- **0001-v3-schema-version.md**(D1):
  ```
  intent.json 必须含 `_meta.schema_version: "3.0"`(必填),可选含 `_meta.tool_version`(产品版本)。
  AI 解析时凭 schema_version 决定走 v3.0 解析逻辑;tool_version 区分产品发布号与契约号。
  老的 `_meta.version` / 顶层 `version` 全部删除。
  ```

- **0002-ending-v4-template.md**(D2):
  ```
  ending 字段重构成 `{template, prompt}` 两文本字段,抛弃 6 选 1 enum。
  原理:枚举退守(只在真离散空间保留 enum)、HTML 是 UX 不是 schema、AI 路由推迟(让 AI 解析时再分类)、可演进 10 年。
  ending.template 必填(HTML 选中模板的人话描述),ending.prompt 可选(用户补充说明)。
  AI 按 §5 E 象限文本路由规则把 template+prompt 解析为 CLI 步骤。
  ```

- **0003-only-v3-schema.md**(D4):
  ```
  智剪工坊 v3.0 只支持 `_meta.schema_version="3.0"`。
  加载老 schema 文件(缺失或非 "3.0")时直接报错"请删除重填",不做自动迁移。
  理由:简单明确;`migrateLegacyIntent` 函数保留作为参考但不启用。
  ```

- **0004-archive-superpowers.md**(D5):
  ```
  仓库的 `docs/superpowers/` 整体移到 `_archive/superpowers/`。
  理由:旧(superpowers)技能流不再使用;历史产物(如 2026-07-25-video-time-segment-model.html)有参考价值,但不应作为生产指南。
  ```

- **0005-md-first.md**(D6):
  ```
  SKILL 重构顺序:md 文档层(Layer 2A)优先,Python 编排层(Layer 2B)跟随。
  理由:md 是 AI 行为的真实契约;Python 是机器实现。AI 看 md 实现代码——先让 md 自洽,再让 Python 实现对齐 md。
  ```

- **0006-trim-cuts-deprecated.md**(D7):
  ```
  intent.json v3.0 不再包含以下 5 个 op:
  - trim-head / trim-tail / cut-middle / pin-range / target-duration
  语义改由 `videos[i].time_segments[]` 边界表达:
  - trim-head sec=N ≡ time_segments[0].start_sec = N
  - trim-tail sec=N ≡ time_segments[last].end_sec = duration_sec - N
  - cut-middle [X,Y] ≡ 创建相邻两个 time_segments,中间不进 JSON
  - pin-range [X,Y] ≡ 单个 time_segments 区间
  - target-duration ≡ 拼接后时长 = 各段相加(无需声明)
  HTML UI 移除对应 checkbox;JSON Schema 拒绝(validateIntent 拒绝)。
  ```

- **0007-color-op-no-grade.md**(D8):
  ```
  段内调色 op 命名为 `color`(不带 `-grade` 后缀)。
  理由:`color-grade` 的 `grade` 后缀语义模糊(中文读者第一反应"等级"而非"调色")。
  命名统一后:HTML / spec / JSON Schema / AI 路由表四方零冲突。
  spec §7 段内白名单:['mute', 'speed-up', 'slow-down', 'reverse', 'color']。
  ```

- **0008-segment-id-format.md**(D9):
  ```
  time_segments[].id 格式:`seg_${videoIdx}_${n}`。
  - videoIdx:视频索引(1-based,entry.index)
  - n:段在该视频内的序号(从 1 递增,seg_${videoIdx}_1 / _2 / _3...)
  理由:可读、AI 友好、天然排序。JSON Schema id pattern 强制 `^seg_[0-9]+_[0-9]+$`。
  HTML addOrSplit 用 SegmentState 内部 nextN 计数器分配新段 id。
  ```

- **0009-v3-principles.md**(D11,纲领):
  ```
  智剪工坊 v3.0 重构的最高指导原则:
  "HTML 开发完善 → 用户编辑产生正确 JSON → 用户和 AI 确认 JSON 已好
   → AI 按工作流指引开始解析 JSON → AI 调用 atomic CLI 和 py 脚本对视频处理。
   不会出现 'python 完全不处理' 的情况。任何小 bug 必须修复,不留尾巴。"

  分工:
  - HTML 负责 UI 收集 + 写正确 JSON
  - JSON 协议层(spec §4 + intent_v3.schema.json)是契约
  - md 文档是 AI 行为的真实契约
  - AI 按 md 指引 + atomic CLI 文档,自己组合 ffmpeg 命令
  - Python lib/video_processing.py 负责整段 video_ops 编排(非段内)
  - atomic CLI 是单 op 工具
  - 任何"python 不处理"的判断都是错的(要么整段处理,要么 AI 组合)
  - 任何小 bug 必须修复,不留尾巴
  ```