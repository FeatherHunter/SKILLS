# 私家大厨 🍳

> 版本：v2.1
> 设计：基于17张表，6个核心用例，无删除操作

---

## ⚠️ 操作规范（强制）

本技能所有数据操作必须通过 CLI，禁止直连数据库。

---

## AI使用规范（强制）

### 调用任何manager前，必须：

1. **展示完整参数示例** — 让用户知道这条命令会用哪些参数
2. **对未提供字段进行合理推测** — 基于菜系特点/常见值/烹饪逻辑
3. **推测不出时询问用户** — 不能留空不填

### 字段推测规则

| 表/字段 | 推测规则 |
|---------|---------|
| recipes.description | 从菜名推断，如"经典川菜" |
| recipes.difficulty | 根据步骤复杂度/时间判断 |
| recipes.photo_url | 询问用户是否有照片 |
| recipes.source_url | 询问用户是否有链接 |
| ingredients.quantity_text | 用户说"适量"时填充，否则留空 |
| ingredients.is_optional | 用户明确说"可选"时设置1 |
| ingredients.substitute | 用户提到"可用XX代替"时填充 |
| ingredients.category | 根据食材名称推断（姜→蔬菜，虾→海鲜） |
| cooking_steps.temperature | 根据heat_level推断：中火≈160度，大火≈180-200度 |
| cooking_steps.expected_result | 根据步骤动作推测合理效果 |
| step_ingredients.quantity_used | 继承ingredients.quantity |
| step_ingredients.introduced_at | 根据步骤序号推断：开局/第X步加入 |

**无法推测时，必须询问用户。**

---

## 功能概览

| 用例 | 说明 |
|------|------|
| 录入食谱 | 一次性输入完整信息 |
| 查看食谱 | 完整信息展示 + 做菜模式 |
| 搜索筛选 | 按各种条件找菜 |
| 修改食谱 | 各部分增改+废弃（discard） |
| 烹饪历史 | 记录+评分+反馈 |
| 采购清单 | 生成清单+AI采购建议 |

---

## 路由表

AI 根据用户说的话，自动加载对应功能文件：

### 用例1：录入食谱
触发词：
- "录入一个新菜"
- "新建食谱"
- "添加一道菜"
- "我要收藏一个新菜"

→ `features/add.md`

---

### 用例2：查看食谱 + 做菜模式
触发词：
- "看看XX怎么做"
- "查看食谱"
- "菜谱详情"
- "XX的完整步骤"
- "开始做这道菜"
- "做菜模式"

→ `features/view.md`

---

### 用例3：搜索/筛选
触发词：
- "找川菜"
- "搜索排骨"
- "有哪些菜"
- "哪些用了虾"
- "过滤"
- "筛选"

→ `features/search.md`

---

### 用例4：修改食谱
触发词：
- "改一下"
- "更新"
- "修改"
- "第X步怎么改"
- "换个做法"
- "加个食材"
- "更新难度"

→ `features/update.md`

---

### 用例5：烹饪历史
触发词：
- "做了几次"
- "评分多少"
- "历史记录"
- "反馈"
- "复盘"
- "记录一下今天做的菜"

→ `features/history.md`

---

### 用例6：采购清单
触发词：
- "生成采购清单"
- "要买什么"
- "列出采购"
- "买什么"
- "准备食材"

→ `features/shopping.md`

---

## 快速导航

| 功能 | 参考文档 |
|------|----------|
| 录入食谱 | `features/add.md` |
| 查看食谱 + 做菜模式 | `features/view.md` |
| 搜索筛选 | `features/search.md` |
| 修改食谱 | `features/update.md` |
| 烹饪历史 | `features/history.md` |
| 采购清单 | `features/shopping.md` |
| 数据库结构 | `references/database_schema.md` |
| 分类参考 | `references/categories.md` |
| CLI命令 | `references/commands.md` |

---

## 核心原则

### 只增不删
- 没有物理删除操作
- 整道食谱废弃用 discard（status = '已废弃'），自动从列表/搜索中过滤
- 已废弃食谱可通过 show 查看简要信息

### 交互确认
- 所有写操作前必须展示，用户确认后执行
- 多选项时让用户选择，不默认

### 自然语言解析
- AI 负责解析用户意图，转换为 CLI 命令
- 信息不完整时追问，不猜测

---

## 表结构

共17张表，详见 `references/database_schema.md`

---

## 与其他技能联动

| 技能 | 联动场景 |
|------|---------|
| 卡路里 | 采购食品时可同步记录营养成分 |
| 居家管家 | 炊具借用/归位时参考 |

**处理原则**：主动思考是否需要联动，先完成主技能，再询问用户。