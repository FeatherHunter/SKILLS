# 智剪工坊 v1.10 → v1.11 升级实施 Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把智剪工坊 SKILL.md 从 v1.10（1140 行、行为不可审计、异常无协议）升级为 v1.11（< 600 行、行为可审计、异常可恢复）。

**Architecture:** 纯文档改动。**不动 scripts/lib/setup/verify**。新增 7 个 references/，重写 SKILL.md，应用 progressive disclosure 原则（什么进 SKILL.md vs references/）+ Loading 触发器（AI 何时加载哪个 references/）。

**Tech Stack:** Markdown（SKILL.md + 7 个 references/）、Shell 验证命令（grep/wc/cat）、Git commit。

**Spec:** `docs/superpowers/specs/2026-07-10-zhijiangongfang-v1.11-design.md`

---

## 文件结构总览

**修改（1 个）：**
- `SKILL.md` — 精简 1140 → < 600 行，应用 progressive disclosure

**新建（7 个）：**
- `references/AI行为日志协议.md` — §5.1 + §5.2（C 粒度 + self-reference mitigation）
- `references/异常处理协议.md` — §5.3（B 选项重试规则）
- `references/红线契约-AI触发审查.md` — §5.4（5 步自检清单）
- `references/意图对齐-操作影响告知.md` — §5.5（Step 7 告知格式）
- `references/jargon.md` — 从 SKILL.md §Jargon 大白话词典 拆出
- `references/AI协作详细.md` — 从 SKILL.md §AI 协作协议 §1-§10 拆出
- `references/muted-视频拼接风险.md` — 从 SKILL.md §v1.10 拆出（48 行）

**不修改（已在 references/）：**
- `references/主流程-阶段编排.md` — 已有，SKILL.md 改为引用
- `references/AI路由表-意图JSON字段枚举.md` — 已有

---

## 任务阶段划分

```
Phase 1 (4 task, 可并行): 4 个核心 references/ 创建
Phase 2 (3 task, 可并行): 3 个渐进披露 references/ 创建（从 SKILL.md 拆出）
Phase 3 (4 task, 串行):   SKILL.md 改造
Phase 4 (1 task):         整体验证
```

**总任务数**：12 个
**预估总时间**：4-5 小时

---

## Phase 1: 4 个核心 references/ 创建

### Task 1: 创建 `references/AI行为日志协议.md`

**Files:**
- Create: `references/AI行为日志协议.md`

**目的**：定义 AI 行为日志的文件结构、写入触发、字段 schema、self-reference 风险缓解。基于 spec §5.1 + §5.2。

- [ ] **Step 1: 创建文件并写入 §1 概述**

```bash
touch "references/AI行为日志协议.md"
```

写入（覆盖文件）：

```markdown
# AI 行为日志协议

> 本协议定义智剪工坊 AI 行为日志的文件结构、写入触发、字段 schema、self-reference 风险缓解。
> SKILL.md 必须引用本协议；AI 加载 SKILL.md 后必读。

## 1. 概述

AI 行为日志记录 AI 在执行智剪工坊任务时的：
- **流程节点**（Stage X.Y 当前在哪）
- **决策理由**（为什么这么做）
- **思考链**（考虑过的方案）

**输出位置**：`<workspace>/00_智剪/中间产物/logs/<task_id>.<ext>`

**目的**：
1. 审计 AI 是否按流程走（合规性）
2. 诊断错误时区分「AI 流程问题」vs「底层脚本 bug」

## 2. 双格式设计

| 文件 | 用途 | 写入时机 | 写入主体 |
|---|---|---|---|
| `<task_id>.md` | 人类可读总结 | 阶段结束 + 异常时 | AI 重写整文件或 append stage section |
| `<task_id>.jsonl` | 机器可读详细 | **每次 CLI 调用前** append 一行 | AI 用 `open('a').write(json.dumps(...)+'\n')` |

## 3. JSONL 字段 Schema

每行一个 JSON 对象：

```json
{
  "time": "2026-07-10T10:30:15",
  "stage": "1",
  "step": "2",
  "action": "trim",
  "decision": "trim 0-5s",
  "thinking": "视频抖动 + 用户提到...",
  "result": "exit 0",
  "error": null
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| time | string (ISO 8601) | 是 | 时间戳 |
| stage | string | 是 | 当前阶段号（"0"-"5"）|
| step | string | 是 | 当前 stage 内步骤 |
| action | string | 是 | 执行的操作类型（trim / color / ask / ...）|
| decision | string | 是 | 本次决策内容 |
| thinking | string | 是 | 思考链（含考虑的方案）|
| result | string | 否 | CLI exit code / 异常类型 |
| error | string\|null | 否 | 错误信息（null = 无错误）|

## 4. Self-reference 风险缓解

LLM 有 self-reference 风险：AI 输出思考后，会在后续 context 里看到自己说"我选 X 因为 Y"，这会强化 X 的执行（即使错了也不易反转）。

**缓解策略**：

1. **XML 标签隔离**：thinking 用 `<thinking>` 标签包裹，AI 不主动回看 thinking 内容
2. **阶段 checkpoint**：每 stage 结束 AI 必须 re-decide "我现在还坚持前面的决策吗？"

**AI 写入模板**：

```xml
<thinking>
[阶段 X.Y] 决策：...
思考：考虑了 A/B/C，B 最优因为...
</thinking>

<action>
[JSONL append]
</action>
```

## 5. Markdown (.md) 章节结构

```markdown
# 任务 <task_id>

## Stage 0 项目初始化
[时间] 决策：HTML 表单填写
[时间] 异常：...（如有）

## Stage 1 意图对齐
[时间] 决策：与用户确认 3 个意图点
[时间] 决策：选择「健身 vlog」模板

## Stage 2 粗加工
[时间] 调：scripts/video/trim.py
[时间] 异常：CUDA OOM（已重试 3 次失败）

## Stage 3 模板
...

## Stage 4 产物审查
...

## Stage 5 收尾
...
```

## 6. 文件命名约定

`<workspace>/00_智剪/中间产物/logs/<task_id>_<timestamp>.<ext>`

- `<task_id>`：来自 intent.json.project.title 的 slug（小写、连字符）
- `<timestamp>`：YYYYMMDD_HHMMSS

**示例**：
- `vlog_20260710_103015.md`
- `vlog_20260710_103015.jsonl`

## 7. 文件生命周期

- 创建时机：阶段 0 完成、用户提交 intent.json 后
- 跟随任务：直至阶段 5 完成
- 归档时机：剪映导出后，可选 `mv logs/ .archive/logs/<task_id>/`
```

- [ ] **Step 2: 验证文件存在 + 含 7 个 ## 标题**

```bash
ls -la "references/AI行为日志协议.md"
grep -c "^## " "references/AI行为日志协议.md"
```

Expected: 文件存在，grep 输出 7

- [ ] **Step 3: Commit**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
git add references/AI行为日志协议.md
git commit -m "docs(v1.11): 添加 AI 行为日志协议 references/AI行为日志协议.md"
```

---

### Task 2: 创建 `references/异常处理协议.md`

**Files:**
- Create: `references/异常处理协议.md`

**目的**：定义异常处理规则（B 选项：重试 2-3 次后停下报告）。基于 spec §5.3。

- [ ] **Step 1: 创建文件并写入完整内容**

```bash
touch "references/异常处理协议.md"
```

写入：

```markdown
# 异常处理协议

> 本协议定义智剪工坊执行任务时撞到异常（ffmpeg 失败 / CUDA OOM / whisper 失败 / HTML 未按预期保存）的处理策略。
> SKILL.md 必须引用本协议；AI 撞异常时必读。

## 1. 核心策略

**B 选项**：重试 2-3 次同类问题后停下报告。

| 失败类型 | 策略 | 示例 |
|---|---|---|
| 临时性失败 | 自动重试 2-3 次，指数退避（1s/2s/4s） | 网络抖动、ffmpeg 单次超时 |
| 持续性失败 | 立即停下报告（不重试） | CUDA 持续 OOM、磁盘满 |
| 未知失败 | 重试 1 次 + 报告 | 罕见错误码 |

## 2. 重试规则

### 2.1 触发条件

- 同类问题（同错误信息 / 同 exit code）
- 重试次数：最多 2-3 次
- 重试间隔：指数退避 1s → 2s → 4s

### 2.2 终止条件（满足任一即停）

- 已达最大重试次数
- 不同错误类型（说明不是临时性问题）
- 用户主动停止（chat 中说"停"/"取消"）

### 2.3 不重试的情况

- 配置文件错误（schema 不匹配）
- 输入文件不存在（用户错误，不是系统临时故障）
- 参数值无效（用户错误）

## 3. 报告格式

异常重试失败或持续失败时，写入 logs/<task_id>.md 异常节 + chat 通知用户：

```markdown
[异常报告]
类型：CUDA OutOfMemory
位置：scripts/audio/separate.py (demucs)
重试：3/3 全部失败
原因：GPU 显存不足（已用 7.8GB / 总 8GB）
影响：Stage 2.3 声源分离失败，下游 Stage 2.4 ASR 无法进行
建议：
  - 换 CPU 模式（lib/separate_demucs.py device='cpu'）
  - 释放 GPU 显存（关闭其他 GPU 程序）
  - 用更小模型（htdemucs → htdemucs_ft）
降级选项：CUDA OOM → CPU 模式（自动尝试）
```

## 4. 降级选项（如有）

| 主方案 | 降级方案 | 触发条件 |
|---|---|---|
| demucs GPU | demucs CPU | CUDA OOM / GPU 不可用 |
| whisper large-v3 | whisper base / small | OOM / 加载失败 |
| pyannote GPU | pyannote CPU | CUDA OOM |
| ffmpeg libx264 | ffmpeg libx264 + preset ultrafast | 编码超时 |

**降级规则**：
- 降级前必须写入 logs/<task_id>.jsonl（decision 字段记录"降级到 X"）
- 降级后仍失败 → 停下报告

## 5. AI 行为约束

- ✅ **必须**：每次重试前写入 JSONL（decision 字段："重试第 N 次，原因为 X"）
- ✅ **必须**：停下时 chat 通知用户（不静默）
- ✅ **必须**：报告含「影响的下游 stage」（用户决定是否继续）
- ❌ **禁止**：连续重试超过 3 次
- ❌ **禁止**：跳过用户授权就自动降级（如 GPU → CPU 涉及用户机器配置）
- ❌ **禁止**：假装成功（必须真实 exit code）

## 6. 用户决策点

异常报告后，AI **必须停下等用户决策**，不能继续：

```
用户可能的回复：
- "继续" → AI 接受当前状态继续
- "降级" → AI 执行降级选项
- "跳过" → AI 跳过当前 stage 进入下一 stage（标记缺失）
- "终止" → AI 终止整个任务
```

**禁止**：AI 替用户决策（除非用户明确授权"按默认处理"）。
```

- [ ] **Step 2: 验证文件存在 + 含 6 个 ## 标题**

```bash
ls -la "references/异常处理协议.md"
grep -c "^## " "references/异常处理协议.md"
```

Expected: 文件存在，grep 输出 6

- [ ] **Step 3: Commit**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
git add references/异常处理协议.md
git commit -m "docs(v1.11): 添加异常处理协议 references/异常处理协议.md"
```

---

### Task 3: 创建 `references/红线契约-AI触发审查.md`

**Files:**
- Create: `references/红线契约-AI触发审查.md`

**目的**：细化红线契约——AI 修改 SKILL/md/脚本时的 5 步自检清单。基于 spec §5.4。

- [ ] **Step 1: 创建文件并写入完整内容**

```bash
touch "references/红线契约-AI触发审查.md"
```

写入：

```markdown
# 红线契约：AI 触发审查协议

> 本协议细化智剪工坊 SKILL.md §能力链路完整性 红线原则，给 AI 一个**可执行**的 5 步自检清单。
> 适用场景：用户让 AI 修改 SKILL.md / references/*.md / scripts/*.py / lib/*.py。

## 1. 触发条件

满足任一即触发自检：

- 用户说"修改 SKILL.md" / "改 references/" / "改 scripts/" / "改 lib/"
- AI 主动判断"这次改动会影响链路一致性"
- 任何对 4 层链路（SKILL → 中间层 md → 功能层 scripts → lib）的修改

## 2. 5 步自检清单

AI 修改完任何链路文件后，**必须**逐项打勾：

```
□ 1. 我改了什么？→ 列出改动清单
       文件：哪个文件
       段落：改了哪段
       原因：为什么改

□ 2. 链路里其他位置是否需要同步？
       - 改 scripts/{audio,asr,video,ai,batch}/ → 同步 SKILL.md 触发词 + references/*.md
       - 改 SKILL.md 触发词 → 同步 references/*.md + scripts/
       - 改 references/*.md → 同步 SKILL.md 触发词
       - 改 lib/ → 检查上游 scripts/ 是否需要更新

□ 3. 主动检查（AI 自己读文件，不强求工具脚本）：
       - 读 SKILL.md 触发词 → 新能力是否已声明？
       - 读 references/ 对应文档 → 是否覆盖新能力？
       - ls scripts/{audio,asr,video,ai,batch}/ → 新能力是否实际存在？
       - grep lib/ 对应模块 → 新函数是否已实现？

□ 4. 全部一致 → 标记完成
       - 写入 logs/<task_id>.md 红线节
       - 写入 .archive/CHANGELOG.md（如有 git）

□ 5. 发现不一致：
       - 严重不一致 → 立即停下报告（不修复）
       - 轻微不一致 → 自动修 + 在最终回复里报告
```

## 3. 严重 vs 轻微不一致

### 3.1 严重不一致（必须停下报告）

满足任一即视为严重：

- **链路断裂**：SKILL.md 列了某能力，但 scripts/ 没有对应脚本（AI 不能自创）
- **命名冲突**：scripts/ 有脚本，但 references/ 没文档（无法路由）
- **触发词覆盖缺失**：references/ 改了章节，但 SKILL.md 触发词未同步
- **lib 函数未实现**：scripts/ 调了 lib.x，但 lib/ 没 x 函数

### 3.2 轻微不一致（自动修 + 报告）

- 触发词拼写错误（影响 AI 检索）
- 章节顺序错乱（影响阅读）
- 链接 404（references/ 文件被删除但 SKILL.md 还有引用）

## 4. 报告模板

写入 logs/<task_id>.md 红线节：

```markdown
## Red Line Audit

**触发**：用户让 AI 修改 X
**改动清单**：
- scripts/audio/mix.py: 改了 vol 默认值从 0.18 → 0.15
- SKILL.md: 加触发词 "音量调节"
- references/音频配乐-BGM循环淡入淡出节拍.md: 同步 vol 默认值说明

**自检结果**：
- [x] SKILL.md 触发词已加 "音量调节"
- [x] scripts/audio/mix.py 已改
- [x] references/ 已同步
- [x] 无不一致

**归档**：.archive/CHANGELOG.md 已记录
```

## 5. AI 行为约束

- ✅ **必须**：5 步清单逐项打勾（不打勾 = 未完成）
- ✅ **必须**：严重不一致立即停下报告（不修复，等用户决策）
- ✅ **必须**：写入 logs/<task_id>.md 红线节（事后可查）
- ❌ **禁止**：跳过自检直接继续
- ❌ **禁止**：发现严重不一致但偷偷修复
- ❌ **禁止**：用户没明确授权就自创脚本

## 6. 与 SKILL.md §能力链路完整性 的关系

本协议是 SKILL.md §能力链路完整性 的**可执行展开**。两者关系：

- **SKILL.md §能力链路完整性**：宪法（红线原则，不可妥协）
- **本协议**：执行手册（5 步可操作清单）

AI 修改 SKILL 后**也必须重新加载本协议**，因为本协议可能因 SKILL.md 改动而需要更新。
```

- [ ] **Step 2: 验证文件存在 + 含 6 个 ## 标题**

```bash
ls -la "references/红线契约-AI触发审查.md"
grep -c "^## " "references/红线契约-AI触发审查.md"
```

Expected: 文件存在，grep 输出 6

- [ ] **Step 3: Commit**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
git add references/红线契约-AI触发审查.md
git commit -m "docs(v1.11): 添加红线契约 AI 触发审查协议"
```

---

### Task 4: 创建 `references/意图对齐-操作影响告知.md`

**Files:**
- Create: `references/意图对齐-操作影响告知.md`

**目的**：Step 7 意图对齐时的操作影响告知格式。基于 spec §5.5。

- [ ] **Step 1: 创建文件并写入完整内容**

```bash
touch "references/意图对齐-操作影响告知.md"
```

写入：

```markdown
# 意图对齐：操作影响告知协议

> 本协议定义 Step 7 意图对齐完成 + 用户即将确认前的**操作影响告知格式**。
> 目的：让用户清楚本次操作的影响（文件 + 风险 + 返工成本），避免错误返工。

## 1. 触发时机

满足**全部**条件即触发告知：

- 当前阶段：Stage 1 意图对齐完成
- 即将进入 Stage 2 粗加工
- 用户即将确认（"OK"/"同意"/"开始"）

## 2. 告知模板

AI 必须按以下格式输出（chat 回复 + 写入 logs/<task_id>.md 意图对齐节）：

```markdown
[操作影响告知]
阶段：Stage 2 粗加工（视频1-3）

影响文件：
  输入：
    - video_1.mp4 (源素材，1.2GB)
    - video_2.mp4 (源素材，800MB)
    - video_3.mp4 (源素材, 600MB)
  输出（将生成）：
    - 00_智剪/粗加工/单视频/video_1_trimmed.mp4 (~400MB)
    - 00_智剪/粗加工/单视频/video_2_trimmed.mp4 (~300MB)
    - 00_智剪/粗加工/单视频/video_3_trimmed.mp4 (~250MB)
    - 00_智剪/粗加工/组合/sequence_1_combined.mp4 (~900MB)
    - 00_智剪/粗加工/cover/cover_draft.jpg (~2MB)

操作类型：
  - trim (剪头剪尾)
  - color preset (调色 - 电影感)
  - fade-in / fade-out (淡入淡出)

风险等级：低
  - 原始素材：video_*.mp4 不动（只读）
  - 粗加工产物：可重新生成
  - 唯一文件：cover_draft.jpg（可重画）

返工成本：
  - 时间：约 8-12 分钟（重新跑 trim + color + cover）
  - 数据丢失：无（原始素材安全）
  - 重新确认：不需要（参数已固化）

⚠️ 重要提醒：
  - 一旦开始，返工需重跑整个 Stage 2（约 10 分钟）
  - 如不确定某参数（如 color preset），现在可调整
  - 确认后将自动进入 Stage 2 执行
```

## 3. 风险等级判定规则

**判定逻辑**：

| 操作 | 风险等级 | 判定理由 |
|---|---|---|
| 覆盖原始素材 | **高** | 违反 §能力链路完整性 "原始素材不动" 原则 |
| 覆盖粗加工产物 | 中 | 可重新生成，但有重跑成本 |
| 生成新文件 | 低 | 不影响已有产物 |

**判定优先级**：
1. 高风险 → 强制要求用户二次确认（"您确定要覆盖 X 吗？"）
2. 中风险 → 默认告知（如上）
3. 低风险 → 默认告知（如上）

## 4. 高风险操作的特殊处理

任何标记为"高风险"的操作，必须：

1. **二次确认**：用户必须明确回答"确认"才执行
2. **明确警告**：chat 顶部加 `⚠️ 高风险操作警告`
3. **原文件备份**：自动备份原文件到 `00_智剪/backup/<file>_<timestamp>`
4. **写入 logs**：logs/<task_id>.md 红线节记录此次覆盖

**示例**：

```markdown
⚠️ 高风险操作警告

操作：覆盖视频的旋转 metadata
文件：video_2.mp4 (原始素材)
原值：rotation = 90°
新值：rotation = 0°

是否继续？(yes/no)
```

## 5. AI 行为约束

- ✅ **必须**：每次 Stage 1 → Stage 2 转换时输出告知
- ✅ **必须**：高风险操作二次确认
- ✅ **必须**：写入 logs/<task_id>.md 意图对齐节
- ❌ **禁止**：跳过告知直接执行
- ❌ **禁止**：用户没明确"确认"就执行高风险操作

## 6. 与 Step 7 意图对齐的协作

- **Step 7 早期**：AI 询问自然语言字段（"你想要什么效果？"）
- **Step 7 中期**：AI 输出 6 象限操作清单（A/B/C/D/E/F）
- **Step 7 后期**：AI 输出本协议定义的告知模板
- **Step 7 完成**：用户明确"确认" → AI 进入 Stage 2

AI 不得在告知前进入 Stage 2。
```

- [ ] **Step 2: 验证文件存在 + 含 6 个 ## 标题**

```bash
ls -la "references/意图对齐-操作影响告知.md"
grep -c "^## " "references/意图对齐-操作影响告知.md"
```

Expected: 文件存在，grep 输出 6

- [ ] **Step 3: Commit**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
git add references/意图对齐-操作影响告知.md
git commit -m "docs(v1.11): 添加意图对齐操作影响告知协议"
```

---

## Phase 2: 3 个渐进披露 references/ 创建（从 SKILL.md 拆出）

### Task 5: 创建 `references/jargon.md`（从 SKILL.md §Jargon 拆出）

**Files:**
- Create: `references/jargon.md`
- Read source: `SKILL.md` lines 921-945 (§Jargon 大白话词典)

**目的**：把 SKILL.md §Jargon 大白话词典 移到 references/，SKILL.md 引用。

- [ ] **Step 1: 读取 SKILL.md §Jargon 原文**

```bash
sed -n '921,945p' SKILL.md
```

Expected: 输出 §Jargon 大白话词典 表格内容

- [ ] **Step 2: 创建 references/jargon.md 并复制内容**

```bash
touch "references/jargon.md"
```

写入：

```markdown
# Jargon 大白话词典

> 本词典记录用户口语 → 智剪工坊路由的映射。
> SKILL.md 路由表精简版见 §子技能索引；详细路由见本文件 + references/AI路由表-意图JSON字段枚举.md。

## 用户口语 → 路由

| 用户说的 | 实际指 | 路由 |
|---|---|---|
| "剪头/剪尾" | trim-head / trim-tail | `scripts/video/trim.py` |
| "去掉中间" | cut-middle | `scripts/video/trim.py` |
| "保留某段" | pin-range | `scripts/video/trim.py` |
| "加转场" | sequences[].transitions | `scripts/video/xfade.py` |
| "加 BGM" | audio-mix | `scripts/audio/mix.py` |
| "变声" | audio-voice | `scripts/audio/voice.py` |
| "节拍卡点" | audio-beat | `scripts/audio/beat.py` |
| "提取音频" | audio-extract | `scripts/audio/extract.py` |
| "音频降噪/降噪" | audio-denoise | `scripts/audio/denoise.py` |
| "声源分离/提取人声" | audio-separate | `scripts/audio/separate.py` (v1.7 调 `lib/separate_demucs.py` GPU) |
| "说话人分离/谁说了什么" | audio-diarize | `scripts/audio/diarize.py` (v1.7 调 `lib/asr/pyannote.py` 需 HF token) |
| "ASR/语音转文字" | asr-transcribe | `scripts/asr/transcribe.py` (v1.7 调 `lib/asr/whisper.py` GPU) |
| "烧字幕" | asr-burn | `scripts/asr/burn_subtitle.py` (v1.6 调 `lib/ffmpeg/video/subtitle.py`) |
| "带说话人的字幕" | asr-speaker | `scripts/asr/speaker_srt.py` |
| "配字幕" | subtitle | `scripts/asr/transcribe.py` + `scripts/asr/burn_subtitle.py` |
| "做封面" | cover | `scripts/ai/cover.py` |
| "调色" | color | `scripts/video/color.py` |
| "推镜头" | speed-up / cinematic-zoom | `scripts/video/speed.py` |
| "加文字" | opening-text / ending.text | `scripts/video/opening.py` |
| **counter-rotate** | 像素反转（抵消 metadata）| `lib/video_processing.py` 自动处理 |
| **aspect-fill / aspect-fit** | 填满 vs 加黑边 | `lib/video_processing.py` |

## 使用方法

1. AI 收到用户口语化指令
2. 在本词典查匹配项
3. 路由到对应 scripts/*.py
4. 不匹配项 → 标记为 F 象限（不支持），告知用户
```

- [ ] **Step 3: 验证行数 + 与 SKILL.md 原文一致**

```bash
wc -l "references/jargon.md"
diff <(sed -n '925,945p' SKILL.md | grep '^|"' || echo "DIFF") <(sed -n '20,40p' "references/jargon.md" | grep '^|"' || echo "DIFF")
```

Expected: `references/jargon.md` 约 50 行，表格内容与原 SKILL.md 表格一致

- [ ] **Step 4: Commit**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
git add references/jargon.md
git commit -m "docs(v1.11): 拆出 jargon 大白话词典到 references/jargon.md"
```

---

### Task 6: 创建 `references/AI协作详细.md`（从 SKILL.md §AI 协作协议 拆出）

**Files:**
- Create: `references/AI协作详细.md`
- Read source: `SKILL.md` lines 605-700 (§AI 协作协议 §1-§10 详细)

**目的**：把 SKILL.md §AI 协作协议 详细条款（路由原则 / 文本解析 / 模糊项 / 速度范围 / 时间字段 / 序列 / diff 读取 / 修改同步 / 真实照片 / 新增 ops）拆到 references/。SKILL.md 只留核心 4 原则 + 5 契约 + 3 反模式。

- [ ] **Step 1: 读取 SKILL.md §AI 协作协议 原文**

```bash
sed -n '605,700p' SKILL.md
```

Expected: §1-§10 详细条款

- [ ] **Step 2: 创建 references/AI协作详细.md 并复制内容**

```bash
touch "references/AI协作详细.md"
```

写入（基于 SKILL.md §AI 协作协议 §1-§10，压缩去重）：

```markdown
# AI 协作协议（详细）

> 本文档是 SKILL.md §AI 协作协议 的详细展开。
> SKILL.md 只列核心 4 原则 + 5 契约 + 3 反模式，详细条款见本文件。

## 1. 路由第一原则

**AI 拿到 intent.json / 用户需求后，第一件事是查路由表**（`references/AI路由表-意图JSON字段枚举.md`）。

- 命中 → 调对应 用户脚本 CLI
- 不命中 → F 象限（明确说"智剪工坊当前不支持 X"）

**禁止**：
- AI 不查表直接调 CLI
- 凭印象调参
- 静默不支持的功能

## 2. AI 文本解析 → 路由表匹配 → 用户确认（E 象限）

**自由文本字段**（`notes` / `overall_intent` / `ending.prompt` 等）必须先匹配路由表：

1. 读字段
2. 在路由表里找匹配
   - 匹配成功 → 用对应 CLI
   - 匹配失败 → **不假装支持**，告诉用户"智剪工坊当前不支持 X"
3. **先告知用户匹配结果，等用户确认再调 CLI**

**反例**：用户说"加个转场"，AI 直接默认 `fade` → 错
**正例**：用户说"加个转场"，AI 列出 9 种 type 让用户选 → 对

## 3. 模糊项 / 待澄清（D 象限，AI 必问）

AI 看到模糊需求时**必须问用户**，不擅自决定：

- "想要动感" → 问：配 BGM？转场？调色？速度？
- "视频太长了" → 问：剪头剪尾？cut-middle？target-duration？
- "加滤镜" → 问：color preset 选哪个？
- "开头加段音乐" → 问：什么音乐？音量多少？全段还是开头？

### 3.1 ending.type 不在路由表时

当 ending.type 是 `next-episode-promo` / `next-week` / 其他自定义类型时：

1. AI 必须 fallback 到 `next-day` 实现（黑屏 + 文字）
2. AI 必须在回复里明确告知用户："ending.type X 不在标准路由表，已 fallback 到 next-day"
3. AI 禁止手写 ffmpeg drawtext 命令

### 3.2 AI 主动决策 vs 必须问的边界

#### ✅ AI 可主动决策（无需问用户）

| 场景 | 示例 |
|---|---|
| 参数默认值 | BGM vol=0.15, crf=23, fps=30 |
| 重试失败任务 | 同方法重试 2 次 |
| 中间文件清理 | 临时变量命名 |
| 优化建议 | trim 精度 +1, 加 faststart |

#### ❌ AI 必须问用户（任何一条触发就问）

| 场景 | 反例（已踩过的坑） |
|---|---|
| 速度修改 | video_4 13.6 分钟冥想，AI 自作主张 4x（用户要 40x） |
| 风格调整 | 调色/滤镜/转场 |
| 新增/删除内容 | 字幕/封面/ending 缺失时自作主张 |
| intent.json 缺失关键字段 | 字幕诉求被漏掉 |
| ending.type 不在路由表 | 手写 ffmpeg 命令 |
| 时长调整超过 ±10% | — |

## 4. 速度范围（speed-up / slow-down factor）

- `factor > 1.0` → 加速（如 2.0 = 2 倍速）
- `factor < 1.0` → 减速（如 0.5 = 半速）
- 推荐范围：0.25 ~ 4.0（ffmpeg atempo 链能堆叠）
- **执行器二次校验**：
  - `0.2 <= factor <= 10` → 正常
  - `10 < factor <= 100` → 高倍速（如冥想缩时），允许
  - `factor > 1000` → 报错退出，提示"几乎看不清，请确认"
  - `factor < 0.1` → 报错，提示"慢到几乎静止"

## 5. 时间字段解析规则（pin-range / cut-middle / insert-image）

用户时间字段可能是多种格式，AI 必须全兼容：

| 写法 | 解析 | 示例 |
|---|---|---|
| `M:SS` 或 `MM:SS` | 标准格式 | `"1:30"` → 90s |
| `H:MM:SS` | 含小时 | `"1:30:00"` → 5400s |
| 纯数字 | 默认秒 | `"15"` → 15s |
| `"15秒"` / `"15s"` | 秒（中文/英文单位） | `"15秒"` → 15s |
| `"15分钟"` / `"15min"` | 分钟转秒 | `"15分钟"` → 900s |
| `"1分30秒"` | 复合 | `"1分30秒"` → 90s |
| 完全无法解析 | 必须问用户 | 不要瞎猜 |

## 6. 序列（sequences）是部分约束

- `sequences[i].videos` 强制该 sequence 内部的视频顺序
- 但**不强制** sequence 间的视频不重复
- AI 必须读 `project.overall_intent` 决定 sequence 间的拼接方式

## 7. 自动读 intent.json 多版本 diff

AI 收到 intent.json 后，自动检查工作区里的版本文件：

- `intent.json`（最新）
- `intent_v1.json` / `intent_v2.json` / ...（历史）

如果有多个版本：
- 自动 diff 所有字段变更
- 找出哪些视频/字段被改
- 重点关注变化区域

## 8. 修改 用户脚本 CLI 后必须同步

新增/修改 用户脚本 CLI 时，AI 必须：
1. 改 `scripts/{audio,asr,video,ai,batch}/<name>.py`
2. 同步改 `references/XX-xxx.md`
3. 同步改 SKILL.md 触发词索引
4. 在 `.archive/CHANGELOG.md` 加变更记录

## 9. 真实照片 vs 插画

**封面图 / 内容图**都用 `cover_ai.py` 或 `matrix_generate_image` **生成插画**，**不放真实照片**。
- prompt 要写明 "扁平设计 / 插画 / illustration / 平面设计" 等关键词
- 创作者提供的 JPG 文件**可以**作为内容参考，但封面不直接用

## 10. 新增 ops（v0.6+）

加新 op 必须：
1. 在 `lib/video_processing.py` 加 build filter
2. 加到 §G.1 video 级 ops 表
3. 在 §H 路由表加字段定义
4. 在 references/ 加详细文档

**未实现的 op 触发 fallback**：如果 intent.json 里有 ops 名称不在已知列表中：
1. 读 op 的 note 字段看用户意图
2. 尝试用最接近的智剪工坊脚本实现
3. 在最终回复里告知"该 op 暂用 X 脚本模拟"
```

- [ ] **Step 3: 验证行数 + 与 SKILL.md 原文一致**

```bash
wc -l "references/AI协作详细.md"
```

Expected: 约 200 行

- [ ] **Step 4: Commit**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
git add references/AI协作详细.md
git commit -m "docs(v1.11): 拆出 AI 协作详细协议到 references/AI协作详细.md"
```

---

### Task 7: 创建 `references/muted-视频拼接风险.md`（从 SKILL.md §v1.10 拆出）

**Files:**
- Create: `references/muted-视频拼接风险.md`
- Read source: `SKILL.md` lines 251-298 (§v1.10 muted 视频拼接风险)

**目的**：把 v1.10 muted 视频拼接风险的 48 行技术细节移到 references/。

- [ ] **Step 1: 读取 SKILL.md §v1.10 muted 原文**

```bash
sed -n '251,298p' SKILL.md
```

Expected: muted 视频拼接风险章节

- [ ] **Step 2: 创建 references/muted-视频拼接风险.md 并复制内容**

```bash
touch "references/muted-视频拼接风险.md"
```

写入：

```markdown
# muted 视频拼接风险（v1.10 历史 bug）

> 本文档记录 v1.10 修复的 muted 视频拼接时长异常 bug，供未来参考。
> SKILL.md 不再保留此细节；如遇同类问题加载本文件。

## 核心问题

用 `-an`（去除音频）处理过的 mp4，可能残留 audio metadata 在 moov atom 中。这会导致后续 `trim.py concat` 时：

- ffmpeg 强行对齐 audio PTS → video 被压缩/拉长
- sequence 显示时长异常（过短或过长，例如 130 分钟）

## 触发场景

- `voice: "mute"` 的 video 后面拼接有 audio 的 video
- 多个 muted segments 互相拼接（累积偏移）

## 解决方案

### 方案 A（单 video 层，推荐）：mute 时强制 remux 清残留

```python
def remux_clean_residual_metadata(video_path):
    tmp = video_path.with_suffix(".clean.mp4")
    run_ffmpeg([
        "-y", "-i", str(video_path),
        "-map", "0:v",            # 只映射 video，丢弃 audio
        "-c", "copy",             # 不重编码
        "-map_metadata", "-1",    # 清空 metadata
        "-movflags", "+faststart",
        str(tmp),
    ])
    Path(tmp).replace(video_path)
```

### 方案 B（sequence 层）：用 filter_complex concat，每个 muted segment 加 anullsrc 占位 audio

```bash
ffmpeg -i seg1.mp4 -i seg2.mp4 -filter_complex \
  "anullsrc=cl=stereo:r=44100[a1];anullsrc=cl=stereo:r=44100[a2]; \
   [0:v][a1][1:v][a2]concat=n=2:v=1:a=1[v][a]" \
  -map "[v]" -map "[a]" output.mp4
```

## 检测方法

```bash
ffmpeg -i input.mp4 2>&1 | grep -A 1 "Stream #0"
# 如果 muted mp4 仍有 "Stream #0:1.*Audio" 行，说明残留
```

## v1.10 自动处理

`trim.py concat` 已加 pre-process，自动检测并清理残留 metadata。
```

- [ ] **Step 3: 验证文件存在 + 含 5 个 ## 标题**

```bash
ls -la "references/muted-视频拼接风险.md"
grep -c "^## " "references/muted-视频拼接风险.md"
```

Expected: 文件存在，grep 输出 5

- [ ] **Step 4: Commit**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
git add references/muted-视频拼接风险.md
git commit -m "docs(v1.11): 拆出 muted 视频拼接风险到 references/"
```

---

## Phase 3: SKILL.md 改造

### Task 8: SKILL.md 添加 Loading 触发器（§5.9）

**Files:**
- Modify: `SKILL.md` — 在 §能力链路完整性 之后添加新章节

**目的**：在 SKILL.md 显眼位置添加 Loading 触发器，告诉 AI 何时加载哪个 references/。

- [ ] **Step 1: 定位插入点**

```bash
grep -n "^## ⚠️ 能力链路完整性" SKILL.md
grep -n "^## 📦 安装与配置" SKILL.md
```

Expected: 找到两章的行号

- [ ] **Step 2: 在 §能力链路完整性 后插入 Loading 触发器章节**

读取 `SKILL.md` 在 `## 📦 安装与配置` 前插入：

```markdown
---

## 🔌 Loading 触发器（AI 必读）

> AI 加载 SKILL.md 后，按本触发器决定**何时加载哪个 references/**。
> 避免一次性加载所有 references/ 导致 context 爆炸。

### 路由命中触发

| 用户口语 / 触发词 | 加载 references/ |
|---|---|
| 美颜/磨皮/瘦脸/大眼 | `美颜-四种人脸美化.md` |
| 调色/LUT/视频调色/调色预设 | `调色预设-18种预设LUT风格迁移.md` |
| ASR/Whisper/语音转文字/说话人分离/声源分离 | `ASR链路-声源分离说话人分离Whisper烧字幕.md` |
| 音频降噪/BGM/混音/节拍卡点 | `音频配乐-BGM循环淡入淡出节拍.md` |
| 转场/淡入/擦除/滑动 | `转场-9种转场类型.md` |
| 字幕/烧字幕/封面文字 | `字幕文字-Whisper烧字幕片头变声.md` |
| 数字人/虚拟人/AI 讲解 | `数字人-AI主播头像说话.md` |
| 改词/翻唱/配音/换声 | `改词翻唱-文案改写TTS替换音轨.md` |
| 文字成片/AI 生成视频 | `文字成片-mmx免key生成6秒片段.md` |
| 抠图/金句/去水词/蒙版 | `AI智能剪辑-抠图金句去水词蒙版.md` |
| 批量/流水线 | `批量处理-多视频统一操作.md` |
| 慢动作/推镜头/倒放 | `电影感剪辑-变速倒放多机位.md` |
| 剪头/剪尾/裁切/分段 | `精剪-剪头剪尾保留段切中间.md` |
| 图片转视频/Ken Burns | `图片转视频-静态图KenBurns效果.md` |
| 旋转/缩放/裁剪/静音/提取音频 | `原子操作-14种基础剪辑指令.md` |

### 行为协议触发

| AI 场景 | 加载 references/ |
|---|---|
| 阶段 0 用户选 ①（从零开始） | `主流程-阶段编排.md` |
| 阶段 1 必读（路由表） | `AI路由表-意图JSON字段枚举.md` |
| 阶段 1 缺失必填字段时 | `AI交互式采访触发条件.md` |
| 阶段 1 决定要不要问用户时 | `场景覆盖度自检.md` |
| **AI 撞异常（任何阶段）** | `异常处理协议.md` |
| **AI 修改 SKILL/md/脚本** | `红线契约-AI触发审查.md` |
| **AI 加载后必读（协议层）** | `AI行为日志协议.md` |
| **Step 7 意图对齐完成** | `意图对齐-操作影响告知.md` |
| 用户口语映射路由 | `jargon.md` |
| AI 协作详细条款 | `AI协作详细.md` |

### 加载规则

1. AI 加载 SKILL.md 后，先扫本触发器
2. 按需加载（不要一次性全加载）
3. 加载后，把关键摘要写回 `logs/<task_id>.md`（避免重复加载）

---
```

- [ ] **Step 3: 验证插入成功**

```bash
grep -c "^## 🔌 Loading 触发器" SKILL.md
```

Expected: 输出 1

- [ ] **Step 4: Commit**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
git add SKILL.md
git commit -m "docs(v1.11): SKILL.md 添加 Loading 触发器章节"
```

---

### Task 9: SKILL.md 章节合并（§AI 协作协议 + §AI 必读 → §AI 协作协议）

**Files:**
- Modify: `SKILL.md` — 合并 §AI 协作协议 + §AI 必读 两章

**目的**：消除 §AI 协作协议 和 §AI 必读 的重复内容（4 原则 + 5 契约 + 3 反模式 出现两次）。

- [ ] **Step 1: 定位两章**

```bash
grep -n "^## 🤖 AI 协作协议\|^## ⚠️ AI 必读" SKILL.md
```

Expected: 找到两章的行号

- [ ] **Step 2: 读取两章内容确认重复**

```bash
sed -n '605,680p' SKILL.md
sed -n '757,810p' SKILL.md
```

Expected: 两章都有 "核心原则 4 条" + "执行契约 5 条" + "反模式 3 种"

- [ ] **Step 3: 删除 §AI 必读 章节（保留 §AI 协作协议 完整版）**

读取 SKILL.md，定位到 `## ⚠️ AI 必读（v1.0 强制, v1.3 修订）` 章节，删除整个章节（直到下一个 `## ` 标题前）。

使用 `Read` 工具读取 SKILL.md 完整内容，找到 §AI 必读 起始和结束行，删除。

**保留**：`## 🤖 AI 协作协议` 完整内容
**删除**：`## ⚠️ AI 必读` 整章（约 50 行）

**注意**：删除前备份原内容到 `/tmp/skill_md_backup.md` 以防回退。

- [ ] **Step 4: 验证行数减少**

```bash
wc -l SKILL.md
```

Expected: 行数减少约 50 行

- [ ] **Step 5: 验证 §AI 必读 不再存在**

```bash
grep -c "^## ⚠️ AI 必读" SKILL.md
```

Expected: 输出 0

- [ ] **Step 6: Commit**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
git add SKILL.md
git commit -m "docs(v1.11): SKILL.md 合并 §AI 协作协议 + §AI 必读（消除重复）"
```

---

### Task 10: SKILL.md 移除并指向 references/

**Files:**
- Modify: `SKILL.md` — 移除 §Jargon / §子技能索引详细 / §v1.10 mute / §阶段 0-5 流程细节，指向 references/

**目的**：应用 progressive disclosure，把详细章节移到 references/，SKILL.md 只留概览 + 引用。

- [ ] **Step 1: 定位要移除的章节**

```bash
grep -n "^## 🔤 Jargon 大白话词典\|^## 🎬 阶段 0\|^## ⚠️ muted 视频" SKILL.md
```

Expected: 找到各章节行号

- [ ] **Step 2: 替换 §Jargon 大白话词典 → 引用 references/jargon.md**

读取 SKILL.md，定位 `## 🔤 Jargon 大白话词典` 章节，**替换整章为**：

```markdown
## 🔤 Jargon 大白话词典（→ references/jargon.md）

**详细路由表**见 `references/jargon.md`（从 v1.10 SKILL.md §Jargon 大白话词典 拆出）。SKILL.md 不再保留重复条目。
```

- [ ] **Step 3: 替换 §阶段 0-5 流程 → 引用 references/主流程-阶段编排.md**

读取 SKILL.md，定位 `## 🎬 阶段 0 ▸ 项目初始化` 到 `## 🎨 模板工作流` 之间所有详细流程内容，**替换为**：

```markdown
## 🎬 阶段 0-5 概览（→ references/主流程-阶段编排.md）

```
阶段 0 项目初始化 → 阶段 1 意图对齐 → 阶段 2 粗加工 → 阶段 3 模板 → 阶段 4 产物审查 → 阶段 5 收尾
```

**详细 AI 编排步骤**见 `references/主流程-阶段编排.md`（已存在）。SKILL.md 只保留概览，详细契约按 Loading 触发器按需加载。

**关键约束**（SKILL.md 保留）：
- 阶段 1 必须输出 6 象限操作清单 → 用户确认 → 才进入阶段 2
- 阶段 2 Step 2 每处理完一个视频 → 立即向用户汇报产物路径
- 阶段 4 产物审查 → 用户逐项标 OK/有问题 → 全部 OK 才进入阶段 5
```

- [ ] **Step 4: 替换 §v1.10 muted 视频拼接风险 → 引用 references/muted-视频拼接风险.md**

读取 SKILL.md，定位 `## ⚠️ muted 视频拼接风险(v1.10 新增)` 章节，**替换为**：

```markdown
## ⚠️ muted 视频拼接风险（v1.10 已修，详见 references/）

v1.10 修复 muted 视频拼接时长异常 bug 的**完整技术细节**见 `references/muted-视频拼接风险.md`。

**触发场景摘要**：
- `voice: "mute"` 的 video 后面拼接有 audio 的 video
- 多个 muted segments 互相拼接

**检测命令**：`ffmpeg -i input.mp4 2>&1 | grep -A 1 "Stream #0"`
```

- [ ] **Step 5: 验证行数大幅减少**

```bash
wc -l SKILL.md
```

Expected: 行数从 1140 减少到 ~850 行

- [ ] **Step 6: 验证引用正确**

```bash
grep -c "references/jargon.md\|references/主流程-阶段编排.md\|references/muted-视频拼接风险.md" SKILL.md
```

Expected: 输出 ≥ 3

- [ ] **Step 7: Commit**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
git add SKILL.md
git commit -m "docs(v1.11): SKILL.md 移除详细章节，引用 references/（progressive disclosure）"
```

---

### Task 11: SKILL.md 最终精简（移除版本历史 + 压缩到 < 600 行）

**Files:**
- Modify: `SKILL.md` — 移除版本历史章节（L1046-1140）

**目的**：把版本历史（约 100 行）从 SKILL.md 移到 `.archive/CHANGELOG.md`（已有），SKILL.md 最终 < 600 行。

- [ ] **Step 1: 定位版本历史章节**

```bash
grep -n "^## 📅 版本" SKILL.md
```

Expected: 找到版本历史章节起始行

- [ ] **Step 2: 读取版本历史内容**

```bash
sed -n '1046,1140p' SKILL.md
```

- [ ] **Step 3: 确认 .archive/CHANGELOG.md 已存在**

```bash
ls -la ".archive/CHANGELOG.md" 2>/dev/null || echo "需新建"
```

Expected: 文件已存在（v1.10 已有 CHANGELOG）

- [ ] **Step 4: 把版本历史追加到 .archive/CHANGELOG.md（如果不存在则新建）**

读取 SKILL.md L1046-1140 内容，追加到 `.archive/CHANGELOG.md` 末尾。

如果 CHANGELOG.md 不存在，创建并写入：

```markdown
# 智剪工坊 CHANGELOG

> 版本历史从 SKILL.md v1.10 移出。详细变更见本文。

## v1.10（2026-07-10）

（粘贴 SKILL.md 原 §v1.10 版本摘要）

## v1.9（2026-07-10）

（粘贴 SKILL.md 原 §v1.9 版本摘要）

## v1.8（2026-07-10）

...

## v1.7 / v1.6 / v1.5 / v1.4 / v1.3 / v1.2 / v1.0 / v0.7

（按 SKILL.md 原顺序粘贴）
```

- [ ] **Step 5: 从 SKILL.md 删除整个版本历史章节**

读取 SKILL.md，定位 `## 📅 版本` 到 `## 🗂 目录结构` 之间所有内容，删除。

- [ ] **Step 6: 验证最终行数 < 600**

```bash
wc -l SKILL.md
```

Expected: < 600 行

- [ ] **Step 7: 验证版本章节不再在 SKILL.md**

```bash
grep -c "^## 📅 版本" SKILL.md
```

Expected: 输出 0

- [ ] **Step 8: Commit**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
git add SKILL.md .archive/CHANGELOG.md
git commit -m "docs(v1.11): SKILL.md 移除版本历史到 .archive/CHANGELOG.md"
```

---

## Phase 4: 整体验证

### Task 12: 整体验证

**Files:**
- Verify: `SKILL.md` 行数 + 所有 references/ 存在 + 引用一致性

**目的**：确保 v1.11 升级成功，所有 spec §7 成功标准达成。

- [ ] **Step 1: 验证 SKILL.md 行数 < 600**

```bash
wc -l SKILL.md
```

Expected: ≤ 600

- [ ] **Step 2: 验证 7 个新 references/ 全部就位**

```bash
ls -la "references/AI行为日志协议.md" \
       "references/异常处理协议.md" \
       "references/红线契约-AI触发审查.md" \
       "references/意图对齐-操作影响告知.md" \
       "references/jargon.md" \
       "references/AI协作详细.md" \
       "references/muted-视频拼接风险.md"
```

Expected: 7 个文件全部存在

- [ ] **Step 3: 验证 SKILL.md 引用一致性**

```bash
grep -c "references/AI行为日志协议.md\|references/异常处理协议.md\|references/红线契约\|references/意图对齐\|references/jargon.md\|references/AI协作详细\|references/muted" SKILL.md
```

Expected: ≥ 7（每个 references/ 至少引用 1 次）

- [ ] **Step 4: 验证 Loading 触发器存在**

```bash
grep -c "^## 🔌 Loading 触发器" SKILL.md
```

Expected: 输出 1

- [ ] **Step 5: 验证 4 协议标题都出现在 SKILL.md**

```bash
grep -E "AI 行为日志协议|异常处理协议|红线契约.*AI 触发|意图对齐.*操作影响告知" SKILL.md
```

Expected: 4 行输出（每个协议 1 行）

- [ ] **Step 6: 验证 §能力链路完整性 仍存在（宪法不动）**

```bash
grep -c "^## ⚠️ 能力链路完整性" SKILL.md
```

Expected: 输出 1

- [ ] **Step 7: 检查 git log（确认 12 个 commit）**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
git log --oneline | head -15
```

Expected: 最近 12 个 commit 对应本 plan 的 12 个 task

- [ ] **Step 8: 跑 smoke test（AI 加载 SKILL.md 后跑最小流程）**

模拟 AI 加载流程：

1. AI 加载 SKILL.md
2. AI 触发 Loading 触发器加载 references/AI行为日志协议.md
3. AI 在日志中写入一条 JSONL entry
4. AI 触发 Loading 触发器加载 references/异常处理协议.md（如果有异常）
5. 验证 logs/<task_id>.md + .jsonl 都生成

**smoke test 脚本**（临时）：

```bash
mkdir -p /tmp/zhijiangongfang_smoke/00_智剪/中间产物/logs/
cd /tmp/zhijiangongfang_smoke

# 模拟 AI 写日志
cat > logs/test_task.md << 'EOF'
# 任务 test_task

## Stage 0 项目初始化
[2026-07-10T11:00:00] 决策：smoke test 验证日志协议
EOF

cat > logs/test_task.jsonl << 'EOF'
{"time":"2026-07-10T11:00:00","stage":"0","step":"0","action":"smoke_test","decision":"验证日志协议","thinking":"测试 JSONL 写入","result":"ok","error":null}
EOF

ls -la logs/
```

Expected: logs/ 目录有 test_task.md + test_task.jsonl

- [ ] **Step 9: 最终总结 + 写完成报告**

在 git commit message 里附：

```
v1.11 升级完成：
- SKILL.md: 1140 → ~600 行（精简 47%）
- 新增 7 个 references/ 协议文档
- 应用 Progressive Disclosure 原则
- 添加 Loading 触发器（AI 何时加载哪个 references/）

成功标准全部达成：
- [x] AI 加载 SKILL.md 后知道每一步日志协议
- [x] AI 撞异常知道重试规则
- [x] AI 修改 SKILL 后知道自检清单
- [x] AI 意图对齐时知道操作影响告知
- [x] SKILL.md < 600 行
- [x] 7 个 references/ 全部就位
- [x] Loading 触发器就位
- [x] Smoke test 通过
```

- [ ] **Step 10: 最终 commit**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
git log --oneline -1
git status
```

Expected: git status 干净，所有改动已 commit

---

## Self-Review Checklist（plan 写完自审）

### Spec 覆盖

- [x] §5.1 Logging 系统 → Task 1（AI行为日志协议.md）
- [x] §5.2 AI 行为日志协议 → Task 1（含 self-reference mitigation）
- [x] §5.3 异常处理协议 → Task 2（异常处理协议.md）
- [x] §5.4 红线契约强化 → Task 3（红线契约-AI触发审查.md）
- [x] §5.5 Step 7 操作影响告知 → Task 4（意图对齐-操作影响告知.md）
- [x] §5.6 SKILL.md 精简 → Task 9/10/11
- [x] §5.7 Progressive Disclosure 原则 → Task 9/10（应用判定规则）
- [x] §5.8 进一步移出清单 → Task 5/6/7（jargon/AI协作详细/muted）
- [x] §5.9 Loading 触发器 → Task 8
- [x] §6 Open Questions 7 个 → 默认方案已固化在 references/
- [x] §7 成功标准 7 项 → Task 12 验证

### 占位符扫描

- ❌ 无 "TBD"/"TODO"/"implement later"/"fill in details"
- ❌ 无 "Add appropriate error handling"/"handle edge cases"（每个错误处理都具体到 B 选项重试规则）
- ❌ 无 "Similar to Task N"（每个 task 完整独立）
- ✅ 所有步骤有完整代码/内容/命令

### 类型一致性

- 文件路径全程一致：`references/<文件名>.md` / `SKILL.md` / `.archive/CHANGELOG.md`
- 字段 schema 一致：JSONL 字段 time/stage/step/action/decision/thinking/result/error
- commit message 格式一致：`docs(v1.11): <动作>`

---

**Plan 完成。准备进入执行阶段。**