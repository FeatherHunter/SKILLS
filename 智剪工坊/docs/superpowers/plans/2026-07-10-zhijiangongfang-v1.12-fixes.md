# 智剪工坊 v1.12 修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 v1.12 重构中 14 个对抗式审查发现的问题（P0 5 个 + P1 5 个 + P2 4 个），让 SKILL 从"有逻辑骨架"变成"可实际跑通"。

**Architecture:** 纯文档改动。8 个 task，每个修改 1-3 个 references/*.md，集成 v1.11.1 建的日志系统到 v1.12 新增的 4 个文件中，按依赖顺序执行。

**Tech Stack:** Markdown / Git / shell (grep, wc, sed)

---

## 文件结构

**修改（8 个）：**
- `references/AI行为日志协议.md` — 扩展 schema 包含 v1.12 新 stages
- `references/精加工-两路径.md` — Path A 约束 + Path C + 沉默处理 + 日志集成
- `references/审查-用户交互循环.md` — 阈值可配置 + 抗疲劳 + 日志集成
- `references/二次加工-复用工作流.md` — 备份命名 + 完整性校验 + BACKUP_NOTE 模板
- `references/粗加工-执行契约.md` — 日志集成 + 批量汇报
- `references/主流程-阶段编排.md` — announce fallback + 回退粒度 + intent 备份 + Step 13 修正
- `SKILL.md` — Loading 触发器更新

**新增（1 个 references/ 章节）：**
- 无（直接在主流程 §5 添加 4 个新章节）

**不修改：**scripts/、lib/、config.json、requirements*.txt、setup.*、verify.py

---

## Task 1: 扩展 AI 行为日志协议 schema（P0-2 基础设施）

**Files:**
- Modify: `references/AI行为日志协议.md`

**目的：**让 v1.12 新增的 stages（粗加工审查/精加工/精加工审查/出片/复用/备份）能在 JSONL stage 字段中表达。后续 5 个 task 依赖此 schema。

- [ ] **Step 1: 读取当前 schema**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
grep -n "stage" references/AI行为日志协议.md
```

预期：找到 §3 JSONL Schema 中 stage 字段说明

- [ ] **Step 2: 更新 stage 字段枚举**

打开 `references/AI行为日志协议.md`，找到 §3 JSONL Schema 的 stage 字段说明。

当前文档：
```markdown
| stage | string | 是 | 当前阶段号（"0"-"5"）|
```

改为：
```markdown
| stage | string | 是 | 当前阶段号（v1.12 扩展）|

**stage 取值（v1.12 扩展）**：
- "0"-"5" — 老阶段（项目初始化/意图对齐/粗加工/模板/审查/出片）
- "step_10_review" — 粗加工审查（v1.12 新）
- "refine" — 精加工（v1.12 新，含路径 A/B）
- "step_12_review" — 精加工审查（v1.12 新）
- "finalize" — 出片（v1.12 重命名自 stage 5）
- "reuse_backup" — 二次加工备份（v1.12 新）
- "reuse_apply" — 二次加工复用（v1.12 新）
```

- [ ] **Step 3: 更新 .md 模板章节结构**

找到 §5 Markdown (.md) 章节结构示例。

当前文档：
```markdown
## Stage 0 项目初始化
[时间] 决策：HTML 表单填写
...
## Stage 5 收尾
...
```

改为：
```markdown
## Step 0-2 初始化
[时间] 决策：HTML 表单填写

## Step 3-4 加载 + 填表
[时间] 决策：HTML 路径
[时间] 决策：intent.json 保存路径

## Step 5-7 意图对齐
[时间] 决策：6 象限操作清单
[时间] 决策：用户回答的关键问题

## Step 8-9 粗加工
[时间] 决策：调用的 CLI（trim/color/normal）
[时间] 异常：...（如有）

## Step 10 粗加工审查
[时间] 决策：用户标 OK / 有问题的项

## Step 11 精加工
[时间] 决策：路径 A or B
[时间] 决策：用户回答的核心问题（路径 A）
[时间] 决策：编排方案 + 用户确认

## Step 12 精加工审查
[时间] 决策：用户标 OK / 有问题

## Step 13 出片
[时间] 决策：命名 + 编码

## Reuse 二次加工（可选）
[时间] 决策：备份时间 + 路径
[时间] 决策：复用时间 + 路径
```

- [ ] **Step 4: 验证**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
grep -c "step_10_review" references/AI行为日志协议.md
grep -c "## Step" references/AI行为日志协议.md
```

预期：第一个 grep 输出 ≥ 1（schema 提到新 stage），第二个 grep 输出 ≥ 9（9 个 step section）

- [ ] **Step 5: Commit**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
git add references/AI行为日志协议.md
git commit -m "fix(v1.12): 扩展 AI行为日志协议 schema (step_10_review/refine/step_12_review/finalize/reuse)"
```

---

## Task 2: 修复 精加工-两路径.md（P0-1, P1-1, P2-4）

**Files:**
- Modify: `references/精加工-两路径.md`

**目的：**Path A 加约束防 AI 自由发挥、新增路径 C（A 主 + B 辅）、沉默处理、加日志集成。

- [ ] **Step 1: 读取当前 Path A 约束**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
grep -n "## 2. 路径 A\|自由发挥\|A.3 AI 设计编排方案" references/精加工-两路径.md
```

- [ ] **Step 2: 在 §2.3 AI 行为约束 中添加 Path A 强约束**

打开 `references/精加工-两路径.md`，找到 §2.3 位置。

当前文档：
```markdown
### 2.3 AI 行为约束

- ✅ **必须**：核心 5 问全部问完才能进 A.3
- ✅ **必须**：用户回答后 AI 复述理解 + 用户确认
- ⚠️ **可选**：补充 3 问 AI 判断后选择性问
- ❌ **禁止**：一次问 10 个问题（用户疲劳）
- ❌ **禁止**：AI 替用户回答"大概是这样吧"
- ❌ **禁止**：跳过问题直接出 v1（"反正用户没耐心"是 AI 揣测）
```

改为（**v1.12 强化**）：
```markdown
### 2.3 AI 行为约束（v1.12 强化）

**Phase 1: 问题收集**：
- ✅ **必须**：核心 5 问全部问完才能进 Phase 2
- ✅ **必须**：用户回答后 AI 复述理解 + 用户确认
- ⚠️ **可选**：补充 3 问 AI 判断后选择性问
- ❌ **禁止**：一次问 10 个问题（用户疲劳）

**Phase 2: 编排方案 + 用户确认**（v1.12 新增，**最重要**）：
- ✅ **必须**：AI 设计完编排方案后**先复述给用户**（不直接出片）
  ```
  AI 输出格式：
  "我打算这样编排：
    - 顺序：video_1 → video_3 → video_2
    - 用这些 op：trim 0-5s、color preset 电影感、xfade fade 0.5s
    - 加 1 个炫酷参数：[参数描述]
    - 预计时长：X 秒
    满意吗？"
  ```
- ✅ **必须**：用户**明确**同意后才执行
- ✅ **必须**：炫酷参数**单独列出**让用户逐项确认
- ❌ **禁止**：AI 跳过复述直接执行
- ❌ **禁止**：AI 一次性给完整编排不解释
- ❌ **禁止**：AI 替用户说"看起来 OK"

**Phase 3: 出片**：
- ✅ **必须**：默认 1 个版本（v1）
- ✅ **必须**：每完成 1 个 CLI 调 write JSONL entry（stage=refine）

**炫酷参数上限**：
- ✅ 最多 2 个非标准 op（如多画面叠加/动态文字）
- ❌ 禁止超过（用户没明确说"随便加"）
- ✅ 例外：用户明确说"放手做" → 上限 5 个
```

- [ ] **Step 3: 添加 §3 路径 C（A 主 + B 辅）**

在 §3 路径 B 后插入新章节。找到 "## 4. 路径 A vs 路径 B 对比"，在它**之前**插入：

```markdown
## 3.5 路径 C：A 主 + B 辅（v1.12 新增）

**适用场景**：用户走路径 A 出 v1 后说"风格可以但想加某个特效"——需要混合。

### 3.5.1 流程

```
C.1 用户走完路径 A 的 A.1-A.4（出 v1）
C.2 用户对 v1 说"满意风格但想加 X 特效"（X 必须在 yaml 里存在）
C.3 AI 加载 X 对应的 yaml stage（不是整个 yaml）
C.4 AI 把 X stage 应用到路径 A 的 v1 上 → 出 v2
C.5 用户可继续追问 / 确认 OK → Step 12 审查
```

### 3.5.2 AI 行为约束

- ✅ **必须**：X 必须在某个 yaml 模板的某个 stage 里有定义
- ✅ **必须**：用户明确说"X 特效"（"加个转场"不算，要"加 fade 转场"）
- ❌ **禁止**：AI 自己选 X（"我觉得你应该加 X"）
- ❌ **禁止**：AI 把整个 yaml 应用到路径 A 产物上（会破坏 v1 风格）
- ❌ **禁止**：X 不在 yaml 里时 AI 自创（违反红线契约）
```

- [ ] **Step 4: 添加 §2.6 沉默处理协议**

在 §2.5 之后插入：

```markdown
### 2.6 沉默处理协议（v1.12 新增）

**用户沉默的判定**：
- AI 问完核心问题后 30 秒内无响应 → 沉默
- AI 输出 v1 后 30 秒内无 OK/通过/不满意 → 沉默
- 用户输入不相关内容（如"嗯"） → 不是响应

**AI 行为**：
- ✅ **必须**：明确再次确认（"我没收到您的反馈。是满意、不满意、还是有疑问？"）
- ✅ **必须**：给出 3 个明确选项（"满意 / 不满意 / 补充信息"）
- ❌ **禁止**：AI 替用户说"看起来用户满意"
- ❌ **禁止**：AI 默认用户 OK 进入下一阶段

**超时升级**（v1.12 新增）：
- 沉默 ≥ 5 分钟 → AI 写入 logs/<task_id>.jsonl `action=user_silent, decision=waiting_user_input`
- 沉默 ≥ 30 分钟 → AI 明确告知用户"我先暂停，您回来后说'继续'即可"
- ❌ 禁止：AI 默默继续后续步骤
```

- [ ] **Step 5: 验证**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
grep -c "Phase 2" references/精加工-两路径.md
grep -c "路径 C" references/精加工-两路径.md
grep -c "沉默处理" references/精加工-两路径.md
```

预期：三个 grep 各输出 ≥ 1

- [ ] **Step 6: Commit**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
git add references/精加工-两路径.md
git commit -m "fix(v1.12): 精加工路径 A 加约束 + 路径 C（A 主 B 辅）+ 沉默处理协议"
```

---

## Task 3: 修复 审查-用户交互循环.md（P0-3, P1-3）

**Files:**
- Modify: `references/审查-用户交互循环.md`

**目的：**5 次阈值改可配置（不同问题不同阈值）、抗用户疲劳（批量汇报 + 分组审查）、集成日志。

- [ ] **Step 1: 读取 §4 异常处理**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
grep -n "## 4. 异常处理\|≥ 5 次" references/审查-用户交互循环.md
```

- [ ] **Step 2: 重写 §4.1 阈值**

找到 §4.1 反复修改不收敛。

当前文档：
```markdown
### 4.1 反复修改不收敛

同一项被重跑 ≥ 5 次仍未通过 → AI 暂停
明确告知用户：「此问题需要你人工介入判断」
让用户决策：
  (a) 接受现状（将该项标 OK）
  (b) 进一步要求（继续重跑）
  (c) 放弃此素材（跳过该项）
```

改为（**v1.12 改进**）：
```markdown
### 4.1 反复修改不收敛（v1.12 阈值可配置）

**默认阈值**（不同问题不同）：
- 基础问题（trim/color/ASR）：3 次
- 创意问题（路径 A 编排/路径 B stage）：5 次
- 用户主动设的阈值：覆盖默认

**触发暂停条件**（任一）：
- 达到该问题类型的阈值
- 用户说"先停一下" / "我看看"
- AI 跑出相同错误 3 次（说明不是参数问题，是逻辑问题）

**AI 暂停行为**：
1. 写 logs/<task_id>.md `## Review Issue` 记录每次重跑的差异
2. 明确告知用户：「此问题 X 次未通过。你想：
   (a) 接受现状
   (b) 继续重跑（增加阈值）
   (c) 跳过此项
   (d) 换种方式（如改参数/换工具）」
3. 等用户明确决策

**用户决策后**：
- (a) 标 OK → 继续
- (b) 增加阈值 → 继续重跑
- (c) 跳过 → 标"跳过"，继续
- (d) 改参数 → 重跑（重置次数）
```

- [ ] **Step 3: 添加 §5 抗疲劳协议（NEW）**

在 §4 异常处理之后插入：

```markdown
## 5. 抗用户疲劳协议（v1.12 新增）

### 5.1 批量汇报（粗加工）

**触发**：Step 9.3 单视频处理 ≥ 10 个视频

**AI 行为**：
- ❌ 禁止：每处理完一个就立即汇报（"已处理 video_1.mp4"）
- ✅ **必须**：每 10 个汇报一次
- ✅ **必须**：汇报格式：

```
[批量汇报 1/5]
  已完成：video_1 至 video_10
  成功：8 个
  异常：2 个（profile.error 非空）
  下次汇报：video_11 至 video_20
  继续处理中...
```

### 5.2 分组审查（Step 10 + Step 12）

**AI 行为**：
- ❌ 禁止：列出所有 100+ 产物让用户逐项标 OK
- ✅ **必须**：按类别分组（单视频 / 组合 / 文字稿 / 封面），用户可只审一类
- ✅ **必须**：提供"一键全部 OK" 选项（前提是用户**明确说**"我信任你，全部 OK"）

```
AI 输出格式：
"粗加工产物分 4 类：
  - 单视频：30 个
  - 组合：5 个
  - 文字稿：10 个
  - 封面：3 个

【审查选项】
  A) 全部 OK（基于产物统计 + 决策.md 推荐）
  B) 只审单视频
  C) 只审组合
  D) 全部详细审查"
```

### 5.3 精加工路径 A 选问（v1.12 优化）

**AI 行为**：
- ❌ 禁止：5 个核心问题**全部**问（用户答 5 轮）
- ✅ **必须**：AI 评估用户意图清晰度
  - 意图清晰（如"做一个热血健身 vlog"） → AI 自动推荐编排方案 → 用户只确认
  - 意图模糊（如"做个视频"） → AI 选 3 个核心问题问（其他 2 个默认）
```

- [ ] **Step 4: 添加日志集成**

在文件末尾 §6 之前插入：

```markdown
## 6. 日志集成（v1.12 强制）

**审查时 AI 必写日志**：

每次审查（Step 10 + Step 12）AI 必须写：
- `logs/<task_id>.jsonl`：`stage=step_10_review` 或 `step_12_review`
- `logs/<task_id>.md`：`## Step 10 粗加工审查` 或 `## Step 12 精加工审查` section

**每个 OK/有问题决定都写一行 JSONL**：
```json
{"time":"2026-07-10T11:00:00","stage":"step_10_review","step":"video_3","action":"review","decision":"有问题: ASR 文字错误","thinking":"用户描述'ASR 把'的'识别成'得''","result":"flagged_for_fix","error":null}
```
```

- [ ] **Step 5: 验证**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
grep -c "阈值" references/审查-用户交互循环.md
grep -c "抗用户疲劳" references/审查-用户交互循环.md
grep -c "日志集成" references/审查-用户交互循环.md
```

预期：三个 grep 各输出 ≥ 1

- [ ] **Step 6: Commit**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
git add references/审查-用户交互循环.md
git commit -m "fix(v1.12): 审查阈值可配置 + 抗用户疲劳 + 日志集成"
```

---

## Task 4: 修复 二次加工-复用工作流.md（P0-5, P1-5, P2-1, P2-3）

**Files:**
- Modify: `references/二次加工-复用工作流.md`

**目的：**备份命名格式（含 task_id_slug 防冲突）、完整性校验（5 类产物必须全在）、BACKUP_NOTE.md 自动生成模板、多备份元数据展示、统一命名（粗加工_满意 → 粗加工_备份）。

- [ ] **Step 1: 读取当前命名约定**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
grep -n "粗加工_满意\|YYYYMMDD\|BACKUP_NOTE" references/二次加工-复用工作流.md
```

- [ ] **Step 2: 重写 §2.2 命名约定**

当前文档：
```markdown
### 2.2 用户操作（手动）

**步骤**：
1. 创建备份目录：`<workspace>/00_智剪/粗加工_满意_<YYYYMMDD>/`
2. 复制 `00_智剪/粗加工/` 全部内容到备份目录
3. （可选）记录备份说明到 `<备份目录>/BACKUP_NOTE.md`
4. **结束当前对话**，开新对话
```

改为（**v1.12 修复 P0-5**）：
```markdown
### 2.2 用户操作（手动 + AI 辅助）

**命名格式（v1.12 防冲突）**：
```
粗加工_备份_<YYYYMMDD_HHMMSS>_<task_id_slug>

其中：
- YYYYMMDD_HHMMSS = 备份时间戳（秒级精度）
- task_id_slug = intent.json.project.title 转 slug
  规则：转小写、空格 → 短横线、保留中文（兼容剪映）
  示例："健身 vlog 训练" → "健身vlog训练"
       "My Travel Diary" → "my-travel-diary"
```

**完整示例**：
```
00_智剪/粗加工_备份_20260710_140000_fitness-vlog/
00_智剪/粗加工_备份_20260710_141500_健身vlog/
00_智剪/粗加工_备份_20260711_093000_travel-diary/
```

**步骤（v1.12 AI 辅助）**：
1. **AI 在粗加工完成时主动告知备份命令**（用户可一键执行）：

```bash
# AI 输出的备份命令（PowerShell 示例）
$backupDir = "00_智剪\粗加工_备份_$(Get-Date -Format 'yyyyMMdd_HHmmss')_fitness-vlog"
New-Item -ItemType Directory -Path $backupDir
Copy-Item -Recurse "00_智剪\粗加工\*" $backupDir
# AI 自动生成 BACKUP_NOTE.md（见 §2.3 模板）
```

2. 用户执行命令（或手动复制）
3. AI 写入 `logs/<task_id>.jsonl`：`stage=reuse_backup`
4. **结束当前对话**，开新对话
```

- [ ] **Step 3: 添加 §2.3 BACKUP_NOTE.md 自动生成模板**

在 §2.2 后插入：

```markdown
### 2.3 BACKUP_NOTE.md 自动生成（v1.12 强制）

**AI 在备份完成时必须写 BACKUP_NOTE.md**（如果用户未指定路径）：

模板：
```markdown
# 备份说明

**任务名**：<intent.json.project.title>
**task_id_slug**：<slug>
**备份时间**：<ISO 8601 时间戳>
**原始工作目录**：<workspace 绝对路径>
**intent.json 来源**：<intent.json 路径>

## 粗加工产物统计

- 单视频：<X> 个
- 组合：<Y> 个
- 文字稿：<Z> 个
- 封面：<W> 个
- 决策.md：✓ 已备份

## 完整性校验

- [x] 单视频/ 至少 1 个 mp4
- [x] 决策.md 存在
- [x] profile_*.json 无未处理异常
- [x] BACKUP_NOTE.md（本文件）

## 用户备注

（用户可手动添加：为什么备份、后续计划等）
```

**AI 自动填充**：除"用户备注"外，其余字段 AI 自动填。
```

- [ ] **Step 4: 重写 §3.1 检测流程（完整性校验）**

当前文档：
```markdown
3. 检查每个备份是否含标准产物：
   - 单视频/（至少 1 个 mp4）
   - 决策.md
   - 其他可选（组合/文字稿/cover/中间产物）
```

改为（**v1.12 完整性校验**）：
```markdown
3. **校验每个备份完整性（v1.12 强制）**：
   ```
   必须含（缺一不可）：
   ✓ 单视频/ 至少 1 个 mp4
   ✓ 决策.md
   ✓ BACKUP_NOTE.md
   
   推荐含（缺失警告但不阻塞）：
   ⚠️ 组合/
   ⚠️ 文字稿/
   ⚠️ cover/
   ⚠️ 中间产物/
   
   校验失败 → AI 拒绝复用，提示用户补齐
   ```

4. 校验通过 → 触发 §3.2 多备份元数据展示
```

- [ ] **Step 5: 重写 §3.2 多备份展示**

当前文档：
```markdown
AI 输出：
"检测到粗加工备份：
  - 00_智剪/粗加工_满意_20260710/  （X 个单视频，Y 个组合）
  - 00_智剪/粗加工_满意_20260708/  （A 个单视频，B 个组合）"
```

改为（**v1.12 元数据展示**）：
```markdown
AI 输出（每个备份展示决策.md 摘要）：
"检测到 2 个粗加工备份：

[备份 1] 00_智剪/粗加工_备份_20260710_140000_fitness-vlog/
  任务：健身 vlog 训练
  时间：2026-07-10 14:00
  产物：单视频 3 个，组合 2 个，文字稿 3 个，封面 1 个
  决策摘要：trim 0-5s、color 电影感、BGM 添加
  BACKUP_NOTE.md：✓ 完整

[备份 2] 00_智剪/粗加工_备份_20260708_093000_travel-diary/
  任务：旅行日记 v1
  时间：2026-07-08 09:30
  产物：单视频 12 个，组合 3 个，文字稿 12 个，封面 2 个
  决策摘要：拼接 12 段 + 字幕 + 多画面叠加
  BACKUP_NOTE.md：✓ 完整

【复用选项】
  A) 复用备份 1（最新）
  B) 复用备份 2
  C) 重新开始"
```

- [ ] **Step 6: 验证命名统一**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
grep -c "粗加工_备份_" references/二次加工-复用工作流.md
grep -c "粗加工_满意" references/二次加工-复用工作流.md
```

预期：第一个 ≥ 5，第二个 = 0（完全替换）

- [ ] **Step 7: Commit**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
git add references/二次加工-复用工作流.md
git commit -m "fix(v1.12): 备份命名 task_id_slug + 完整性校验 + BACKUP_NOTE 自动生成 + 粗加工_满意 → 粗加工_备份"
```

---

## Task 5: 修复 粗加工-执行契约.md（日志集成 + 批量汇报）

**Files:**
- Modify: `references/粗加工-执行契约.md`

**目的：**集成日志（每个 CLI 调写一行 JSONL）、用户疲劳缓解（批量汇报）。

- [ ] **Step 1: 读取 Step 9.3 当前位置**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
grep -n "Step 9.3 单视频处理\|强制" references/粗加工-执行契约.md
```

- [ ] **Step 2: 在 §3 Step 9.3 加批量汇报 + 日志**

找到 §3 Step 9.3 单视频处理 章节。

当前文档：
```markdown
**强制**：
- 每处理完一个 → 立即向用户汇报（产物路径 + 摘要 + 异常）
- 出现卡死 / 超时 → 立即向用户汇报
```

改为（**v1.12 抗疲劳**）：
```markdown
**强制（v1.12 抗疲劳版）**：
- ❌ **禁止**：每处理完 1 个就立即向用户汇报（用户疲劳）
- ✅ **必须**：每 10 个汇报一次（批量）
- ✅ **必须**：写 `logs/<task_id>.jsonl` 每个 CLI 调用：
  ```json
  {"time":"2026-07-10T11:00:00","stage":"粗加工","step":"9.3","action":"trim","decision":"trim 0-5s for video_3","thinking":"用户意图说要剪开头","result":"exit 0","error":null}
  ```
- ✅ **必须**：卡死 / 超时立即向用户汇报（这是例外）
```

- [ ] **Step 3: 在 §2 Step 9.1 加日志**

找到 §2 Step 9.1 输出 schema 后插入：

```markdown
**日志要求（v1.12 强制）**：
- 写 `logs/<task_id>.jsonl`：stage=粗加工, step=9.1, action=parse_intent
- 异常字段：缺失字段列表（即使整体不退出也要写）
```

- [ ] **Step 4: 在 §3 Step 9.2 加日志**

类似：

```markdown
**日志要求（v1.12 强制）**：
- 每个 ASR 完成写一行：stage=粗加工, step=9.2, action=asr, decision="<model> for <video_name>"
```

- [ ] **Step 5: 验证**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
grep -c "每 10 个汇报" references/粗加工-执行契约.md
grep -c "日志要求" references/粗加工-执行契约.md
```

预期：两个 grep 各输出 ≥ 1

- [ ] **Step 6: Commit**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
git add references/粗加工-执行契约.md
git commit -m "fix(v1.12): 粗加工-执行契约 日志集成 + 批量汇报（抗疲劳）"
```

---

## Task 6: 修复 主流程-阶段编排.md（P0-4, P1-2, P1-4, P2-2）

**Files:**
- Modify: `references/主流程-阶段编排.md`

**目的：**announce fallback（通过日志触发）、回退粒度明确（整体 vs 局部）、intent.json 备份、Step 13 决策点修正。

- [ ] **Step 1: 读取决策点矩阵和状态机图**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
grep -n "决策点矩阵\|状态机图\|Step 13" references/主流程-阶段编排.md
```

- [ ] **Step 2: 修正 §3 决策点矩阵 Step 13**

当前文档：
```markdown
| 13 | 出片确认 | 必须 | 最终命名 + 导出 |
```

改为（**v1.12 修正 P2-2**）：
```markdown
| 13 | **出片完成通知**（事后告知） | 必须（告知即可） | 用户不需要决策，AI 通知完成 + 路径 |
```

- [ ] **Step 3: 重写 §2 状态机图（明确回退粒度）**

当前文档：
```markdown
         ┌─→ [回退到 Step 7]
         │
状态:    意图 → 粗加工产物 → 精加工产物 → 出片
         │            ↑
         │   ┌────────[回退到 Step 11]──┘
         │   │
         └──[复用：备份 + 全新会话重跑]
```

改为（**v1.12 明确回退粒度 P1-2**）：
```markdown
状态机（v1.12 明确回退粒度）：

                         ┌─→ [回退到 Step 7：重新对齐意图]
                         │     重做范围：Step 7+（粗加工可能保留）
                         │
状态:    意图 → 粗加工 → 精加工 → 出片
              │        │        ↑
              │        │   ┌────[回退到 Step 11 整体回退]──┘
              │        │   │     清空精加工产物，从 Step 11 重做
              │        │   │
              │        │   └─→ [回退到 Step 11 局部回退]
              │        │         保留精加工产物，只重跑某个 stage
              │        │
              │        └─→ [复用：备份 + 全新会话]
              │
              └─→ [Step 10 审查不通过 → 回 Step 7]

**回退粒度由用户在审查时决定**：
- 整体回退："全部重做"
- 局部回退："只改 X stage"

AI 必须问清楚，不替用户决定。
```

- [ ] **Step 4: 在 §5 添加 §5.4 intent.json 备份机制**

在 §5.3 之前插入：

```markdown
### 5.4 intent.json 备份（v1.12 新增 P1-4 修复）

**触发**：Step 7 完成（用户确认最终意图后）

**AI 必做**：
1. 复制 `intent.json` 到 `00_智剪/中间产物/intent_backup_<时间戳>.json`
2. 写 `logs/<task_id>.jsonl`：stage=意图对齐, action=backup_intent

**用途**：
- 二次加工复用时如 intent.json 损坏/丢失，可从备份恢复
- 调试时可对比原始意图与粗加工结果

**用户决策**：
- ✅ 默认：每次 Step 7 完成都备份
- ⚠️ 可选：用户说"不备份"则跳过
```

- [ ] **Step 5: 在 §5.1 添加 announce fallback**

找到 §5.1 粗加工完成时 AI 必告知协议，在协议后添加：

```markdown
**announce fallback（v1.12 强制 P0-4）**：

AI 必须在粗加工完成时写日志 `logs/<task_id>.jsonl`：
```json
{"stage":"粗加工","action":"announce_complete","decision":"粗加工完成，X 产物","result":"success"}
```

**自我检测协议**：
- AI 写完上述日志后**必须主动**读自己的日志
- 如果日志中没有 `announce_complete` → AI 必须立即告诉用户"粗加工完成"
- ❌ 禁止 AI 跳过 announce 直接进入 Step 10
```

- [ ] **Step 6: 在 §6 引用表更新**

把"4 个聚焦文件"那行的命名同步：

```markdown
| `references/二次加工-复用工作流.md` | §5 详细：备份目录 + AI 检测 + 用户决策 | 粗加工完成时 + 新会话检测时 |
```

改为（命名统一 P2-1）：
```markdown
| `references/二次加工-复用工作流.md` | §5 详细：备份目录（粗加工_备份_<时间戳>_<slug>） + AI 检测 + 用户决策 | 粗加工完成时 + 新会话检测时 |
```

- [ ] **Step 7: 验证**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
grep -c "intent.json 备份" references/主流程-阶段编排.md
grep -c "回退粒度" references/主流程-阶段编排.md
grep -c "announce fallback" references/主流程-阶段编排.md
grep -c "出片完成通知" references/主流程-阶段编排.md
```

预期：4 个 grep 各 ≥ 1

- [ ] **Step 8: Commit**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
git add references/主流程-阶段编排.md
git commit -m "fix(v1.12): 主流程 announce fallback + 回退粒度 + intent 备份 + Step 13 修正"
```

---

## Task 7: 更新 SKILL.md 加载触发器（v1.12 协议引用）

**Files:**
- Modify: `SKILL.md`

**目的：**让 Loading 触发器反映 v1.12 修复后的新约定（命名统一、阈值可配置等）。

- [ ] **Step 1: 读取 Loading 触发器当前状态**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
grep -n "二次加工-复用工作流\|备份\|粗加工_满意" SKILL.md
```

- [ ] **Step 2: 更新 Loading 触发器 §行为协议触发**

找到行为协议触发表格（§行为协议触发）。

当前文档：
```markdown
| **AI 粗加工完成时 + 新会话检测备份** | `二次加工-复用工作流.md` |
```

改为：
```markdown
| **AI 粗加工完成时**（v1.12 强制 announce + 备份提示） | `二次加工-复用工作流.md` |
| **新会话检测粗加工_备份_*** 目录 | `二次加工-复用工作流.md` |
```

- [ ] **Step 3: 在 §scripts/ 目录命名约定 后添加备份约定**

找到 §scripts/ 章节，在"AI 行为约束"后添加：

```markdown
## 💾 备份目录命名约定（v1.12）

**格式**：`粗加工_备份_<YYYYMMDD_HHMMSS>_<task_id_slug>`

**示例**：
```
00_智剪/粗加工_备份_20260710_140000_fitness-vlog/
00_智剪/粗加工_备份_20260710_141500_健身vlog训练/
```

**规则**：
- YYYYMMDD_HHMMSS = 秒级时间戳（防同日冲突）
- task_id_slug = intent.json.project.title 转 slug（防不同项目冲突）
- 备份目录**只读**，AI 复用时不修改
- 详见 `references/二次加工-复用工作流.md`
```

- [ ] **Step 4: 验证**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
grep -c "粗加工_备份" SKILL.md
grep -c "intent.json 备份" SKILL.md
```

预期：两个 grep 各 ≥ 1

- [ ] **Step 5: Commit**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
git add SKILL.md
git commit -m "fix(v1.12): SKILL.md 更新加载触发器 + 加备份命名约定章节"
```

---

## Task 8: 端到端验证

**Files:**
- Verify: 所有修改的文件

**目的：**确认所有 14 个问题都已修复，无 broken references，一致性达标。

- [ ] **Step 1: 验证所有 14 个问题的 grep 关键字**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"

# P0-1: 路径 A 约束
echo "=== P0-1 Path A 约束 ==="
grep -c "Phase 2" references/精加工-两路径.md

# P0-2: 日志集成
echo "=== P0-2 日志集成 ==="
grep -l "日志集成\|announce_complete\|stage=refine" references/*.md | wc -l

# P0-3: 阈值可配置
echo "=== P0-3 阈值 ==="
grep -c "阈值" references/审查-用户交互循环.md

# P0-4: announce fallback
echo "=== P0-4 announce ==="
grep -c "announce fallback\|announce_complete" references/主流程-阶段编排.md

# P0-5: 备份命名
echo "=== P0-5 备份命名 ==="
grep -c "粗加工_备份_" references/二次加工-复用工作流.md

# P1-1: 路径 C
echo "=== P1-1 路径 C ==="
grep -c "路径 C" references/精加工-两路径.md

# P1-2: 回退粒度
echo "=== P1-2 回退粒度 ==="
grep -c "回退粒度" references/主流程-阶段编排.md

# P1-3: 抗疲劳
echo "=== P1-3 抗疲劳 ==="
grep -c "抗用户疲劳\|批量汇报" references/审查-用户交互循环.md

# P1-4: intent.json 备份
echo "=== P1-4 intent 备份 ==="
grep -c "intent.json 备份" references/主流程-阶段编排.md

# P1-5: 多备份元数据
echo "=== P1-5 多备份 ==="
grep -c "BACKUP_NOTE.md" references/二次加工-复用工作流.md

# P2-1: 路径命名统一
echo "=== P2-1 路径命名 ==="
grep -c "粗加工_满意" references/*.md | grep -v ":0$" || echo "(0 旧名残留)"

# P2-2: Step 13 修正
echo "=== P2-2 Step 13 ==="
grep -c "出片完成通知" references/主流程-阶段编排.md

# P2-3: BACKUP_NOTE 模板
echo "=== P2-3 BACKUP_NOTE ==="
grep -c "## 完整性校验" references/二次加工-复用工作流.md

# P2-4: 沉默处理
echo "=== P2-4 沉默处理 ==="
grep -c "沉默处理" references/精加工-两路径.md
```

预期：每个 grep 都 ≥ 1（除 P2-1 应该 0 残留）

- [ ] **Step 2: 验证无残留旧命名**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
grep -r "粗加工_满意" references/ SKILL.md
```

预期：无输出（完全替换为粗加工_备份）

- [ ] **Step 3: 验证引用一致性**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
echo "=== 主流程 引用的 4 个聚焦文件 ==="
grep -E "粗加工-执行契约|精加工-两路径|审查-用户交互循环|二次加工-复用工作流" references/主流程-阶段编排.md | head -10
echo ""
echo "=== SKILL.md Loading 触发器引用 ==="
grep -E "粗加工-执行契约|精加工-两路径|审查-用户交互循环|二次加工-复用工作流" SKILL.md
```

预期：4 个文件都被引用，无 broken link

- [ ] **Step 4: 验证 JSONL schema 一致性**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
echo "=== 新 stage 枚举值跨文件一致 ==="
for stage in step_10_review refine step_12_review finalize reuse_backup reuse_apply; do
  echo "--- $stage ---"
  grep -l "stage.*$stage\|$stage.*stage" references/*.md | head -3
done
```

预期：每个 stage 在 多个文件中被引用

- [ ] **Step 5: 验证 git status 干净**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
git status
```

预期：working tree clean（除 submodule 改动）

- [ ] **Step 6: 最终 commit**

```bash
cd "D:/2Study/StudyNotes/SKILLS/智剪工坊"
git log --oneline -10
```

预期：8 个新 commits 对应 8 个 tasks

---

## Self-Review

**1. Spec coverage:**
- ✅ P0-1 路径 A 约束 → Task 2
- ✅ P0-2 日志集成 → Task 1 (schema) + Task 5 (粗加工集成) + Task 3 (审查集成)
- ✅ P0-3 阈值可配置 → Task 3
- ✅ P0-4 announce fallback → Task 6
- ✅ P0-5 备份命名 → Task 4
- ✅ P1-1 路径 C → Task 2
- ✅ P1-2 回退粒度 → Task 6
- ✅ P1-3 抗疲劳 → Task 3 + Task 5
- ✅ P1-4 intent.json 备份 → Task 6
- ✅ P1-5 多备份元数据 → Task 4
- ✅ P2-1 路径命名统一 → Task 4
- ✅ P2-2 Step 13 修正 → Task 6
- ✅ P2-3 BACKUP_NOTE 模板 → Task 4
- ✅ P2-4 沉默处理 → Task 2

**2. Placeholder scan:**
- 无 TBD / TODO / "implement later"
- 无 "similar to Task N"（每个 task 独立）
- 所有代码块完整（content 用 ```markdown 包裹示例 JSON）
- 所有命令完整（带 cd 路径）

**3. Type consistency:**
- 文件名一致（references/ 下固定路径）
- 命名格式一致（粗加工_备份_YYYYMMDD_HHMMSS_<slug>）
- Stage 字段值跨文件一致（step_10_review / refine / step_12_review / finalize / reuse_backup / reuse_apply）
- JSONL schema 字段一致（time/stage/step/action/decision/thinking/result/error）