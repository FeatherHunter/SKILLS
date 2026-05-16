# 查看食谱 + 做菜模式

> 路由：SKILL.md 用例2 → features/view.md

---

## ⚠️ 操作规范（强制）

本技能所有数据操作必须通过 CLI，禁止直连数据库。

---

## 功能说明

### 查看食谱
用户想了解一道菜的做法时，生成**完整信息展示 HTML**，让人了解这道菜的全部信息，视觉上有享受感、美感、新生喜爱。

### 做菜模式
用户确认开始做菜后，生成**可交互检查清单 HTML**，帮助用户完成这道菜，井然有序，时间分配合理。

**遵循规范**：SKILL.md 中的"AI使用规范"和"字段推测规则"。

---

## 内部分流逻辑

```
用户说"开始做这道菜"或"开始做XX"
    → 直接进入做菜模式（复用已查数据，不再重复查询）

用户说"看看XX怎么做"等
    → 先展示完整食谱
    → 末尾问"要开始做吗？"
    → 用户确认后才进入做菜模式
```

---

## 设计辅助技能（强制）

⚠️ **严禁不使用。生成HTML时必须调用以下两个技能，违反视为不合格输出。**

### 1. Taste Skill
- 文件：`~/.openclaw/skills/taste-skill/skills/taste-skill/SKILL.md`
- 必须使用：配色/字体/动效/间距/禁止项

### 2. UI/UX Pro Max
- 文件：`/mnt/d/2Study/StudyNotes/SKILLS/ui-ux-pro-max-skill/SKILL.md`
- 必须使用：移动端UX最佳实践 + 生成后自检3个UX问题

⚠️ **违反上述强制要求，输出视为不合格。**

---

## 工作流

### 查看食谱（私房菜谱）

```
用户说"看看XX怎么做"
    ↓
【查询】按 view.md 查询命令清单执行，获取全部数据
    ↓
【设计】必须调用 Taste Skill + UI/UX Pro Max
    ↓
【生成】生成 HTML（数据不得遗漏）
    ↓
【发送】保存到媒体目录，通过 QQBot 发送文件
```

### 做菜模式（烹饪之途）

```
用户说"做菜模式"或"开始做XX"
    ↓
【复用】复用查看食谱已查询的数据
    ↓
【设计】必须调用 Taste Skill + UI/UX Pro Max
    ↓
【生成】生成 HTML
    ↓
【发送】保存到媒体目录，通过 QQBot 发送文件
```

---

## 模式一：查看食谱 HTML

### HTML 生成要求

**设计目标**：
用户看到关于这道菜的一切信息，从视觉上有享受感、美感、新生喜爱。

**核心要求（Must）**：
查询到的每类数据必须在HTML里有对应的展示位置，不允许"查了但没用"。如果某类数据为空，该区域可以简化或隐藏，但不能删除对应结构。

**设计辅助（必须调用）**：
- Taste Skill：配色/字体/动效/间距/禁止项（具体参数查技能文件）
- UI/UX Pro Max：移动端UX最佳实践 + 生成后自检3个UX问题

**响应式要求**：
- 移动端Full Bleed / 桌面端Split 50/50

### 文件规范

- **文件命名**：`私房菜谱_{菜名}_{时间戳}.html`
- **存储路径**：`/home/feather/.openclaw/media/qqbot/`

---

## 模式二：做菜模式 HTML

### HTML 生成要求

**设计目标**：
帮助用户完成这道菜，井然有序，时间分配合理。

**核心约束（Must）**：

| # | 约束 | 说明 |
|---|------|------|
| 1 | 线性步骤 | 步骤按顺序1→2→3→...执行，不能跳过 |
| 2 | 依赖检查 | 如果下一步必须依赖当前步骤的结果，则不能继续（AI需判断） |
| 3 | 等待步骤可并发 | 当前步骤是等待型（如炖30分钟），完成后启动计时器，用户可以去处理其他步骤 |
| 4 | 多步并行等待 | 可以同时有多个等待步骤（如烤箱30分钟 + 炖汤30分钟同时跑），各计时器独立互不干扰 |
| 5 | 到期高亮提醒 | 等待步骤时间到了，页面内高亮显示"可以继续了"，用户切回页面时一眼能看到 |
| 6 | 断点续做 | localStorage记录所有步骤状态，刷新/关闭后回来能接着做 |
| 7 | 兼容性 | 兼容移动端和桌面端 |

**禁止项**：
- 不能实现"页面关闭后推送浏览器通知"（HTML文件无后端，无法后台推送）
- 不能跳过线性步骤（除非AI判断某步骤允许并行）

**设计辅助（必须调用）**：
- Taste Skill：深色主题（厨房强光场景）/ 大触摸目标 / 高对比度文字
- UI/UX Pro Max：厨房场景UX最佳实践 + 生成后自检3个UX问题

### 文件规范

- **文件命名**：`烹饪之途_{菜名}_{时间戳}.html`
- **存储路径**：`/home/feather/.openclaw/media/qqbot/`

---

## 查询逻辑（两模式共用）

1. 先通过菜名查 `recipes` 表获取 `recipe_id`
2. 用 `recipe_id` 查所有关联表
3. 做菜模式直接复用上述数据，不再查库
4. 如果某字段为空，显示为"未知"或"-"

---

## 命令参考

```bash
# 查看食谱详情
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
python scripts/step_ingredient_manager.py list-by-ingredient <ingredient_id>

# 步骤
python scripts/step_manager.py list <recipe_id>
python scripts/technique_manager.py list-by-step <step_id>
python scripts/step_ingredient_manager.py list-by-step <step_id>

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

---

## 参考

- 分类参考：`references/categories.md`
- 命令行参考：`references/commands.md`
- 表结构：`references/database_schema.md`
- Taste Skill：`~/.openclaw/skills/taste-skill/skills/taste-skill/SKILL.md`
- UI/UX Pro Max：`/mnt/d/2Study/StudyNotes/SKILLS/ui-ux-pro-max-skill/SKILL.md`