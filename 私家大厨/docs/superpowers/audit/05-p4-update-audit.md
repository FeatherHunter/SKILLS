# P4 修改食谱 - AI执行者工作流审计报告

> 审计日期：2026-05-23
> 审计范围：features/update.md + SKILL.md P4路由 + references/commands.md
> 审计方法：AI执行者视角，模拟3条修改路径的完整流程

---

## 一、修改功能概览

### 12种修改类型（命令参考覆盖）

| # | 修改对象 | manager脚本 | 操作类型 | 示例场景 |
|---|---------|------------|---------|---------|
| 1 | 食谱主表（recipes） | recipe_manager.py | update/discard | 改难度、改时间 |
| 2 | 分类标签（6个子表） | category_manager/season_manager/cooking_method_manager/flavor_manager/diet_tag_manager/meal_type_manager | add/update | 改菜系、加季节 |
| 3 | 食材（ingredients） | ingredient_manager.py | add/update | 加食材、改用量 |
| 4 | 步骤（cooking_steps） | step_manager.py | add/update/reorder | 改动作、调顺序 |
| 5 | 步骤x食材（step_ingredients） | step_ingredient_manager.py | add | 关联食材到步骤 |
| 6 | 技法（step_techniques） | technique_manager.py | add/update | 加技法 |
| 7 | 小贴士（tips） | tip_manager.py | add/update | 改优先级 |
| 8 | 背景知识（background_knowledge） | background_manager.py | update | 改故事 |
| 9 | 炊具（cookware） | cookware_manager.py | update | 改炊具 |
| 10 | 营养信息（nutrition_info） | nutrition_manager.py | update | 改热量 |
| 11 | 烹饪历史（recipe_history） | history_manager.py | update | 改评分 |
| 12 | 派生关系（recipe_relations） | relation_manager.py | update | 改关系类型 |

### 核心原则

- **只增不删**：没有物理删除操作
- **废弃用discard**：整道食谱废弃时 status 变为"已废弃"
- **写操作必须确认**：所有修改前展示对比，用户确认后执行

---

## 二、路径模拟与故障发现

### 路径1："把宫保虾球第2步改成小火"

#### 模拟流程

```
用户输入："把宫保虾球第2步改成小火"
    ↓
路由匹配：SKILL.md P4 触发词"改成" → 命中 → 菜名提取"宫保虾球"
    ↓
加载 features/update.md → 修改步骤示例
    ↓
AI需要执行：
  1. 获取 recipe_id（通过 recipe_manager.py show 宫保虾球）
  2. 获取 step_id（通过 step_manager.py list <recipe_id>，找到 sequence=2 的步骤）
  3. 展示修改前后对比
  4. 用户确认后执行：python scripts/step_manager.py update <step_id> --heat_level 小火
```

#### 发现的故障

### [P1-1] 修改步骤的前置查询流程未在update.md中说明

- **位置**：features/update.md:69-87（修改步骤示例）
- **现象**：示例中使用 `<step_id>` 作为占位符，但未说明AI如何获取step_id。示例假设AI已经知道step_id，但实际用户输入的是"第2步"（sequence number），不是step_id。
- **复现路径**：
  - 用户说"把宫保虾球第2步改成小火"
  - AI加载update.md，看到示例 `python scripts/step_manager.py update <step_id>`
  - AI不知道如何从"第2步"得到step_id
  - 需要先执行 `step_manager.py list <recipe_id>` 但update.md中没有这个前置步骤
- **影响范围**：所有涉及step_id、ingredient_id、tip_id等实体ID的修改操作
- **修复建议**：在update.md的"修改步骤"示例前增加前置查询说明：
  ```
  前置步骤：
  1. python scripts/recipe_manager.py show 宫保虾球 → 获取 recipe_id
  2. python scripts/step_manager.py list <recipe_id> → 获取第2步的 step_id
  ```

### [P1-2] recipe_id获取方式未在update.md中说明

- **位置**：features/update.md（全文）
- **现象**：所有命令都需要 recipe_id，但update.md没有说明如何从菜名获取 recipe_id。用户输入的是菜名"宫保虾球"，命令需要的是 recipe_id。
- **复现路径**：
  - 用户说"把宫保虾球的难度改成困难"
  - AI看到命令 `python scripts/recipe_manager.py update <recipe_id> --difficulty 困难`
  - AI需要先执行 `recipe_manager.py show 宫保虾球` 获取 recipe_id
  - 但update.md中没有这个前置步骤
- **影响范围**：所有修改操作
- **修复建议**：在update.md开头增加通用前置步骤说明

### [P2-1] step_manager.py list命令在update.md命令参考中缺失

- **位置**：features/update.md:186-332（命令参考部分）
- **现象**：命令参考只列出了写操作（add/update/reorder），没有列出读操作（list）。但AI要完成修改，必须先执行list来获取实体ID。
- **复现路径**：
  - AI读取update.md命令参考
  - 看到 `step_manager.py update <step_id>` 但没有 `step_manager.py list`
  - AI可能不知道可以/应该先执行list
- **影响范围**：步骤、食材、小贴士等所有需要ID的修改
- **修复建议**：在命令参考中增加必要的读操作命令，或在文档开头说明"修改前需要先查询，读命令见 commands.md"

---

### 路径2："给宫保虾球加一个食材，姜丝10g，在第4步加入"

#### 模拟流程

```
用户输入："给宫保虾球加一个食材，姜丝10g，在第4步加入"
    ↓
路由匹配：SKILL.md P4 触发词"加食材"/"加个食材" → 命中 → 菜名提取
    ↓
加载 features/update.md → 添加食材（含步骤关联）示例
    ↓
AI需要执行的多步操作：
  1. 获取 recipe_id → recipe_manager.py show 宫保虾球
  2. 添加食材 → ingredient_manager.py add <recipe_id> --name 姜丝 --quantity 10 --unit g --category 蔬菜
     → 获取返回的 ingredient_id
  3. 获取第4步的 step_id → step_manager.py list <recipe_id> → 找到 sequence=4
  4. 关联 → step_ingredient_manager.py add --step_id <第4步ID> --ingredient_id <ingredient_id> --quantity_used 10 --introduced_at "第4步加入"
```

#### 发现的故障

### [P1-3] 多步操作中中间ID获取流程不明确

- **位置**：features/update.md:89-109（添加食材含步骤关联）
- **现象**：示例标注了"假设返回 ingredient_id = xxx"，但没有说明：
  1. AI如何从CLI输出中解析 ingredient_id
  2. 如果第4步不存在怎么办（食谱只有3步）
  3. 如果添加食材失败，是否需要回滚
- **复现路径**：
  - 用户说"给宫保虾球加一个食材，姜丝10g，在第4步加入"
  - AI执行 ingredient_manager.py add
  - AI需要从命令输出中提取 ingredient_id
  - 文档没有说明输出格式是JSON还是纯文本
  - AI可能无法正确解析
- **影响范围**：所有需要中间ID的多步操作（添加食材+关联、添加步骤+关联等）
- **修复建议**：
  1. 说明CLI命令的输出格式（JSON？包含ID？）
  2. 增加错误处理说明（第4步不存在时怎么办）
  3. 增加"如果食谱没有第4步，询问用户是否要先添加步骤"

### [P2-2] 添加食材示例中缺少recipe_id参数

- **位置**：features/update.md:102-103
- **现象**：示例命令 `python scripts/ingredient_manager.py add <recipe_id>` 使用了 `<recipe_id>`，但commands.md中的完整参数说明也确认这是正确的。问题在于update.md没有说明如何获取recipe_id。
- **影响范围**：添加食材操作
- **修复建议**：在示例前增加"先通过 recipe_manager.py show 获取 recipe_id"

### [P2-3] step_ingredient_manager.py add 的输出格式未定义

- **位置**：features/update.md:106-108 及 references/commands.md:356-389
- **现象**：多步操作依赖从CLI输出中获取中间ID，但没有任何文档说明CLI命令的输出格式。
- **复现路径**：
  - AI执行 `ingredient_manager.py add <recipe_id> --name 姜丝 --quantity 10 --unit g --category 蔬菜`
  - AI需要从输出中获取 ingredient_id
  - 输出可能是："食材添加成功，ID: xxx" 或 JSON 或其他格式
  - AI不知道如何解析
- **影响范围**：所有需要中间ID的多步操作
- **修复建议**：在commands.md中为每个add命令定义标准输出格式，如：
  ```json
  {"success": true, "id": "xxx", "name": "姜丝"}
  ```

### [P3-1] "引入时机"推测规则与示例不一致

- **位置**：features/update.md:98 vs references/commands.md:832
- **现象**：
  - update.md示例中"在第4步加入"→ 引入时机为"开局加入"
  - commands.md推测规则："根据步骤序号推断：开局/第X步加入"
  - 用户明确说"在第4步加入"，推测规则应该用"第4步加入"而非"开局加入"
- **影响范围**：添加食材时引入时机的推测
- **修复建议**：update.md示例中的"开局加入"应改为"第4步加入"以匹配用户输入

---

### 路径3："不想要宫保虾球了"

#### 模拟流程

```
用户输入："不想要宫保虾球了"
    ↓
路由匹配：按优先级扫描触发词
  - P1 做菜模式：无命中
  - P2 查看食谱：无命中
  - P3 搜索筛选：无命中
  - P4 修改食谱：检查"改成"/"换成"/"加食材"/"加个食材"/"修改"/"难度" → 无命中
  - P5 烹饪历史：无命中
  - P6 采购清单：无命中
  - P7 录入食谱：无命中
  - 兜底：走 search.md
    ↓
结果：用户想废弃食谱，但被路由到搜索功能！
```

#### 发现的故障

### [P0-1] "不想要"不在P4触发词列表中，废弃食谱功能无法通过自然语言触发

- **位置**：SKILL.md:117-129（P4触发词列表）vs features/update.md:147（废弃示例）
- **现象**：
  - update.md第147行示例："用户：不想要宫保虾球了"→ 废弃食谱
  - 但SKILL.md P4触发词列表中没有"不想要"
  - P4触发词只有：`改成`、`换成`、`加食材`、`加个食材`、`修改`、`难度`
  - 用户说"不想要宫保虾球了"不会触发P4，会走兜底search.md
- **复现路径**：
  - 用户输入"不想要宫保虾球了"
  - AI按路由算法扫描触发词
  - 无任何P4触发词命中
  - 走兜底 → search.md
  - AI尝试搜索"不想要宫保虾球了"作为菜名
  - 搜索失败或返回无关结果
  - 用户的废弃意图完全丢失
- **影响范围**：废弃食谱功能完全不可用
- **修复建议**：在P4触发词列表中增加废弃相关触发词：
  ```
  | `不想要` | 后面跟菜名，如"不想要宫保虾球了" |
  | `废弃` | 后面跟菜名，如"废弃宫保虾球" |
  | `删掉` | 后面跟菜名，如"删掉宫保虾球"（引导到discard） |
  ```

### [P2-4] 废弃操作的触发词覆盖不全

- **位置**：SKILL.md:117-129
- **现象**：即使增加了"不想要"，用户可能使用的其他表达方式也未覆盖：
  - "宫保虾球不要了"
  - "把宫保虾球废了"
  - "宫保虾球删了吧"
  - "这个菜不用了"
- **影响范围**：废弃食谱的触发可靠性
- **修复建议**：增加多个废弃触发词，或在update.md中说明废弃操作的推荐触发词

---

## 三、写操作确认格式检查

### 格式定义

update.md第166-181行定义了确认格式：

```
AI：确认修改：

【修改前】
- 难度：中等
- 总时间：25分钟

【修改后】
- 难度：困难
- 总时间：30分钟

确认吗？说"对"执行。
```

### 发现的故障

### [P2-5] 确认格式缺少结构化多步操作的展示模板

- **位置**：features/update.md:166-181
- **现象**：确认格式只展示了简单的字段修改对比，但对于多步操作（如"添加食材+关联步骤"），没有展示模板。
- **复现路径**：
  - 用户说"给宫保虾球加一个食材，姜丝10g，在第4步加入"
  - AI需要展示确认信息
  - 应该展示什么？只有食材信息？还是食材+步骤关联？
  - 文档中只有简单字段的对比格式
- **影响范围**：所有多步操作的确认展示
- **修复建议**：增加多步操作的确认格式模板：
  ```
  AI：确认添加：

  【新食材】
  - 名称：姜丝
  - 用量：10g
  - 分类：蔬菜

  【步骤关联】
  - 关联步骤：第4步
  - 引入时机：第4步加入

  确认吗？说"对"执行。
  ```

### [P3-2] "说'对'执行"的确认词定义不够灵活

- **位置**：features/update.md:181
- **现象**：确认词固定为"对"，但用户可能说"好"、"确认"、"行"、"是的"等。
- **影响范围**：所有写操作的确认
- **修复建议**：在SKILL.md或update.md中说明可接受的确认词列表

---

## 四、其他发现

### [P2-6] update.md示例覆盖不完整

- **位置**：features/update.md:36-163（修改类型示例）
- **现象**：命令参考列出了12种修改类型的完整命令，但示例部分只覆盖了6种：
  - [x] 修改主信息（单字段）
  - [x] 修改主信息（多字段）
  - [x] 修改步骤
  - [x] 添加食材（含步骤关联）
  - [x] 调整步骤顺序
  - [x] 更新小贴士优先级
  - [x] 废弃食谱
  - [ ] 修改分类标签
  - [ ] 更新技法
  - [ ] 更新背景知识
  - [ ] 更新炊具
  - [ ] 更新营养信息
  - [ ] 更新烹饪历史
  - [ ] 更新派生关系
- **影响范围**：AI对未示例的修改类型可能不知道如何构造确认信息
- **修复建议**：为每种修改类型至少提供一个简短示例

### [P3-3] category_manager.py update 参数语义不一致

- **位置**：references/commands.md:129-133
- **现象**：`category_manager.py update <recipe_id>` 直接用 recipe_id，而其他manager（如step_manager、ingredient_manager）用实体自身的ID。这不是bug，但可能让AI混淆。
- **影响范围**：分类标签的修改操作
- **修复建议**：在update.md中明确说明"分类标签的update直接用recipe_id，不需要先查category_id"

---

## 五、故障汇总

| 编号 | 严重程度 | 故障标题 | 位置 |
|------|---------|---------|------|
| P0-1 | P0-阻塞 | "不想要"不在P4触发词列表中，废弃功能无法触发 | SKILL.md:117-129 |
| P1-1 | P1-严重 | 修改步骤的前置查询流程未说明 | update.md:69-87 |
| P1-2 | P1-严重 | recipe_id获取方式未说明 | update.md（全文） |
| P1-3 | P1-严重 | 多步操作中间ID获取流程不明确 | update.md:89-109 |
| P2-1 | P2-中等 | 读操作命令在update.md命令参考中缺失 | update.md:186-332 |
| P2-2 | P2-中等 | 添加食材示例缺少recipe_id获取说明 | update.md:102-103 |
| P2-3 | P2-中等 | CLI输出格式未定义，中间ID无法解析 | commands.md（全局） |
| P2-4 | P2-中等 | 废弃操作触发词覆盖不全 | SKILL.md:117-129 |
| P2-5 | P2-中等 | 确认格式缺少多步操作展示模板 | update.md:166-181 |
| P2-6 | P2-中等 | 示例覆盖不完整（12种只写了7种） | update.md:36-163 |
| P3-1 | P3-轻微 | "引入时机"推测与示例不一致 | update.md:98 |
| P3-2 | P3-轻微 | 确认词"对"不够灵活 | update.md:181 |
| P3-3 | P3-轻微 | category_manager参数语义与其他manager不一致 | commands.md:129-133 |

---

## 六、修复建议优先级

### 必须修复（P0）

1. **在P4触发词列表中增加废弃相关触发词**（SKILL.md:117-129）
   - 增加：`不想要`、`废弃`、`删掉`

### 应该修复（P1）

2. **在update.md开头增加通用前置步骤说明**
   - 说明如何从菜名获取 recipe_id
   - 说明如何从序号获取 step_id/ingredient_id

3. **为多步操作增加完整的流程说明**
   - 明确每步的输入输出
   - 说明CLI输出格式
   - 增加错误处理说明

### 建议修复（P2/P3）

4. 补充缺失的修改类型示例
5. 定义CLI命令标准输出格式
6. 增加多步操作的确认格式模板
7. 修正"引入时机"推测示例
8. 说明确认词的可接受范围

---

## 七、测试用例验证表

| # | 用户输入 | 预期路由 | 预期行为 | 实际路由 | 实际行为 | 结果 |
|---|---------|---------|---------|---------|---------|------|
| 1 | "把宫保虾球第2步改成小火" | P4 修改食谱 | 查询step_id→展示对比→确认→执行 | P4 | 需要前置查询但文档未说明 | 部分通过 |
| 2 | "给宫保虾球加一个食材，姜丝10g，在第4步加入" | P4 修改食谱 | 多步操作→确认→执行 | P4 | 中间ID获取流程不明确 | 部分通过 |
| 3 | "不想要宫保虾球了" | P4 修改食谱 | 废弃食谱→确认→执行 | P3 兜底搜索 | 被路由到搜索，废弃意图丢失 | 失败 |
| 4 | "把宫保虾球的难度改成困难" | P4 修改食谱 | 查询→对比→确认→执行 | P4 | 需要recipe_id但文档未说明获取方式 | 部分通过 |
| 5 | "宫保虾球第2步和第3步换一下" | P4 修改食谱 | 展示当前顺序→确认→执行 | P4 | reorder命令用recipe_id，流程清晰 | 通过 |

---

**审计结论**：P4修改食谱功能存在1个P0阻塞故障（废弃功能无法触发）和3个P1严重故障（前置查询流程缺失）。核心修改流程（改步骤、加食材）在AI执行者视角下缺少必要的前置步骤说明，可能导致AI无法正确构造CLI命令。建议优先修复P0和P1故障。
