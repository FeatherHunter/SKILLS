# 查看食谱 + 做菜模式

> 路由：SKILL.md 用例2 → features/view.md

---

## ⚠️ v5.0 架构变更（2026-07-10 实施）

从 v5.0 起，本技能 **HTML 生成统一由 `scripts/recipe_render.py` 负责**，AI 不再自己拼 HTML（根治 audit P0-5「做菜模式数据源缺失」）。

### 功能一：查看食谱 ✅ 已支持

一条命令搞定：

```bash
python scripts/recipe_render.py render <菜名或ID>
```

执行后：
- 数据从 `recipe_manager.py export-json` 拿（schema 完整对齐 `recipe_template.json`）
- 渲染走 Jinja2 + `templates/recipe_view.html`（Apple 风，浅色蓝重点，含 JS 折叠 + 份数切换）
- 输出到 `$CHEF_OUTPUT_DIR/recipes/<slug>.html`（尊重环境变量，默认 `output/`）

**AI 收到「查看食谱」请求的标准动作**：
1. 执行 `recipe_render.py render <菜名>`（如有冲突先 `recipe_manager.py show` 找菜）
2. 把生成的 HTML 文件路径告诉用户
3. （可选）根据用户偏好直接附图 / 发文件

### 功能二：做菜模式 ⚠️ 暂未支持

`recipe_render.py` 当前只服务「查看」场景。

**做菜模式**（逐步展开 / 计时器 / localStorage / 线性跳转）暂仍由 AI 自己生成 HTML，遵循下方「做菜模式」章节的全部规范（线性 + 不锁 / 等待型 / 计时器 / 断点续做等约束）。

等做菜模式专用模板上线后，统一迁移到 render.py。

---

## ⚠️ 操作规范（强制）

本技能所有数据操作必须通过 CLI，禁止直连数据库。

---

## 功能说明

### 功能一：查看食谱
用户想了解一道菜的做法时，AI 调 `recipe_render.py` 生成完整信息展示 HTML，让人了解这道菜的全部信息，视觉上有享受感、美感、新生喜爱。

### 功能二：做菜模式
用户确认开始做菜后，AI 生成可交互检查清单 HTML，帮助用户完成这道菜，井然有序，时间分配合理。

**遵循规范**：SKILL.md 中的"AI使用规范"和"字段推测规则"。

---

## 内部分流逻辑

```
用户说"开始做这道菜"或"开始做XX"
    → 进入做菜模式（暂由 AI 自己生成 HTML，详见下方）

用户说"看看XX怎么做" / "查看食谱XX" 等
    → AI 调 recipe_render.py render <菜名>
    → 输出 HTML 文件给用户
    → 末尾问"要开始做吗？"
    → 用户确认才进入做菜模式
```

---

## 工作流

### 功能一：查看食谱

```
用户说"看看XX怎么做"
    ↓
【查找菜】如有歧义，先 recipe_manager.py show 定位
    ↓
【渲染】recipe_render.py render <菜名或ID>
    ↓
【返回】把生成的 HTML 文件路径告诉用户
```

**禁止**：
- AI 自行拼接 HTML 字符串
- 调用 taste-skill / ui-ux-pro-max-skill（已废弃，统一由模板服务）
- 内联 CSS / JS（已统一在 `templates/recipe_view.html`）

### 功能二：做菜模式

```
用户说"做菜模式"或"开始做XX"
    ↓
【判断】是否有已查数据？
    有 → 复用已查数据
    无 → 按命令参考执行查询获取全部数据
    ↓
【设计】AI 自己生成 HTML（模板未上线前的过渡方案）
    ↓
【生成】生成 HTML
    ↓
【发送】保存到媒体目录，通过 QQBot 发送文件
```

---

## 功能一：查看食谱

### HTML 生成要求

**设计目标**：
用户看到关于这道菜的一切信息，从视觉上有享受感、美感、新生喜爱。

**核心要求（Must）**：
查询到的每类数据必须在HTML里有对应的展示位置，不允许"查了但没用"。如果某类数据为空，该区域可以简化或隐藏，但不能删除对应结构。

**响应式要求**：
- 断点：768px
- 移动端（<768px）：Full Bleed（全宽布局）
- 桌面端（≥768px）：Split 50/50（左右分栏）
- Split 布局适用于：成品照片+基本信息、食材清单+步骤列表

### HTML Section 模板

**必须 section**：
1. 菜名标题 + 副标题（描述）
2. 成品照片（如有）
3. 基本信息栏（难度/时间/份量/状态）
4. 分类标签（菜系/口味/季节/烹饪方式）
5. 食材清单（含用量、可选标记）
6. 烹饪步骤（含时间、火候、预期效果）

**推荐 section**：
7. 小贴士
8. 炊具清单
9. 营养信息
10. 背景知识（起源/历史/文化意义）

**可选 section**：
11. 烹饪历史
12. 派生关系

### 文件规范

- **文件命名**：`<slug>.html`（slugify 菜名，自动去除 Windows 非法字符）
- **存储路径**：`$CHEF_OUTPUT_DIR/recipes/`（默认 `output/recipes/`，尊重环境变量）
- **示例**：`宫保虾球.html` / `上海排骨年糕.html`

---

## 功能二：做菜模式

### 设计目标

帮助用户完成这道菜，井然有序，时间分配合理。充分发挥 HTML 互动性，让用户专注于做菜而非记忆步骤。

---

### 步骤类型定义

每步必须明确定义类型，用于依赖检查和并发逻辑：

| 类型 | 标识 | 说明 |
|------|------|------|
| **普通型** | `type: normal` | 完成后直接解锁下一步 |
| **等待型** | `type: wait` | 完成后启动计时器，用户可去做其他已解锁步骤 |

**自动推断规则**：
- 步骤描述含以下关键词 → 等待型：`炖`、`烤`、`焗`、`腌`、`卤`、`浸泡`、`醒`、`发酵`
- 其他情况 → 普通型

---

### 核心约束（Must）

| # | 约束 | 说明 |
|---|------|------|
| 1 | 线性+不锁 | 步骤按顺序完成才能进入下一步（不能跳）。但等待型步骤只启动计时器，不阻止后续步骤解锁 |
| 2 | 用户触发切换 | 完成当前步骤后，点"完成步骤→"手动触发跳转到下一步骤页 |
| 3 | 等待页样式 | 等待页显示倒计时，到期高亮提醒，用户可随时返回确认完成 |
| 4 | 顶部计时器固定区 | 所有进行中的计时器（最多4个）固定在页面顶部，超出横向滚动 |
| 5 | 并发等待 | 多个等待步骤可同时计时，各自独立 |
| 6 | 到期提醒 | 等待到期时提醒用户，左上角出现提示条 |
| 7 | 断点续做 | localStorage保存：当前页码、步骤完成状态、计时器开始时间戳 |
| 8 | 移动+桌面兼容 | 响应式布局，移动端44px最小触摸目标 |

**禁止项**：
- 不能实现浏览器通知（HTML无后端）
- 不能跳过线性步骤
- 不能在页面垂直方向一次性展示所有步骤（必须分页）
- 计时器超过4个时，后续排队不显示在顶部

**正向要求**：
- 必须每步独立页面（首页 → 步骤1 → 步骤2 → ... → 步骤N → 完成页），线性跳转，不能滚动
- 必须用户手动点"完成步骤→"触发跳转，不能自动滚动
- 顶部固定计时器区域，最多4个并行，超出排队不显示
- localStorage保存：当前页码、步骤完成状态、计时器开始时间戳，刷新后恢复
- 移动端44px最小触摸目标，响应式布局

---

## 新增约束（从实际bug中提取）

### Bug1：计时器恢复bug（9399:58）

**目标**：计时器断点续做正确，刷新后 remaining 计算精准

**约束（Must）**：
| # | 约束 | 说明 |
|---|------|------|
| T1 | 已有timer不重置 | `initStepTimer` 调用前必须检查 `state.timers[stepId]` 是否已存在，存在则不重置 startTime |
| T2 | 暂停状态保存remaining | paused 状态保存 `remaining` 值，重开时用 `startTime = Date.now() - (duration - remaining)` |
| T3 | 恢复后正确显示 | 刷新后每个计时器的 remaining 必须与关闭前一致 |

**禁止项**：
- `initStepTimer` 在已有 timer 时重新初始化 startTime
- 出现任何荒谬数值（如9399:58）

---

### Bug2：步骤页左上角返回键

**目标**：步骤页的返回不中断做菜流程，首页的返回才清进度

**约束（Must）**：
| # | 约束 | 说明 |
|---|------|------|
| R1 | 步骤页左上角只允许返回上一步或留在当前 | 点击行为：上一步未完成 → 提示"请先完成当前步骤"；上一步已完成 → 返回上一步 |
| R2 | "返回首页"仅限首页和完成页 | 步骤页禁止出现"返回首页"按钮或功能 |
| R3 | 步骤页左上角禁止清进度 | 不能因为点击左上角而清除已完成步骤的进度 |

**禁止项**：
- 步骤页左上角出现"返回首页"或"清进度"功能

---

### Bug3：首页体验

**目标**：首页干净，只做入口，不诱导跳步

**约束（Must）**：
| # | 约束 | 说明 |
|---|------|------|
| H1 | 首页仅展示必要信息 | 仅：菜名、总时间、份量、食材预览、开始按钮 — 不能有步骤列表或导航 |
| H2 | 首页禁止返回功能 | 首页不能有"返回"、"清进度"按钮（完成页才有） |
| H3 | 步骤列表独立Tab | 步骤列表必须通过底部Tab切换进入，不能在首页直接展示 |

**禁止项**：
- 首页嵌入步骤列表或"查看全部步骤"入口
- 首页有清进度、返回上一级等干扰功能

---

**页面流程**：
```
首页 → 步骤1 → 步骤2 → ... → 步骤N（最后一步完成）
                                          ↓
                               [ 完成！返回首页 ]
```

最后一步完成后显示完成提示 + "返回首页"按钮。点击返回首页清除进度，可重新开始。

---

### 依赖检查算法

canUnlock(step N):
```
    if step N-1 is not completed:
        return false  // 上一步未完成，不能进入步骤N
    return true  // 上一步完成，步骤N解锁
```

**等待型步骤特殊逻辑**：
等待型步骤启动计时器后即视为"已解锁后续步骤"，不阻止 step N+1 解锁。

---

### 计时器恢复算法

**正常情况**：
```
remaining = duration - (currentTimestamp - startTimestamp)
```

**暂停情况**：
```
remaining = savedRemaining（从 localStorage 读取暂停时保存的 remaining 值）
```

若 `remaining <= 0`，该步骤到期，触发高亮提醒。

---
### 等待面板（Wait Panel）设计规范

**必须展示**：
- 所有进行中的等待步骤（倒计时中）
- 已到期等待步骤（高亮）
- 已解锁的可操作步骤（用户可自由切换）

**视觉要求**：
- 多个计时器横向排列，滚动支持
- 到期计时器高亮并持续显示（直到用户确认）

---

### 到期提醒规范

计时器到期时，左上角出现提示条告知用户，与核心约束 #6 保持一致。具体样式由 AI 根据上下文自行决定。

### 时间戳格式

- **格式**：`YYYYMMDD_HHMMSS`（如 `20260523_143000`）


### 文件规范

- **文件命名**：`烹饪之途_{菜名}_{时间戳}.html`
- **存储路径**：`$CHEF_OUTPUT_DIR`（默认 `output/`）

---

## 查询逻辑（两模式共用）

1. 先通过菜名查 `recipes` 表获取 `recipe_id`
2. 用 `recipe_id` 查所有关联表
3. 做菜模式直接复用上述数据，不再查库
4. 如果某字段为空，显示为"未知"或"-"

### 错误处理

**食谱不存在**：
如果 `recipe_manager.py show` 返回"未找到食谱"，AI 应：
1. 告知用户"没有找到这道菜"
2. 询问是否要录入："要不要录入这道菜？说'录入'开始"

---

## 命令参考

### 查询命令（按依赖顺序）

**Batch 1：无依赖（直接用 recipe_id）**

```bash
# 获取 recipe_id（必须第一步执行）
python scripts/recipe_manager.py show <菜名或ID>

# 分类
python scripts/category_manager.py list <recipe_id>
python scripts/season_manager.py list <recipe_id>
python scripts/cooking_method_manager.py list <recipe_id>
python scripts/flavor_manager.py list <recipe_id>
python scripts/diet_tag_manager.py list <recipe_id>
python scripts/meal_type_manager.py list <recipe_id>

# 炊具
python scripts/cookware_manager.py list <recipe_id>

# 食材
python scripts/ingredient_manager.py list <recipe_id>

# 步骤
python scripts/step_manager.py list <recipe_id>

# 小贴士
python scripts/tip_manager.py list <recipe_id>

# 历史
python scripts/history_manager.py list <recipe_id>

# 背景
python scripts/background_manager.py get <recipe_id>

# 派生
python scripts/relation_manager.py list-parent <recipe_id>
python scripts/relation_manager.py list-child <recipe_id>

# 营养
python scripts/nutrition_manager.py get <recipe_id>
```

**Batch 2：依赖 ingredient_id（从 Batch 1 的 ingredient 结果获取）**

```python
python scripts/step_ingredient_manager.py list-by-ingredient <ingredient_id>
```

**Batch 3：依赖 step_id（从 Batch 1 的 step 结果获取）**

```python
python scripts/technique_manager.py list-by-step <step_id>
python scripts/step_ingredient_manager.py list-by-step <step_id>
```

### 做菜模式最小数据集

以下命令是做菜模式**必须执行**的（按顺序）：

```bash
# 1. 获取 recipe_id + 基本信息
python scripts/recipe_manager.py show <菜名>

# 2. 食材清单
python scripts/ingredient_manager.py list <recipe_id>

# 3. 步骤列表
python scripts/step_manager.py list <recipe_id>

# 4. 步骤×食材关联（需 step_id，从步骤列表获取）
python scripts/step_ingredient_manager.py list-by-step <step_id>

# 5. 技法（需 step_id，从步骤列表获取）
python scripts/technique_manager.py list-by-step <step_id>

# 6. 小贴士
python scripts/tip_manager.py list <recipe_id>
```

> 做菜模式优先保证上述 6 类数据完整，其余数据（分类/历史/背景等）有则展示、无则省略。

---

## 参考

- 分类参考：`references/categories.md`
- 命令行参考：`references/commands.md`
- 表结构：`references/database_schema.md`
- Taste Skill：调用 `taste-skill` 技能
- UI/UX Pro Max：调用 `ui-ux-pro-max-skill` 技能