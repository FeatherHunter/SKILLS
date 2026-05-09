---
name: 居家管家
description: 家庭物品管理系统。当用户提到"居家管家"、查找物品（"找XX""XX在哪""有没有XX""XX还有多少"）、录入物品、盘点、推荐穿搭、整理物品时必须使用此技能。所有物品操作通过Python CLI执行数据库读写，AI负责解析自然语言和交互确认。
---

# 居家管家 v1.0

## 功能概述

- **物品录入**：自然语言描述物品，AI 解析后写入数据库
- **物品查找**：按名称/位置/标签/分类/状态搜索
- **物品更新**：位置变动、状态变更、数量调整、标签修改
- **物品盘点**：按需盘点指定位置的所有物品
- **穿搭推荐**：根据天气+标签推荐今日穿搭
- **旅游归位**：出门带物+回家归位的完整流程
- **频率统计**：区分高频/低频物品，识别长期未用物品

## 目录结构

```
居家管家/
├── SKILL.md
├── home.db                          # SQLite 数据库
├── photos/                          # 物品照片目录
├── scripts/
│   └── home_manager.py              # CLI 工具
└── references/
    ├── categories.md                # 28大类分类参考
    └── statuses.md                  # 10种状态值参考
```

## 数据库结构

### 表1：items（物品表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键自增 |
| name | TEXT | 物品名称 |
| category | TEXT | 大类（参考 references/categories.md） |
| location | TEXT | 存放位置（路径格式，当前实际位置） |
| owner | TEXT | 所有者（默认"使用者"） |
| status | TEXT | 状态（参考 references/statuses.md） |
| quantity | INTEGER | 数量（默认1） |
| purchase_price | REAL | 单价（元/件），按单瓶/单袋/单盒记，方便计算当前库存价值 |
| purchase_date | TEXT | 购买日期（YYYY-MM-DD格式，可空） |
| expiration_date | TEXT | 过期日期（YYYY-MM-DD格式，可空，用于食品/化妆品） |
| remark | TEXT | 备注 |
| photo | TEXT | 图片路径 |
| access_count | INTEGER | 被访问次数 |
| last_accessed_at | TIMESTAMP | 最后访问时间 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

### 表2：item_tags（标签表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键自增 |
| item_id | INTEGER | 关联 items.id |
| tag | TEXT | 单个标签 |

- 同一物品同一标签不可重复（UNIQUE约束）
- 多个物品可以有相同标签
- 搜索用精确匹配

### 表3：locations（位置历史表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键自增 |
| location_path | TEXT UNIQUE | 位置路径 |
| use_count | INTEGER | 使用次数 |
| last_used | TIMESTAMP | 最后使用时间 |

- 录入/更新物品位置时自动记录
- AI 从中智能提示用户用过的位置

---

## ⚠️ 核心使用原则

1. **任何写操作前必须交互确认**：AI 先展示将要执行的操作，用户说"对"才执行
2. **多物品冲突时让用户选**：搜到多个同名物品，列出来让用户选，不默认选任何一个
3. **物品只增不删，可修改**：物品不会物理删除，数量最小为0。quantity=0 自动标记"已用完"，"已废弃"需用户明确表态
4. **location = 当前实际位置**：物品长期放公司就更新为公司地址，不保留旧位置

---

## 使用流程

### Step 1：判断用户意图

AI 按以下层级判断操作类型，路由到对应功能模块：

**第1层 — 显式触发：** 用户以"居家管家"开头 → 进入「功能模块一：物品录入」

**第2层 — 场景关键词：**

| 用户说 | 进入 |
|--------|------|
| "找XX""XX在哪""有没有XX""XX还有多少""还剩多少XX""有多少XX" | 功能模块二：物品查找 |
| "XX换位置了""把XX放到XX""XX借给""XX坏了""XX用完了""XX吃了""XX扔了" | 功能模块三：物品更新 |
| "盘点XX""整理一下XX" | 功能模块四：物品盘点 |
| "今天穿什么""推荐穿搭" | 功能模块五：穿搭推荐 |
| "带XX出去旅游""旅游回来了" | 功能模块六：旅游归位 |
| "高频物品""长期没碰的""物品统计" | 功能模块七：频率统计 |
| "标签合并""整理标签" | 功能模块八：标签管理 |

---

## 功能模块一：物品录入

### Step 1: 解析用户描述
- AI 从用户自然语言中提取：名称、分类、位置、数量、标签、备注
- 对照 `references/categories.md` 推断分类，不确定则询问
- 对照 `references/statuses.md` 确认状态（默认"在家"）

### Step 2: 补全缺失字段
- AI 一句话问完所有缺失信息 —— 模板：
  ```
  收到，先记个草稿 📝

  {name} ｜ {category}

  再补充几点就好：
  · 它放在哪儿？（**必须至少两级路径，如`客厅/冰箱`、`厨房/灶台`**，不允许只写"客厅"）
  · 谁的？（不说就默认「使用者」）
  · 数量有几件/包？（不说就默认 1）
  · 花了多少钱？（没记就跳过）
  · 什么时候买的？（大概日期就行，跳过也可以）
  · 会过期吗？（食品/化妆品类才需要，写个大概日期）
  · 贴几个标签方便以后找？（比如颜色、品牌、季节）
  · 有没有备注想留的？（没有就跳过）

  一口气告诉我就行 👇
  ```
- 原则：缺什么问什么，不问已经给过的
- **必需字段 name/category/location 必须全部确认**
- **location 路径规则**：必须至少包含两级（如 `客厅/冰箱`，`厨房/灶台`），不允许单级位置（如只写"客厅"或"卧室"）。AI 在询问位置时需提醒用户必须细化到至少第二级。

### Step 3: 确认并写入
- AI 展示完整记录，用户说"对"后执行：
  ```bash
  python workspace/skills/居家管家/scripts/home_manager.py add \
    --name "薯片" --category "食品" --location "厨房/上柜/左侧" \
    --quantity 3 --tags "零食,乐事,原味"
  ```

### Step 4: 展示结果
- AI 展示脚本输出的录入结果

### Step 5: 提示录入图片
- AI 主动询问用户是否需要为此物品录入图片，模板：
  ```
  物品已录入成功（ID: {物品ID}）。
  是否需要为此物品添加图片？发给我图片即可，或回复"不用"跳过。
  ```
- 用户选择跳过 → 结束录入流程
- 用户发送图片 → 进入「图片录入子流程」

**图片录入子流程：**
```
Step A: 先添加物品（不带 photo）→ 得到 ID
Step B: AI 保存图片到 photos/{物品ID}_{名称}.jpg
Step C: update --id {ID} --photo "photos/{ID}_{名称}.jpg"
```

---

## 功能模块二：物品查找

### Step 1: 解析搜索条件
- AI 从用户输入提取：名称关键词、位置片段、标签、分类、状态
- 示例："找卧室里白色的T恤" → `--name "T恤" --tag "白色" --location "卧室"`
- "黑色的杯子" → `--name "杯子" --tag "黑色"`

### Step 2: 执行搜索
```bash
python workspace/skills/居家管家/scripts/home_manager.py search --name "T恤" --tag "白色"
```
支持组合搜索：`--location`, `--category`, `--status`, `--exact`

### Step 3: 处理结果
- **0 条** → 告知未找到，询问是否换个关键词或新建物品
- **1 条** → 直接展示
- **多条** → 列出让用户选择，选中后用 detail 查看详情：
  ```bash
  python workspace/skills/居家管家/scripts/home_manager.py detail --id {选中ID}
  ```

---

## 功能模块三：物品更新

### Step 1: 搜索目标物品
- AI 先搜索目标物品，确认是哪一个（多物品时让用户选）

### Step 2: 推断变更内容

**位置变更：**
- "放到客厅" → `--location "客厅/茶几"`

**状态变更（参考 `references/statuses.md`）：**
- "借给朋友" → `--status "借用中"`
- "坏了" → `--status "维修中"`
- "扔了/不要了" → `--status "已废弃"`

**数量变更：**
- "用完了" → `--quantity 0`（脚本自动标记"已用完"）
- "吃了1包/用了2个" → **先 search 查当前数量 → 计算新数量 → 展示确认** → `--quantity {新数量}`
- "还剩2包" → 直接 `--quantity 2`

### Step 3: 展示变更内容
- AI 列出将要改动的字段和值，请用户确认

### Step 4: 确认并执行
- 用户说"对" → 执行：
  ```bash
  python workspace/skills/居家管家/scripts/home_manager.py update --id 3 --status "借用中"
  ```
- AI 展示脚本输出的更新结果

**quantity=0 规则：**
- `--quantity 0` → 脚本自动将 status 设为"已用完"
- quantity>0 但用户说"废弃" → `--status "已废弃"`，quantity 保持原值

---

## 功能模块四：物品盘点

### Step 1: 查询位置
```bash
python workspace/skills/居家管家/scripts/home_manager.py inventory --location "卧室/衣柜"
```

### Step 2: 逐个确认
- AI 逐个列出物品，请用户确认状态是否正确

### Step 3: 用户说"XX变了"
- 进入「功能模块三：物品更新」处理

### Step 4: 盘点完成
- 用户说"都对" → 结束
- 中途退出：已确认的修改已写入，未确认的保持原样

---

## 功能模块五：穿搭推荐

### Step 1: 获取天气
- AI 尝试获取今日天气预报

### Step 2: 查询衣物
```bash
python workspace/skills/居家管家/scripts/home_manager.py list --category "衣物" --status "在家"
python workspace/skills/居家管家/scripts/home_manager.py list --category "鞋帽" --status "在家"
```

### Step 3: 筛选与推荐
- AI 根据温度+天气，通过 tags 匹配季节/材质/厚度

### Step 4: 展示推荐
- 不自动改状态，用户自行决定

**天气获取失败时：** 告知用户，纯列所有在家衣物

---

## 功能模块六：旅游归位

### 出门前

**Step 1:** 用户说"居家管家 我要带XX出去旅游"
**Step 2:** AI 搜索并确认要带哪些物品
**Step 3:** 用户确认 → 执行：
```bash
python workspace/skills/居家管家/scripts/home_manager.py update --id 5 --status "旅游中"
```

### 回家后

**Step 1:** 用户说"居家管家 旅游回来了"
**Step 2:** 查询所有"旅游中"物品：
```bash
python workspace/skills/居家管家/scripts/home_manager.py search --status "旅游中"
```
**Step 3:** 逐个询问："这东西放回原位还是换位置？"
**Step 4:** 用户逐一确认 → 更新 status="在家"，更新 location

---

## 功能模块七：频率统计

### Step 1: 选择统计类型
- "高频物品" → `frequent`
- "长期没碰" → `dormant`
- "物品统计" → `summary`

### Step 2: 执行统计
```bash
python workspace/skills/居家管家/scripts/home_manager.py stats --type frequent --limit 20
```

### Step 3: 展示结果
- AI 展示脚本输出

**访问计数规则：** 只有 `update`（明确操作）和 `detail`（明确查看）会增加计数。`search`/`list`/`inventory`（批量查询）不增加。

---

## 功能模块八：标签管理

### Step 1: 列出所有标签
```bash
python workspace/skills/居家管家/scripts/home_manager.py tag-list
```

### Step 2: 识别相似标签
- AI 识别字面高度重叠的标签对（如"白"和"白色"），告知用户

### Step 3: 确认并合并
- 用户确认 → 执行：
```bash
python workspace/skills/居家管家/scripts/home_manager.py tag-merge --from "白" --to "白色"
```

---

## 命令行参考

| 操作 | 命令模板 |
|------|---------|
| 初始化 | `python workspace/skills/居家管家/scripts/home_manager.py init` |
| 添加 | `python workspace/skills/居家管家/scripts/home_manager.py add --name "..." --category "..." --location "..." --tags "..."` |
| 搜索 | `python workspace/skills/居家管家/scripts/home_manager.py search --name "..." --location "..." --tag "..."` |
| 更新 | `python workspace/skills/居家管家/scripts/home_manager.py update --id N --status "..." --location "..."` |
| 列表 | `python workspace/skills/居家管家/scripts/home_manager.py list --location "..." --sort recent --limit 50` |
| 盘点 | `python workspace/skills/居家管家/scripts/home_manager.py inventory --location "..."` |
| 统计 | `python workspace/skills/居家管家/scripts/home_manager.py stats --type summary` |
| 标签合并 | `python workspace/skills/居家管家/scripts/home_manager.py tag-merge --from "A" --to "B"` |
| 标签列表 | `python workspace/skills/居家管家/scripts/home_manager.py tag-list` |
| 详情 | `python workspace/skills/居家管家/scripts/home_manager.py detail --id N` |

---

## 错误处理

| 场景 | AI 处理方式 |
|------|------------|
| 搜不到物品 | 告知用户，询问是否换个关键词或新建物品 |
| 搜到多个同名物品 | 列出让用户选择，不默认选任何一个 |
| 用户输入模糊无法解析 | 追问确认 |
| 数据库写入失败 | 告知用户失败原因，询问重试 |
| 首次使用（无数据库） | 脚本自动建表，无需手动操作 |
| 盘点中途退出 | 已确认的已写入，未确认的保持原样 |
| 穿搭推荐无匹配 | 告知无匹配衣物，建议扩展标签或录入 |
| 天气数据获取失败 | 告知无法获取天气，改用纯标签筛选 |
| 标签合并不存在 | 脚本输出"标签不存在"，AI 告知用户 |

---

## 高级配置

### 数据库路径查找顺序

1. **环境变量** `SKILLS_DB_PATH`（最高优先级）
   - 设置后所有技能db统一存放
   - 例：`export SKILLS_DB_PATH=/mnt/d/2Study/Notes/.db`

2. **技能所在目录**（默认）
   - 开箱即用，适合他人clone后直接使用

3. **父目录层层查找 `.db` 文件夹**
   - 适合集中管理多个技能的db文件
   - 脚本从技能目录向上搜索，找到 `.db` 目录为止

### 推荐做法

将db文件统一存放在 `~/.db/` 或项目根目录的 `.db/` 文件夹中：

```
D:\2Study\Notes\SKILLS\
├── .db\
│   ├── 居家管家.db
│   ├── 卡路里.db
│   └── 饼干记账.db
├── 居家管家\
├── 卡路里\
└── 饼干记账\
```

设置环境变量后，所有技能自动使用统一目录：

```bash
# Windows (WSL)
export SKILLS_DB_PATH=/mnt/d/2Study/Notes/.db

# Windows (PowerShell)
$env:SKILLS_DB_PATH="D:\2Study\Notes\.db"
```

---

## 联动说明

本技能可能与以下技能产生联动：

| 技能 | 可能的联动场景 |
|------|--------------|
| 饼干记账 | 购买物品时可同步记录支出金额 |
| 卡路里 | 购买食品时可同步记录营养成分（需用户提供营养数据） |

**处理原则**：在处理用户请求时，主动思考是否需要与上述技能联动。如判断需要联动，先完成主技能操作，再询问用户是否需要触发关联技能的相应功能。不要强制联动，尊重用户意图。

---

## Lint 检查（数据健康检查）

**触发词**：`"健康检查"`、`"检查数据"`、`"lint"`、`"数据审计"`

### 检查项

**1. 标签完整性**
- 物品是否缺少标签？标签太少（如少于2个）？
- 重要属性是否遗漏（如品牌、颜色、型号）？

**2. 表利用率**
- items 表：所有物品是否都有合理的分类、位置、状态？
- item_tags 表：是否有物品完全没有标签？
- locations 表：位置历史是否被充分利用？是否有相似位置未合并？

**3. 状态时效性**
- `快递中` 的物品是否超过合理时限未收到？是否忘了更新状态？
- `旅游中` 的物品是否长期未归位？
- `洗护中`、`维修中` 的物品是否处理完毕未更新？

**4. 位置规范性**
- 位置路径是否至少两级（如 `客厅/电视柜`）？
- 是否存在单级位置（如只有"客厅"）？

### 处理原则
- 发现问题后列出清单，让用户确认是否需要处理
- 不要自动修改，只能建议
- 用户说"检查一下"时执行，不主动触发
