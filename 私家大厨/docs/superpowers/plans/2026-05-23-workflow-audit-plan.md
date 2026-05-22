# AI技能执行者工作流审计 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 以AI执行者视角走查私家大厨技能全部7个功能，发现阻塞性故障和逻辑矛盾，产出可直接修复的问题清单。

**Architecture:** 按功能模块逐个审计，每个任务读取对应的功能文件和命令参考，模拟AI执行者推演完整工作流，记录所有发现的故障。任务1-8互相独立可并行，任务9-10依赖前序结果，任务11为汇总。

**Tech Stack:** SQLite, Python CLI scripts, Markdown feature files

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `SKILL.md` | 路由算法、优先级规则 |
| `features/view.md` | 查看食谱 + 做菜模式 |
| `features/search.md` | 搜索筛选 |
| `features/update.md` | 修改食谱 |
| `features/history.md` | 烹饪历史 |
| `features/shopping.md` | 采购清单 |
| `features/add.md` | 录入食谱 |
| `references/commands.md` | CLI命令完整参考 |
| `references/database_schema.md` | 数据库表结构 |
| `references/categories.md` | 分类值参考 |
| `scripts/recipe_import.py` | JSON导入脚本 |
| `scripts/recipe_manager.py` | 食谱主表管理 |
| `scripts/category_manager.py` | 分类管理 |
| `scripts/step_manager.py` | 步骤管理 |
| `scripts/ingredient_manager.py` | 食材管理 |
| `scripts/history_manager.py` | 历史管理 |
| `scripts/shopping_manager.py` | 采购清单管理 |
| `docs/superpowers/specs/2026-05-23-ai-executor-workflow-audit-design.md` | 审计设计文档 |

---

### Task 1: 路由层审计

**Files:**
- Read: `SKILL.md`（路由算法和路由表部分，约第30-175行）
- Create: `docs/superpowers/audit/01-routing-audit.md`

- [ ] **Step 1: 读取路由规则**

读取 `SKILL.md` 第30-175行，提取：
- 7个优先级的触发关键词列表
- 菜名提取规则（触发词后面的文字，≥2字符）
- 兜底规则（无命中→search.md）

- [ ] **Step 2: 构造10条测试用例并逐一推演**

按以下输入逐一推演路由匹配结果：

| # | 用户输入 | 预期路由 | 预期菜名 | 检查点 |
|---|---------|---------|---------|--------|
| 1 | "开始做宫保虾球" | P1 做菜模式 | 宫保虾球 | "开始做"是否在P1触发词列表中 |
| 2 | "看看宫保虾球" | P2 查看食谱 | 宫保虾球 | "看看"是否在P2触发词列表中 |
| 3 | "宫保虾球菜谱" | P2 查看食谱 | 宫保虾球 | "菜谱"在"宫保虾球"后面，菜名提取是否正确 |
| 4 | "找川菜" | P3 搜索筛选 | 川菜 | "找"是否在P3触发词列表中 |
| 5 | "哪些菜里有虾" | P3 搜索筛选 | 无 | "哪些菜"命中后，"里有虾"是否<2字符被正确过滤 |
| 6 | "把宫保虾球第2步改成小火" | P4 修改食谱 | 宫保虾球 | "改成"是否在P4触发词列表中 |
| 7 | "宫保虾球做过几次了" | P5 烹饪历史 | 宫保虾球 | "做过"是否在P5触发词列表中 |
| 8 | "宫保虾球采购清单" | P6 采购清单 | 宫保虾球 | "清单"是否在P6触发词列表中 |
| 9 | "录入一个新菜" | P7 录入食谱 | 无 | "录入"命中后，"一个新菜"是否<2字符被正确过滤 |
| 10 | "宫保虾球" | P3 兜底搜索 | 宫保虾球 | 无触发词命中，走兜底search.md |

对每条用例：
1. 从SKILL.md中找到对应的触发词
2. 验证菜名提取逻辑
3. 记录匹配结果是否正确

- [ ] **Step 3: 检查优先级冲突**

检查是否存在同一输入可能匹配多个优先级的情况：
- "开始做宫保虾球"：P1"开始做" vs P2"看看"（应走P1）
- "宫保虾球菜谱"：P2"菜谱" vs 兜底（应走P2）
- "宫保虾球做过几次了"：P5"做过" vs 兜底（应走P5）

记录所有优先级冲突或歧义。

- [ ] **Step 4: 检查菜名提取边界情况**

测试以下边界输入：
- "做菜模式"（无菜名）→ 应追问
- "做"（单字触发词，但"做"不在触发词列表中）→ 应走兜底
- "看看"（无菜名）→ 应追问
- "找"（无菜名）→ 应追问
- "宫保"（单个菜名，2字符刚好）→ 应走兜底搜索

- [ ] **Step 5: 写入审计报告**

将所有发现写入 `docs/superpowers/audit/01-routing-audit.md`，格式：

```markdown
# 路由层审计报告

## 测试结果

| # | 用户输入 | 预期路由 | 实际路由 | 结果 |
|---|---------|---------|---------|------|
| 1 | ... | ... | ... | ✅/❌ |

## 发现的故障

### [P0/P1/P2/P3] 故障标题
- **位置**：SKILL.md:行号
- **现象**：...
- **复现路径**：...
- **修复建议**：...
```

- [ ] **Step 6: 提交**

```bash
git add docs/superpowers/audit/01-routing-audit.md
git commit -m "audit: 路由层审计报告"
```

---

### Task 2: P1 做菜模式走查

**Files:**
- Read: `features/view.md`（功能二：做菜模式部分，约第110-270行）
- Read: `references/commands.md`（step_manager、step_ingredient_manager、technique_manager部分）
- Read: `references/database_schema.md`（cooking_steps、step_ingredients、step_techniques表）
- Create: `docs/superpowers/audit/02-p1-cooking-mode-audit.md`

- [ ] **Step 1: 读取做菜模式的完整工作流**

读取 `features/view.md` 第110-270行，提取：
- 步骤类型定义（normal vs wait）
- 8个核心约束（Must）
- 3个Bug修复约束
- 计时器恢复算法
- 依赖检查算法
- 文件规范（命名、路径）

- [ ] **Step 2: 模拟"开始做宫保虾球"的完整流程**

以AI执行者视角推演：
1. 用户输入"开始做宫保虾球"
2. 路由匹配→P1做菜模式→加载view.md
3. 复用查看食谱已查询的数据（但如果是直接进入做菜模式，没有预先查询的数据）
4. 检查：是否需要先执行查看食谱的查询流程？

重点检查：
- 做菜模式是否依赖查看食谱的查询结果
- 如果用户直接说"开始做XX"，没有预先查看，数据从哪来
- view.md中的命令参考（第282-323行）是否覆盖了所有需要的数据

- [ ] **Step 3: 检查外部技能依赖**

读取view.md中的外部技能引用：
- Taste Skill: `~/.openclaw/skills/taste-skill/SKILL.md`
- UI/UX Pro Max: `~/.openclaw/skills/ui-ux-pro-max/SKILL.md`

以及底部的参考路径：
- Taste Skill: `/mnt/d/2Study/StudyNotes/SKILLS/taste-skill/skills/taste-skill/SKILL.md`
- UI/UX Pro Max: `/mnt/d/2Study/StudyNotes/SKILLS/ui-ux-pro-max-skill/.claude/skills/ui-ux-pro-max/SKILL.md`

检查：
- 两处路径是否一致（~/.openclaw vs /mnt/d/...）
- 哪个路径是正确的
- 如果路径不存在会发生什么

- [ ] **Step 4: 检查HTML生成约束的可执行性**

验证view.md中的HTML生成要求是否完整可执行：
- 文件命名：`烹饪之途_{菜名}_{时间戳}.html`
- 存储路径：`/home/feather/.openclaw/media/qqbot/`
- 8个核心约束是否有歧义
- 3个Bug修复约束是否清晰

重点检查：
- 等待面板设计规范中"已到期等待步骤（高亮）"重复出现了两次（第249行和第255行）
- 存储路径在第267-269行重复出现了两次
- 计时器约束是否足够清晰，AI能否正确实现

- [ ] **Step 5: 检查查询命令的完整性**

对比view.md的命令参考（第282-323行）与功能需求：
- 做菜模式需要哪些数据？
- 命令参考是否覆盖了所有需要的查询？
- 是否有遗漏的查询？

- [ ] **Step 6: 写入审计报告并提交**

将所有发现写入 `docs/superpowers/audit/02-p1-cooking-mode-audit.md`，按故障记录格式。

```bash
git add docs/superpowers/audit/02-p1-cooking-mode-audit.md
git commit -m "audit: P1做菜模式走查报告"
```

---

### Task 3: P2 查看食谱走查

**Files:**
- Read: `features/view.md`（功能一：查看食谱部分，约第90-108行）
- Read: `references/commands.md`（recipe_manager show、category_manager list等）
- Create: `docs/superpowers/audit/03-p2-view-recipe-audit.md`

- [ ] **Step 1: 读取查看食谱的完整工作流**

读取 `features/view.md` 第60-108行，提取：
- 工作流：查询→设计→生成→发送
- HTML生成要求
- 文件规范

- [ ] **Step 2: 模拟"看看宫保虾球怎么做"的完整流程**

以AI执行者视角推演：
1. 用户输入"看看宫保虾球怎么做"
2. 路由匹配→P2查看食谱→加载view.md功能一
3. 执行查询命令清单
4. 调用Taste Skill + UI/UX Pro Max
5. 生成HTML
6. 保存到媒体目录
7. 通过QQBot发送文件

重点检查：
- 查询命令清单是否完整（需要查哪些表）
- 查询顺序是否正确（先查recipe_id，再查关联表）
- 每个查询命令的参数格式是否正确

- [ ] **Step 3: 检查HTML生成的核心要求**

view.md第97-98行："查询到的每类数据必须在HTML里有对应的展示位置，不允许'查了但没用'"

检查：
- 查询了哪些数据类别？
- HTML展示要求是否覆盖了所有类别？
- 如果某类数据为空，处理方式是否明确？

- [ ] **Step 4: 检查内部分流逻辑**

view.md第27-35行的内部分流：
- "开始做这道菜"→直接进入做菜模式
- "看看XX怎么做"→先展示食谱，末尾问"要开始做吗？"

检查：
- 这个分流逻辑是否清晰？
- AI能否正确判断用户意图？
- 从查看模式切换到做菜模式时，数据是否正确复用？

- [ ] **Step 5: 写入审计报告并提交**

```bash
git add docs/superpowers/audit/03-p2-view-recipe-audit.md
git commit -m "audit: P2查看食谱走查报告"
```

---

### Task 4: P3 搜索筛选走查

**Files:**
- Read: `features/search.md`（全部）
- Read: `references/commands.md`（各manager的search命令）
- Create: `docs/superpowers/audit/04-p3-search-audit.md`

- [ ] **Step 1: 读取搜索功能的完整定义**

读取 `features/search.md`，提取：
- 6种搜索方式
- 每种搜索的CLI命令
- 搜索结果格式
- 空结果格式

- [ ] **Step 2: 模拟"找川菜"的流程**

1. 用户输入"找川菜"
2. 路由匹配→P3搜索筛选→加载search.md
3. 执行：`python scripts/category_manager.py search 川菜`
4. 返回结果格式

重点检查：
- 命令格式是否正确
- 返回结果的展示格式是否明确

- [ ] **Step 3: 模拟"哪些菜里有虾"的流程**

1. 用户输入"哪些菜里有虾"
2. 路由匹配→P3→"哪些菜"触发词→菜名提取"里有虾"→<2字符→无菜名
3. 执行：`python scripts/ingredient_manager.py search 虾`

重点检查：
- 菜名提取逻辑：触发词"哪些菜"后面是"里有虾"，但实际搜索词应该是"虾"
- AI能否正确从"哪些菜里有虾"中提取出搜索词"虾"？
- 这里是否有歧义？

- [ ] **Step 4: 模拟组合搜索的流程**

1. 用户输入"找个辣的川菜，30分钟能搞定的"
2. 路由匹配→P3→"找"触发词
3. 执行步骤：先按菜系搜索，再过滤时间和口味

重点检查：
- 组合搜索的执行步骤是否清晰
- AI能否正确解析多个筛选条件
- 是否有更高效的命令方式

- [ ] **Step 5: 检查搜索结果的后续引导**

search.md第126-148行的结果格式：
- 标准格式包含"想看哪道的做法？说'看看第X道'或直接说菜名"
- 空结果格式包含建议

检查：
- 后续引导是否与路由规则一致
- 用户说"看看第1道"时，AI能否正确处理

- [ ] **Step 6: 写入审计报告并提交**

```bash
git add docs/superpowers/audit/04-p3-search-audit.md
git commit -m "audit: P3搜索筛选走查报告"
```

---

### Task 5: P4 修改食谱走查

**Files:**
- Read: `features/update.md`（全部）
- Read: `references/commands.md`（各manager的update/add命令）
- Create: `docs/superpowers/audit/05-p4-update-audit.md`

- [ ] **Step 1: 读取修改功能的完整定义**

读取 `features/update.md`，提取：
- 12种修改类型
- 每种修改的CLI命令
- 写操作确认格式
- "只增不删"原则

- [ ] **Step 2: 模拟"把宫保虾球第2步改成小火"的流程**

1. 用户输入"把宫保虾球第2步改成小火"
2. 路由匹配→P4修改食谱→加载update.md
3. AI需要：
   a. 先查询当前第2步的内容（需要step_id）
   b. 展示修改前后对比
   c. 用户确认后执行update命令

重点检查：
- AI如何获取step_id？需要先查询步骤列表
- update.md中是否有说明这个两步流程？
- step_manager.py update命令的参数格式是否正确

- [ ] **Step 3: 模拟"给宫保虾球加一个食材"的流程**

1. 用户输入"给宫保虾球加一个食材，姜丝10g，在第4步加入"
2. AI需要：
   a. 查询recipe_id
   b. 执行ingredient_manager.py add
   c. 获取ingredient_id
   d. 查询第4步的step_id
   e. 执行step_ingredient_manager.py add

重点检查：
- 这个多步操作的流程是否清晰
- AI能否正确处理中间ID的获取
- 如果某一步失败，是否有错误处理说明

- [ ] **Step 4: 模拟"不想要宫保虾球了"的流程**

1. 用户输入"不想要宫保虾球了"
2. 路由匹配→P4修改食谱（"不想要"是否命中触发词？）

重点检查：
- "不想要"是否在P4触发词列表中
- 如果不在，这个输入会走哪个路由？
- 废弃食谱的触发方式是否明确

- [ ] **Step 5: 检查写操作确认格式**

update.md第166-181行的确认格式：
```
【修改前】
- 难度：中等
【修改后】
- 难度：困难
确认吗？说"对"执行。
```

检查：
- 确认格式是否足够清晰
- AI能否正确构造修改前后的对比

- [ ] **Step 6: 写入审计报告并提交**

```bash
git add docs/superpowers/audit/05-p4-update-audit.md
git commit -m "audit: P4修改食谱走查报告"
```

---

### Task 6: P5 烹饪历史走查

**Files:**
- Read: `features/history.md`（全部）
- Read: `references/commands.md`（history_manager部分）
- Create: `docs/superpowers/audit/06-p5-history-audit.md`

- [ ] **Step 1: 读取历史功能的完整定义**

读取 `features/history.md`，提取：
- 4种操作（记录、查看历史、查看统计、更新记录）
- 每种操作的CLI命令
- 字段说明和推测规则
- 评分参考

- [ ] **Step 2: 模拟"今天做了宫保虾球，评分4.5"的流程**

1. 用户输入"今天做了宫保虾球，评分4.5"
2. 路由匹配→P5烹饪历史→加载history.md
3. AI需要：
   a. 查询recipe_id
   b. 执行history_manager.py add

重点检查：
- cook_date的默认值处理（用户说"今天"→默认当天）
- rating的范围验证（1-5）
- feedback是否必须（用户未提供时如何处理）

- [ ] **Step 3: 模拟"宫保虾球做过几次了"的流程**

1. 用户输入"宫保虾球做过几次了"
2. 路由匹配→P5→"做过"触发词
3. 执行：`python scripts/history_manager.py list 宫保虾球`

重点检查：
- 命令中是否可以直接使用菜名（而非recipe_id）
- history_manager.py list命令是否支持菜名参数

- [ ] **Step 4: 检查评分参考的一致性**

history.md第150-159行的评分参考：
- 5.0=完美，4.5=很好，4.0=好，3.5=还可以，3.0=一般，<3.0=失败

检查：
- 评分参考是否与数据库约束一致（1-5，是否支持小数）
- AI能否正确使用这个评分标准

- [ ] **Step 5: 写入审计报告并提交**

```bash
git add docs/superpowers/audit/06-p5-history-audit.md
git commit -m "audit: P5烹饪历史走查报告"
```

---

### Task 7: P6 采购清单走查

**Files:**
- Read: `features/shopping.md`（全部）
- Read: `references/commands.md`（shopping_manager部分）
- Create: `docs/superpowers/audit/07-p6-shopping-audit.md`

- [ ] **Step 1: 读取采购清单的完整定义**

读取 `features/shopping.md`，提取：
- 工作流
- 命令格式
- JSON输出格式
- HTML生成要求（14项）
- 文件规范

- [ ] **Step 2: 模拟"宫保虾球采购清单"的流程**

1. 用户输入"宫保虾球采购清单"
2. 路由匹配→P6采购清单→加载shopping.md
3. AI需要：
   a. 查询recipe_id
   b. 执行shopping_manager.py generate
   c. 解析JSON输出
   d. 生成HTML
   e. 保存到指定路径
   f. 通过QQBot发送

重点检查：
- shopping_manager.py generate命令是否支持菜名参数
- JSON输出格式是否与文档一致
- HTML生成的14项要求是否完整可执行

- [ ] **Step 3: 模拟多食谱采购清单的流程**

1. 用户说"宫保虾球和辣炒虾球的采购清单"
2. AI需要：
   a. 查询两个recipe_id
   b. 执行shopping_manager.py generate "id1,id2"
   c. 处理同名食材合并

重点检查：
- 多ID的命令格式是否正确
- 同名食材合并逻辑是否明确
- "按分类看"和"按食谱看"两种视图的切换逻辑

- [ ] **Step 4: 检查HTML存储路径**

shopping.md第134-136行：
```
/home/feather/.openclaw/media/qqbot/shopping/
```

检查：
- 这个路径与view.md中的路径是否一致
- view.md是`/home/feather/.openclaw/media/qqbot/`，shopping.md是`.../qqbot/shopping/`
- 这个差异是有意的还是错误

- [ ] **Step 5: 写入审计报告并提交**

```bash
git add docs/superpowers/audit/07-p6-shopping-audit.md
git commit -m "audit: P6采购清单走查报告"
```

---

### Task 8: P7 录入食谱走查

**Files:**
- Read: `features/add.md`（全部）
- Read: `scripts/recipe_import.py`（前100行，了解CLI接口）
- Read: `templates/recipe_template.json`
- Read: `references/commands.md`（recipe_import部分）
- Create: `docs/superpowers/audit/08-p7-add-recipe-audit.md`

- [ ] **Step 1: 读取录入功能的完整定义**

读取 `features/add.md`，提取：
- 两种输入方式（图片OCR、MD文件）
- 字段推测规则
- 交互流程
- 同名冲突处理
- JSON导入流程

- [ ] **Step 2: 模拟传统CLI录入流程**

1. 用户发送食谱图片
2. AI解析后展示确认信息
3. 用户确认后执行10步CLI命令

重点检查：
- 10步CLI命令的顺序是否正确
- 每步命令的参数格式是否正确
- 中间ID的获取是否正确
- 如果某一步失败，是否有错误处理

- [ ] **Step 3: 模拟JSON导入流程**

1. AI收集食谱信息
2. 生成JSON文件
3. 执行：`python scripts/recipe_import.py import recipe.json`

重点检查：
- recipe_import.py的CLI接口是否与add.md描述一致
- JSON模板是否完整
- 验证规则是否覆盖所有必填字段
- 冲突处理的4个选项是否正确实现

- [ ] **Step 4: 检查同名冲突处理**

add.md第127-171行的冲突处理：
- 第一次调用检测冲突
- 返回JSON格式的冲突信息
- AI根据用户意图选择action

重点检查：
- recipe_manager.py add命令是否支持--choice参数
- 冲突JSON格式是否与文档一致
- 4个action（view/derive/update/cancel）是否都正确实现

- [ ] **Step 5: 检查字段推测规则的一致性**

add.md第25-39行的推测规则 vs SKILL.md中的"字段推测规则"引用：
- 两处是否一致
- 是否有遗漏的字段
- 推测规则是否合理

- [ ] **Step 6: 写入审计报告并提交**

```bash
git add docs/superpowers/audit/08-p7-add-recipe-audit.md
git commit -m "audit: P7录入食谱走查报告"
```

---

### Task 9: 依赖链审计

**Files:**
- Read: 所有features/*.md（提取外部依赖引用）
- Read: `scripts/db_config.py`（数据库路径配置）
- Create: `docs/superpowers/audit/09-dependency-audit.md`

**Dependencies:** Tasks 2-8 must be completed first (to collect all external references)

- [ ] **Step 1: 提取所有外部依赖引用**

从所有feature文件中提取：
- 外部技能路径
- 文件存储路径
- 数据库路径
- 脚本路径

汇总成依赖清单。

- [ ] **Step 2: 验证外部技能路径**

检查以下路径是否存在：
- `~/.openclaw/skills/taste-skill/SKILL.md`
- `~/.openclaw/skills/ui-ux-pro-max/SKILL.md`
- `/mnt/d/2Study/StudyNotes/SKILLS/taste-skill/skills/taste-skill/SKILL.md`
- `/mnt/d/2Study/StudyNotes/SKILLS/ui-ux-pro-max-skill/.claude/skills/ui-ux-pro-max/SKILL.md`

记录哪些存在，哪些不存在。

- [ ] **Step 3: 验证文件存储路径**

检查以下路径是否可写：
- `/home/feather/.openclaw/media/qqbot/`
- `/home/feather/.openclaw/media/qqbot/shopping/`

记录路径是否存在，是否有写入权限。

- [ ] **Step 4: 验证数据库和脚本**

检查：
- `scripts/db_config.py`中的数据库路径
- 所有manager脚本是否存在
- `scripts/recipe_import.py`是否存在

- [ ] **Step 5: 写入审计报告并提交**

```bash
git add docs/superpowers/audit/09-dependency-audit.md
git commit -m "audit: 依赖链审计报告"
```

---

### Task 10: 交叉引用一致性检查

**Files:**
- Read: `references/commands.md`（全部）
- Read: 所有features/*.md（命令引用部分）
- Create: `docs/superpowers/audit/10-cross-reference-audit.md`

**Dependencies:** Tasks 2-8 must be completed first (to collect all command references)

- [ ] **Step 1: 提取所有feature文件中的CLI命令引用**

从每个feature文件中提取所有CLI命令，记录：
- 命令格式
- 参数名
- 必填/可选标记

- [ ] **Step 2: 与commands.md逐一对比**

对比每个命令：
- 格式是否一致
- 参数名是否拼写正确
- 必填/可选标记是否一致
- 字段值范围是否一致

记录所有不一致。

- [ ] **Step 3: 检查数据库表名和字段名**

从feature文件中提取所有表名和字段名，与database_schema.md对比：
- 表名是否正确
- 字段名是否正确
- 字段类型是否正确

- [ ] **Step 4: 检查分类值参考**

从feature文件中提取所有分类值（菜系、季节、口味等），与categories.md对比：
- 值是否在参考列表中
- 是否有遗漏的值

- [ ] **Step 5: 写入审计报告并提交**

```bash
git add docs/superpowers/audit/10-cross-reference-audit.md
git commit -m "audit: 交叉引用一致性检查报告"
```

---

### Task 11: 汇总与优先级排序

**Files:**
- Read: `docs/superpowers/audit/01-routing-audit.md` 到 `10-cross-reference-audit.md`
- Create: `docs/superpowers/audit/11-final-audit-report.md`

**Dependencies:** Tasks 1-10 must be completed first

- [ ] **Step 1: 收集所有故障清单**

读取任务1-10的所有审计报告，提取所有故障项。

- [ ] **Step 2: 去重和分类**

- 合并重复的故障
- 按严重程度分类：P0/P1/P2/P3
- 按功能模块分类

- [ ] **Step 3: 优先级排序**

按以下优先级排序：
1. P0-阻塞（功能完全无法执行）
2. P1-严重（主流程有明显缺陷）
3. P2-中等（边界情况处理不当）
4. P3-轻微（体验问题，不影响功能）

- [ ] **Step 4: 生成最终审计报告**

写入 `docs/superpowers/audit/11-final-audit-report.md`，格式：

```markdown
# 私家大厨技能 - AI执行者工作流审计报告

> 审计日期：2026-05-23
> 审计范围：7个功能模块，16条功能测试路径 + 10条路由测试用例
> 审计方法：AI执行者视角全流程推演

## 执行摘要

- 总发现：X个故障
- P0-阻塞：X个
- P1-严重：X个
- P2-中等：X个
- P3-轻微：X个

## P0-阻塞（必须修复）

### [P0-1] 故障标题
...

## P1-严重（应该修复）

### [P1-1] 故障标题
...

## P2-中等（建议修复）

### [P2-1] 故障标题
...

## P3-轻微（可以优化）

### [P3-1] 故障标题
...

## 修复建议优先级

1. 先修P0，确保功能可用
2. 再修P1，保证主流程正确
3. 最后处理P2/P3，提升体验
```

- [ ] **Step 5: 提交最终报告**

```bash
git add docs/superpowers/audit/11-final-audit-report.md
git commit -m "audit: 最终审计报告汇总"
```

---

## 执行说明

**并行性**：
- 任务1-8互相独立，可并行执行
- 任务9-10依赖任务2-8的结果
- 任务11依赖任务1-10的结果

**每个任务的执行者**：
1. 读取指定文件
2. 按步骤逐一检查
3. 记录所有发现的故障
4. 写入审计报告
5. 提交到git

**故障严重程度参考**：
| 级别 | 判断标准 |
|------|---------|
| P0-阻塞 | AI执行者走到某一步时完全无法继续（路径不存在、命令报错） |
| P1-严重 | AI执行者能继续但结果错误（路由匹配错误、参数格式错误） |
| P2-中等 | 特定输入下出现问题（边界情况、特殊字符） |
| P3-轻微 | 不影响功能但体验不好（格式不一致、提示不清晰） |
