# P2 查看食谱走查报告

> 审计日期：2026-05-23
> 测试路径："看看宫保虾球怎么做"
> 审计方法：AI执行者视角全流程推演

---

## 流程概要

```
用户输入"看看宫保虾球怎么做"
    → 路由匹配：P2"看看"触发词 → 菜名"宫保虾球"
    → 加载 view.md → 功能一：查看食谱
    → 【查询】执行18条CLI命令获取全部数据
    → 【设计】读取 Taste Skill + UI/UX Pro Max
    → 【生成】生成完整信息展示HTML
    → 【发送】保存到媒体目录，通过QQBot发送
```

---

## Step 1：路由匹配

| 项目 | 值 |
|------|-----|
| 用户输入 | "看看宫保虾球怎么做" |
| 触发词 | "看看"（P2优先级） |
| 提取菜名 | "宫保虾球"（去掉触发词和"怎么做"后缀） |
| 路由目标 | view.md → 功能一：查看食谱 |

**路由匹配结果**：正确。SKILL.md第87行确认"看看"为P2触发词，示例第183行确认"看看宫保虾球怎么做"→"宫保虾球"。

**发现问题**：菜名提取规则不完整，详见故障F01。

---

## Step 2：查询命令清单推演

### 命令清单（view.md第284-323行）

以AI执行者视角，按依赖顺序执行：

**Batch 1（无依赖，可并行）**：

| # | 命令 | 返回数据 | 数据类别 |
|---|------|---------|---------|
| 1 | `python scripts/recipe_manager.py show 宫保虾球` | recipe_id + 基本信息 | 食谱基本信息 |
| 2 | `python scripts/category_manager.py list <recipe_id>` | 菜系/地区/国家 | 分类 |
| 3 | `python scripts/season_manager.py list <recipe_id>` | 季节 | 分类 |
| 4 | `python scripts/cooking_method_manager.py list <recipe_id>` | 烹饪方式 | 分类 |
| 5 | `python scripts/flavor_manager.py list <recipe_id>` | 口味 | 分类 |
| 6 | `python scripts/diet_tag_manager.py list <recipe_id>` | 饮食标签 | 分类 |
| 7 | `python scripts/meal_type_manager.py list <recipe_id>` | 用餐类型 | 分类 |
| 8 | `python scripts/cookware_manager.py list <recipe_id>` | 炊具 | 炊具 |
| 9 | `python scripts/ingredient_manager.py list <recipe_id>` | 食材清单 | 食材 |
| 10 | `python scripts/step_manager.py list <recipe_id>` | 步骤列表 | 步骤 |
| 11 | `python scripts/tip_manager.py list <recipe_id>` | 小贴士 | 小贴士 |
| 12 | `python scripts/history_manager.py list <recipe_id>` | 烹饪历史 | 历史 |
| 13 | `python scripts/background_manager.py get <recipe_id>` | 背景知识 | 背景 |
| 14 | `python scripts/relation_manager.py list-parent <recipe_id>` | 父食谱 | 派生关系 |
| 15 | `python scripts/relation_manager.py list-child <recipe_id>` | 子食谱 | 派生关系 |
| 16 | `python scripts/nutrition_manager.py get <recipe_id>` | 营养信息 | 营养 |

**Batch 2（依赖Batch 1的ingredient_id）**：

| # | 命令 | 依赖 | 返回数据 |
|---|------|------|---------|
| 17 | `python scripts/step_ingredient_manager.py list-by-ingredient <ingredient_id>` | 需要从#9获取每个ingredient_id | 食材在哪些步骤中使用 |

**Batch 3（依赖Batch 1的step_id）**：

| # | 命令 | 依赖 | 返回数据 |
|---|------|------|---------|
| 18 | `python scripts/technique_manager.py list-by-step <step_id>` | 需要从#10获取每个step_id | 步骤技法 |
| 19 | `python scripts/step_ingredient_manager.py list-by-step <step_id>` | 需要从#10获取每个step_id | 步骤中使用的食材 |

### 查询命令分析结果

**查询完整性**：18条命令覆盖全部17张表，查询完整。

**查询顺序问题**：view.md未说明查询顺序，也未说明Batch 2/3对Batch 1的依赖关系。AI执行者需要自行推断依赖，详见故障F02。

**参数格式**：所有命令格式与commands.md一致，参数正确。

---

## Step 3：外部技能调用推演

### Taste Skill

view.md第43-46行要求：
> 目录：`~/.openclaw/skills/taste-skill/SKILL.md`
> AI加载此文件后，必须先用 read 工具读取完整内容，再开始生成HTML

**实际验证**：
- view.md引用路径：`~/.openclaw/skills/taste-skill/SKILL.md`
- view.md底部参考路径：`/mnt/d/2Study/StudyNotes/SKILLS/taste-skill/skills/taste-skill/SKILL.md`
- 实际文件路径：`D:/2Study/StudyNotes/SKILLS/taste-skill/skills/taste-skill/SKILL.md`
- 文件存在性：已验证存在

**问题**：两处路径引用格式不一致，且均非标准Windows路径。详见故障F03。

### UI/UX Pro Max

view.md第48-51行要求：
> 目录：`~/.openclaw/skills/ui-ux-pro-max/SKILL.md`
> AI加载此文件后，必须先用 read 工具读取完整内容，再开始生成HTML

**实际验证**：
- view.md引用路径：`~/.openclaw/skills/ui-ux-pro-max/SKILL.md`
- view.md底部参考路径：`/mnt/d/2Study/StudyNotes/SKILLS/ui-ux-pro-max-skill/.claude/skills/ui-ux-pro-max/SKILL.md`
- 实际文件路径：`D:/2Study/StudyNotes/SKILLS/ui-ux-pro-max-skill/.claude/skills/ui-ux-pro-max/SKILL.md`
- 文件存在性：已验证存在

**问题**：路径引用格式不一致，且view.md正文中的路径缺少`.claude`层级。详见故障F04。

---

## Step 4：HTML生成核心要求检查

### 数据类别 vs HTML展示要求

view.md第97-98行核心要求：
> 查询到的每类数据必须在HTML里有对应的展示位置，不允许"查了但没用"。如果某类数据为空，该区域可以简化或隐藏，但不能删除对应结构。

**查询了16类数据**：

| # | 数据类别 | 来源表 | HTML是否有明确展示要求 |
|---|---------|--------|---------------------|
| 1 | 食谱基本信息 | recipes | 无 |
| 2 | 菜系/地区/国家 | recipe_categories | 无 |
| 3 | 季节 | recipe_seasons | 无 |
| 4 | 烹饪方式 | recipe_cooking_methods | 无 |
| 5 | 口味 | recipe_flavors | 无 |
| 6 | 饮食标签 | recipe_diet_tags | 无 |
| 7 | 用餐类型 | recipe_meal_types | 无 |
| 8 | 炊具 | cookware | 无 |
| 9 | 食材清单 | ingredients | 无 |
| 10 | 步骤×食材关联 | step_ingredients | 无 |
| 11 | 烹饪步骤 | cooking_steps | 无 |
| 12 | 步骤技法 | step_techniques | 无 |
| 13 | 小贴士 | tips | 无 |
| 14 | 烹饪历史 | recipe_history | 无 |
| 15 | 背景知识 | background_knowledge | 无 |
| 16 | 派生关系 | recipe_relations | 无 |
| 17 | 营养信息 | nutrition_info | 无 |

**结论**：view.md只给出了抽象的"每类数据必须有对应展示位置"要求，但没有指定HTML应包含哪些section、section的布局、优先级或视觉层次。AI执行者需要自行设计16+个section的HTML结构。详见故障F05。

### 响应式要求

view.md第100-101行：
> 移动端 Full Bleed / 桌面端 Split 50/50

**问题**：未定义断点（如768px），未说明哪些section使用Split布局，AI需自行判断。详见故障F06。

---

## Step 5：内部分流逻辑检查

### 分流定义（view.md第27-35行）

```
用户说"开始做这道菜"或"开始做XX"
    → 直接进入做菜模式（复用已查数据，不再重复查询）

用户说"看看XX怎么做"等
    → 先展示完整食谱
    → 末尾问"要开始做吗？"
    → 用户确认后才进入做菜模式
```

### 检查结果

**意图判断**：清晰。SKILL.md已定义P1触发词（"开始做"等）和P2触发词（"看看"等），不会混淆。

**数据复用问题**：view.md说"复用已查数据，不再重复查询"，但未说明数据如何跨轮次保持。详见故障F07。

---

## 发现的故障

### [P2-1] F01：菜名提取规则不完整

- **位置**：SKILL.md:41-42
- **现象**：规则说"触发词后面的内容 → 去掉空格 → 剩余文字"。对于"看看宫保虾球怎么做"，提取结果为"宫保虾球怎么做"（含"怎么做"后缀），但预期菜名是"宫保虾球"。
- **复现路径**："看看宫保虾球怎么做" → 触发词"看看" → 剩余"宫保虾球怎么做" → 应为"宫保虾球"
- **影响范围**：所有含动作后缀的用户输入（"怎么做"、"做法"、"步骤"等），P2/P3/P5/P6均受影响
- **修复建议**：在菜名提取规则中增加后缀清洗逻辑，列出常见后缀词（"怎么做"、"做法"、"步骤"、"菜谱"等），提取菜名时去除这些后缀

---

### [P2-2] F02：查询命令清单缺少执行顺序和依赖说明

- **位置**：view.md:284-323
- **现象**：命令参考仅列出18条命令，但未说明执行顺序。其中step_ingredient_manager.list-by-ingredient依赖ingredient_manager.list返回的ingredient_id，technique_manager.list-by-step和step_ingredient_manager.list-by-step依赖step_manager.list返回的step_id。如果AI按文档顺序从上到下执行，会在没有ID的情况下调用这些命令。
- **复现路径**：AI按view.md命令清单顺序执行 → 执行到step_ingredient_manager.list-by-ingredient时没有ingredient_id → 命令失败
- **影响范围**：查看食谱和做菜模式共用此命令清单，两个功能均受影响
- **修复建议**：将命令清单改为分组形式，标注依赖关系：
  ```
  第1组（无依赖）：recipe_manager show, category/season/method/flavor/diet/meal list, cookware list, ingredient list, step list, tip list, history list, background get, relation list-parent/child, nutrition get
  第2组（依赖ingredient_id）：step_ingredient_manager list-by-ingredient（对每个ingredient_id执行）
  第3组（依赖step_id）：technique_manager list-by-step, step_ingredient_manager list-by-step（对每个step_id执行）
  ```

---

### [P2-3] F03：Taste Skill路径引用不一致

- **位置**：view.md:44 和 view.md:332
- **现象**：view.md正文引用`~/.openclaw/skills/taste-skill/SKILL.md`，底部参考引用`/mnt/d/2Study/StudyNotes/SKILLS/taste-skill/skills/taste-skill/SKILL.md`。两处路径格式不同，且`~/.openclaw`是Linux Home路径，在Windows环境下不保证可解析。
- **复现路径**：AI读取view.md → 看到`~/.openclaw/skills/taste-skill/SKILL.md` → 尝试读取 → Windows下`~`可能解析为`C:/Users/王辰浩` → 路径不存在 → 技能加载失败
- **影响范围**：查看食谱和做菜模式的HTML生成阶段
- **修复建议**：统一使用相对于项目根目录的路径，或使用`D:/2Study/StudyNotes/SKILLS/taste-skill/skills/taste-skill/SKILL.md`。建议同时保留两处引用（正文用`~/.openclaw`，参考用绝对路径），并在正文中注明Windows环境下的等效路径

---

### [P2-4] F04：UI/UX Pro Max路径引用不一致且正文路径缺少层级

- **位置**：view.md:49 和 view.md:333
- **现象**：
  1. 正文引用`~/.openclaw/skills/ui-ux-pro-max/SKILL.md`（缺少`.claude`层级）
  2. 底部参考引用`/mnt/d/2Study/StudyNotes/SKILLS/ui-ux-pro-max-skill/.claude/skills/ui-ux-pro-max/SKILL.md`
  3. 实际路径包含`.claude`目录：`D:/2Study/StudyNotes/SKILLS/ui-ux-pro-max-skill/.claude/skills/ui-ux-pro-max/SKILL.md`
- **复现路径**：AI读取view.md正文 → 看到`~/.openclaw/skills/ui-ux-pro-max/SKILL.md` → 即使`~/.openclaw`能解析，该路径也缺少`.claude`层级 → 文件不存在
- **影响范围**：查看食谱和做菜模式的HTML生成阶段
- **修复建议**：修正正文路径为`~/.openclaw/skills/ui-ux-pro-max/.claude/skills/ui-ux-pro-max/SKILL.md`，或统一使用底部参考的绝对路径

---

### [P2-5] F05：HTML生成缺少具体的section结构定义

- **位置**：view.md:90-107
- **现象**：核心要求说"查询到的每类数据必须在HTML里有对应的展示位置"，但未定义HTML应包含哪些section、section的排列顺序、视觉优先级。AI需要自行设计16+个数据类别的HTML展示结构，可能导致：(a) 不同次生成的HTML结构差异大；(b) 次要信息（如派生关系）和核心信息（如食材、步骤）视觉权重相同；(c) AI可能遗漏某些类别。
- **复现路径**：AI查询完16类数据 → 准备生成HTML → 没有section模板 → 自行设计 → 可能遗漏或布局不合理
- **影响范围**：所有查看食谱功能的HTML输出质量
- **修复建议**：在view.md中定义HTML section模板，至少包括：
  ```
  必须section：菜名标题、成品图、基本信息（难度/时间/份量）、食材清单、烹饪步骤、小贴士
  推荐section：分类标签（菜系/口味/烹饪方式等）、炊具、营养信息、背景知识
  可选section：烹饪历史、派生关系
  空数据处理：section保留但显示"暂无数据"或隐藏
  ```

---

### [P2-6] F06：响应式断点和布局规则不具体

- **位置**：view.md:100-101
- **现象**：要求"移动端 Full Bleed / 桌面端 Split 50/50"，但未定义：(a) 断点值（如768px）；(b) 哪些section使用Split布局；(c) Full Bleed的具体含义（全宽图片？全宽卡片？）
- **复现路径**：AI生成HTML → 不知道断点值 → 可能用768px也可能用1024px → 不一致
- **影响范围**：HTML在不同设备上的显示效果
- **修复建议**：补充明确的断点值和布局规则，如：
  ```
  断点：768px
  移动端（<768px）：单列Full Bleed布局
  桌面端（>=768px）：左右Split 50/50（左侧：图片+基本信息，右侧：食材+步骤）
  ```

---

### [P2-7] F07：查看→做菜模式切换时数据复用机制未定义

- **位置**：view.md:27-35
- **现象**：内部分流说"开始做这道菜→直接进入做菜模式（复用已查数据，不再重复查询）"，但未说明数据如何跨轮次保持。在QQBot对话场景中，每次交互是独立的HTTP请求，AI不会自动保留上一轮的查询结果。
- **复现路径**：
  1. 用户："看看宫保虾球怎么做" → AI查询16类数据 → 生成HTML → 发送
  2. 用户："开始做这道菜" → AI进入做菜模式 → 需要复用数据 → 但数据已丢失 → 需要重新查询
- **影响范围**：从查看模式切换到做菜模式的用户体验（需要重新等待查询）
- **修复建议**：两种方案：
  1. 明确说明做菜模式在无预先数据时需要执行完整查询（修改"不再重复查询"的描述）
  2. 定义数据缓存机制（如将查询结果保存为临时文件）

---

### [P2-8] F08：文件命名时间戳格式未定义

- **位置**：view.md:105
- **现象**：文件命名规范为`私房菜谱_{菜名}_{时间戳}.html`，但未定义时间戳格式（YYYYMMDD_HHmmss？ISO 8601？Unix timestamp？）
- **复现路径**：AI生成文件名 → 不知道时间戳格式 → 可能用`私房菜谱_宫保虾球_20260523_143022.html`也可能用`私房菜谱_宫保虾球_1748001022.html`
- **影响范围**：文件管理和QQBot发送
- **修复建议**：明确时间戳格式，建议`YYYYMMDD_HHmmss`（如`私房菜谱_宫保虾球_20260523_143022.html`）

---

### [P2-9] F09：缺少食谱不存在时的处理逻辑

- **位置**：view.md:60-72
- **现象**：工作流假设"宫保虾球"存在于数据库中，但未说明如果recipe_manager.py show返回空或报错时AI应如何处理
- **复现路径**：用户："看看红烧狮子头怎么做" → AI执行`recipe_manager.py show 红烧狮子头` → 食谱不存在 → 无处理指引
- **影响范围**：所有查看食谱场景中菜名不存在的情况
- **修复建议**：在工作流中增加错误处理步骤：
  ```
  如果 recipe_manager.py show 返回"未找到"：
    → 告知用户"未找到该食谱"
    → 询问"是否要录入这道菜？"（引导到P7录入食谱）
  ```

---

### [P2-10] F10：view.md文档存在重复行

- **位置**：view.md:249+255 和 view.md:268+269
- **现象**：
  1. "已到期等待步骤（高亮）"在等待面板设计规范中重复出现（第249行和第255行）
  2. 存储路径`/home/feather/.openclaw/media/qqbot/`重复出现（第268行和第269行）
- **复现路径**：AI读取view.md → 解析等待面板规范 → 可能对重复条目产生困惑
- **影响范围**：文档质量，不影响功能执行（属于做菜模式部分，不影响查看食谱）
- **修复建议**：删除重复行

---

### [P2-11] F11：外部技能加载失败时无降级方案

- **位置**：view.md:39-54
- **现象**：view.md说"生成 HTML 时必须调用以下两个技能，违反视为不合格输出"，但未说明如果技能文件读取失败（路径不存在、权限不足等）时AI应如何处理。按当前描述，AI会因为无法读取技能文件而完全无法生成HTML。
- **复现路径**：AI尝试读取Taste Skill → 路径解析失败 → 无法继续 → 功能完全阻塞
- **影响范围**：所有需要生成HTML的功能（查看食谱+做菜模式）
- **修复建议**：增加降级方案：
  ```
  如果技能文件读取失败：
    → 记录警告
    → 使用内置的基础设计规则生成HTML
    → 在输出中注明"未加载设计技能，使用基础样式"
  ```

---

## 故障汇总

| # | 严重程度 | 故障ID | 标题 | 影响范围 |
|---|---------|--------|------|---------|
| 1 | P2-中等 | F01 | 菜名提取规则不完整 | 所有含动作后缀的输入 |
| 2 | P2-中等 | F02 | 查询命令清单缺少执行顺序和依赖说明 | 查看食谱+做菜模式 |
| 3 | P2-中等 | F03 | Taste Skill路径引用不一致 | HTML生成阶段 |
| 4 | P2-中等 | F04 | UI/UX Pro Max路径引用不一致且正文路径缺少层级 | HTML生成阶段 |
| 5 | P2-中等 | F05 | HTML生成缺少具体的section结构定义 | HTML输出质量 |
| 6 | P2-中等 | F06 | 响应式断点和布局规则不具体 | HTML多设备显示 |
| 7 | P2-中等 | F07 | 查看→做菜模式切换时数据复用机制未定义 | 模式切换体验 |
| 8 | P3-轻微 | F08 | 文件命名时间戳格式未定义 | 文件管理 |
| 9 | P2-中等 | F09 | 缺少食谱不存在时的处理逻辑 | 边界场景 |
| 10 | P3-轻微 | F10 | view.md文档存在重复行 | 文档质量 |
| 11 | P2-中等 | F11 | 外部技能加载失败时无降级方案 | HTML生成容错 |

**总计**：11个故障
- P0-阻塞：0个
- P1-严重：0个
- P2-中等：8个
- P3-轻微：2个（另有1个归入做菜模式）

---

## 审计结论

P2查看食谱的主流程（路由→查询→生成→发送）逻辑清晰，查询命令清单覆盖全部17张表，查询完整性无问题。主要问题集中在：

1. **查询执行顺序**：命令清单未标注依赖关系，AI可能在缺少中间ID的情况下调用依赖命令
2. **外部技能路径**：两处引用格式不一致，在Windows环境下可能导致路径解析失败
3. **HTML生成规范**：核心要求过于抽象，缺少具体的section模板和布局规则
4. **错误处理**：未定义食谱不存在、技能加载失败等边界情况的处理方案

这些问题不会导致功能完全不可用（无P0），但会影响输出质量和一致性（多个P2）。

---

## 修复建议优先级

1. **F02**：补充查询命令的依赖关系和执行顺序 → 消除执行错误风险
2. **F03+F04**：统一外部技能路径引用 → 消除路径解析失败风险
3. **F05**：定义HTML section模板 → 提升输出质量和一致性
4. **F09**：增加食谱不存在时的处理逻辑 → 完善边界场景
5. **F11**：增加外部技能加载失败的降级方案 → 提升容错能力
6. **F01**：完善菜名提取规则 → 提升路由准确性
7. **F07**：明确数据复用机制 → 改善模式切换体验
8. **F06+F08+F10**：细节完善 → 提升文档质量
