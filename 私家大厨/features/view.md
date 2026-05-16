# 查看食谱 + 做菜模式

> 路由：SKILL.md 用例2 → features/view.md

---

## ⚠️ 操作规范（强制）

本技能所有数据操作必须通过 CLI，禁止直连数据库。

---

## 功能说明

### 功能一：查看食谱
用户想了解一道菜的做法时，生成**完整信息展示 HTML**，让人了解这道菜的全部信息，视觉上有享受感、美感、新生喜爱。

### 功能二：做菜模式
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

## 设计辅助技能（必须调用）

⚠️ **生成 HTML 时必须调用以下两个技能，违反视为不合格输出。**

### 1. Taste Skill
- 目录：`~/.openclaw/skills/taste-skill/SKILL.md`
- **AI加载此文件后，必须先用 read 工具读取完整内容，再开始生成HTML**
- 厨房场景适配：大触摸目标

### 2. UI/UX Pro Max
- 目录：`~/.openclaw/skills/ui-ux-pro-max/SKILL.md`
- **AI加载此文件后，必须先用 read 工具读取完整内容，再开始生成HTML**
- 必须使用：移动端UX最佳实践（44px触摸目标、8px间隔、对比度4.5:1）
- 生成后自检3个UX问题

⚠️ **违反上述强制要求，输出视为不合格。**

---

## 工作流

### 功能一：查看食谱（私房菜谱）

```
用户说"看看XX怎么做"
    ↓
【查询】按 view.md 查询命令清单执行，获取全部数据
    ↓
【设计】调用 Taste Skill + UI/UX Pro Max
    ↓
【生成】生成 HTML（数据不得遗漏）
    ↓
【发送】保存到媒体目录，通过 QQBot 发送文件
```

### 功能二：做菜模式（烹饪之途）

```
用户说"做菜模式"或"开始做XX"
    ↓
【复用】复用查看食谱已查询的数据
    ↓
【设计】调用 Taste Skill + UI/UX Pro Max
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
- 移动端 Full Bleed / 桌面端 Split 50/50

### 文件规范

- **文件命名**：`私房菜谱_{菜名}_{时间戳}.html`
- **存储路径**：`/home/feather/.openclaw/media/qqbot/`

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
| C2 | 线性+不锁 | 步骤按顺序完成才能进入下一步（不能跳）。但等待型步骤只启动计时器，不阻止后续步骤解锁 |
| C3 | 用户触发切换 | 完成当前步骤后，点"完成步骤→"手动触发跳转到下一步骤页 |
| C5 | 等待页样式 | 等待页显示倒计时，到期高亮提醒，用户可随时返回确认完成 |
| C6 | 顶部计时器固定区 | 所有进行中的计时器（最多4个）固定在页面顶部，超出横向滚动 |
| C7 | 并发等待 | 多个等待步骤可同时计时，各自独立 |
| C8 | 到期提醒 | 等待到期时提醒用户，左上角出现提示条 |
| C9 | 断点续做 | localStorage保存：当前页码、步骤完成状态、计时器开始时间戳 |
| C10 | 移动+桌面兼容 | 响应式布局，移动端44px最小触摸目标 |

**禁止项**：
- 不能实现浏览器通知（HTML无后端）
- 不能跳过线性步骤
- 不能在页面垂直方向一次性展示所有步骤（必须分页）
- 计时器超过4个时，后续排队不显示在顶部

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
    return true  // 上一步完成，步骤N解锁（等待型不锁后续）
```

---

### 计时器恢复算法

刷新页面后，按以下公式计算剩余时间：
```
remaining = duration - (currentTimestamp - startTimestamp)
```

若 `remaining <= 0`，该步骤到期，触发高亮提醒。

---
### 页面布局结构

**首页（第1页）**
```
┌─────────────────────────────────────────────┐
│  [← 退出]          菜名         [≡ 菜单]    │
├─────────────────────────────────────────────┤
│                                             │
│            菜品大图                          │
│                                             │
│         菜名 + 一句话描述                     │
│    难度 | 总时间 | 份量                       │
│                                             │
│          [ 开始烹饪 ]                       │
│                                             │
└─────────────────────────────────────────────┘
```

**步骤页（每步1页，顶部固定计时器区）**
```
┌─────────────────────────────────────────────┐
│  [← 首页]   步骤3/8   [⏰ 45:30] [⏰ 18:20] │ ← 顶部固定（计时器区）
├─────────────────────────────────────────────┤
│                                             │
│  步骤3：煎牛腩                              │
│  ┌─────────────────────────────────────┐   │
│  │  技法：煎                            │   │
│  │  投入食材：牛腩块 200g               │   │
│  │  小贴士：中火热锅，每面2分钟          │   │
│  │  状态：进行中                        │   │
│  └─────────────────────────────────────┘   │
│                                             │
│          [ ✓ 完成步骤 → ]                   │
│                                             │
└─────────────────────────────────────────────┘
```

**等待页（等待型步骤）**
```
┌─────────────────────────────────────────────┐
│  [← 首页]   步骤6/8   [⏰ 45:30] [⏰ 18:20] │ ← 顶部固定（计时器区）
├─────────────────────────────────────────────┤
│                                             │
│  步骤6：炖煮 30分钟                         │
│  ┌─────────────────────────────────────┐   │
│  │  等待中... 剩余 45:30               │   │
│  │  [ 取消等待 ]                        │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  已解锁的可操作步骤：                        │
│  [步骤4] [步骤5]                           │ ← 可提前做其他步骤
│                                             │
└─────────────────────────────────────────────┘
```

**最后一步完成**
```
┌─────────────────────────────────────────────┐
│  [← 首页]              🎉 完成了！            │
├─────────────────────────────────────────────┤
│                                             │
│         这道菜已完成，祝你用餐愉快！          │
│                                             │
│          [ 返回首页 ]                       │
│                                             │
└─────────────────────────────────────────────┘
```

**顶部计时器区规范**：
- 固定在页面顶部，不随步骤切换消失
- 最多显示4个计时器，超出横向滚动
**顶部计时器区规范**：
- 到期计时器高亮提醒，持续显示直到用户确认

### 等待面板（Wait Panel）设计规范

**必须展示**：
- 所有进行中的等待步骤（倒计时中）
- 已到期等待步骤（高亮）
- 已到期等待步骤（高亮）
- 已解锁的可操作步骤（用户可自由切换）

**视觉要求**：
- 多个计时器横向排列，滚动支持
- 到期计时器高亮并持续显示（直到用户确认）
- 到期计时器高亮并持续显示（直到用户确认）

---

### 到期提醒规范

计时器到期时，页面出现提示信息告知用户，具体样式由AI根据上下文自行决定。


### 文件规范

- **文件命名**：`烹饪之途_{菜名}_{时间戳}.html`
- **存储路径**：`/home/feather/.openclaw/media/qqbot/`

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
- Taste Skill：`/mnt/d/2Study/StudyNotes/SKILLS/taste-skill/skills/taste-skill/SKILL.md`
- UI/UX Pro Max：`/mnt/d/2Study/StudyNotes/SKILLS/ui-ux-pro-max-skill/.claude/skills/ui-ux-pro-max/SKILL.md`