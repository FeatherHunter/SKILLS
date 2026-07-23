---
name: 居家管家
description: >
  家庭物品全生命周期管理技能。当用户使用以下指令时触发：
  查物品、看物品（搜索/查看详情）、
  录物品、拍物品（文字录入/拍照录入）、
  改物品、移物品、补物品、减物品、标物品、废物品、借物品、修物品（更新类）、
  盘物品、盘全部（盘点）、
  穿什么（穿搭推荐）、
  带物品、归物品（旅游归位）、
  统物品、查高频、查低频（频率统计）、
  查过期（过期检查）、
  看标签、合标签（标签管理）、
  查快递（快递查询）、
  查账号、存账号、改账号（账号密码管理）、
  查异常（数据健康检查）。
  所有操作通过 Python CLI 执行数据库读写，AI 负责解析自然语言和交互确认；录物品/拍物品流程在写入前生成 HTML 预览供用户确认。
metadata: { "openclaw": { "emoji": "🏠", "requires": { "python": ">=3.7" } } }
---

**🔗 联动提示：** 完成本技能主操作后，检查技能路由器（`图片路由/SKILL.md`）的联动规则，判断是否需要联动其他技能（如用户提到物品价格→询问是否记录支出；物品是食品/饮料→询问是否记录卡路里）。详见路由器的联动规则表。

## ⚠️ HTML 同步规范（最高优先级）

> **此规范优先级高于本文件中所有其他规定。**

1. **全量同步**：该技能的所有优化和变动、脚本的所有变动都必须体现在 `居家管家.html` 上。任何功能模块的新增、修改、删除，任何唤醒词的调整，任何 CLI 命令的变化，任何脚本逻辑的改动——都必须同步更新 HTML 页面中对应的内容。
2. **最高优先级**：本条规定在所有规范中优先级最高。当其他流程或习惯与本条冲突时，以本条为准。
3. **逐行确认**：对该技能的所有文件、脚本的任何一行修改，都需要明确得到用户的 1 次确认后方可执行。不得批量静默修改，不得跳过确认步骤。

---

## ⚠️ 操作规范（强制）

本技能所有数据操作必须通过 CLI，禁止直连数据库。

---

## ⚠️ 分类命名规范（强制）

**所有写入 categories 表的 name 字段必须满足以下规则。违规会被 `category_manager.py` 拒收，不入库。**

### 规则

| # | 规则 | 违规示例 | 原因 |
|---|---|---|---|
| 1 | 非空,strip 后 1-30 字 | `""` / `"   "` | 占位/空白无意义 |
| 2 | **禁数字前缀** | `3. 家居` / `2 衣物` / `[1]数码` / `(2)图书` | DB id 137/138/205-210 已是天然编号,name 再加 = 双重编号 = 装饰 |
| 3 | 禁 emoji | `🎉 食物` | 装饰,破坏纯文本 |
| 4 | 同 parent 下 name 唯一 | 两个同名二级 | 防止 merge 漏掉产生歧义 |

### 第一性

- 数字编号是 **DB id 的事**,name 负责语义
- 8 顶级 name **统一不带前缀**:`食物与饮品` / `衣物与穿戴` / `家居与陈设` / `工具与器材` / `数码与电子` / `健康与医药` / `文体与娱乐` / `资产与凭证`
- 跨次加节点时,先看现有 name 风格,跟齐

### 实现位置

`scripts/category_manager.py` 的 `_validate_name(name, parent_name, conn)` 函数,被 `cmd_import` / 未来 `cmd_add` 调用。

---

## 路由表

AI 收到用户输入后，按以下表匹配唤醒词，命中即加载对应功能。

| # | 唤醒词 | 功能 | 加载文件 | 需要物品名？ |
|---|--------|------|----------|-------------|
| 1 | 查物品 | 物品搜索 | features/search.md | 可选（无则列全部） |
| 2 | 看物品 | 物品详情 | features/search.md → detail | 是（多件时让用户选） |
| 3 | 录物品 | 文字录入 | features/add.md | 否（AI 解析描述） |
| 4 | 拍物品 | 拍照录入 | features/add.md → 图片子流程 | 否（从图片提取） |
| 5 | 改物品 | 通用更新 | features/update.md | 是 |
| 6 | 移物品 | 位置移动 | features/update.md → 位置移动 | 是 |
| 7 | 补物品 | 数量增加 | features/update.md → 数量变更 | 是 |
| 8 | 减物品 | 数量减少 | features/update.md → 数量变更 | 是 |
| 9 | 标物品 | 标签更新 | features/update.md → 标签更新 | 是 |
| 10 | 废物品 | 标记废弃 | features/update.md → 状态变更 | 是 |
| 11 | 借物品 | 标记借出 | features/update.md → 状态变更 | 是 |
| 12 | 修物品 | 标记维修 | features/update.md → 状态变更 | 是 |
| 13 | 盘物品 | 按位置盘点 | features/inventory.md | 是（位置） |
| 14 | 盘全部 | 全屋盘点 | features/inventory.md | 否 |
| 15 | 穿什么 | 穿搭推荐 | features/fashion.md | 否 |
| 16 | 带物品 | 出门标记 | features/travel.md → 出门前 | 是 |
| 17 | 归物品 | 回家归位 | features/travel.md → 回家后 | 否（查所有旅游中） |
| 18 | 统物品 | 总体统计 | features/stats.md → summary | 否 |
| 19 | 查高频 | 高频物品 | features/stats.md → frequent | 否 |
| 20 | 查低频 | 低频物品 | features/stats.md → dormant | 否 |
| 21 | 查过期 | 过期检查 | features/stats.md → expiring | 否 |
| 22 | 看标签 | 列出标签 | features/tags.md → 列表 | 否 |
| 23 | 合标签 | 合并标签 | features/tags.md → 合并 | 是（from/to） |
| 24 | 查快递 | 快递查询 | features/search.md → 快递 | 否 |
| 25 | 推位置 | 位置推荐 | features/add.md → Step 2.5 | 是（category-id 整数） |
| 26 | 找位置 | 参考锚定 | features/add.md → Step 2.6 | 是（reference） |
| 27 | 查账号 | 查看账号 | accounts.py → show/list | 是（平台名，无则列全部） |
| 28 | 存账号 | 新增账号 | accounts.py → add | 是 |
| 29 | 改账号 | 更新账号 | accounts.py → show | 是（平台名） |
| 30 | 查异常 | 数据健康检查 | SKILL.md → Lint 检查 | 否 |
| 31 | 查物品 | 物品搜索（默认输出 HTML） | features/search.md → Step 4 | 可选（无则列全部） |
| 32 | 看物品 | 物品详情（默认输出 HTML） | features/search.md → Step 4 | 是（多件时先选） |
| 33 | 统物品 | 总体统计（默认输出 HTML） | features/search.md → Step 4 | 否 |

### 匹配规则

1. **精确匹配**：用户输入包含表中唤醒词即命中
2. **最长匹配**：同时命中多个时，取最长的（如"查高频"优先于"查"）
3. **物品名提取**：唤醒词前后的文字作为物品名/参数
4. **缺失物品名**：需要物品名但用户未提供时，追问

### 唤醒词 CLI 映射

| 唤醒词 | CLI 命令 |
|--------|---------|
| 查物品 | `search --name "XX"` 或 `search --location "XX"` 或 `search --tag "XX"` |
| 看物品 | `detail --id {ID}` |
| 录物品 | `add --name "XX" --category-id N --location "XX"` (category-id 必填,从 categories 表查) |
| 拍物品 | 先看图并保存到 `HOME_PHOTOS_DIR` → `add --name "XX" --category-id N --location "XX" --tags "...≥10" --remark "..." --photo "XX"` 一次写入 |
| 改物品 | `update --id {ID}` + 对应参数 |
| 移物品 | `update --id {ID} --new-location "新位置" --location "原位置"` |
| 补物品 | `update --id {ID} --plus N` |
| 减物品 | `update --id {ID} --minus N` |
| 标物品 | `update --id {ID} --tags "新标签"` |
| 废物品 | `update --id {ID} --location-status "已废弃"` |
| 借物品 | `update --id {ID} --location-status "借用中"` |
| 修物品 | `update --id {ID} --location-status "维修中"` |
| 盘物品 | `inventory --location "位置"` |
| 盘全部 | `list`（无筛选条件） |
| 穿什么 | `list --category-id 138 --status "在家"` (衣物顶级) + `list --category-id 148 --status "在家"` (鞋类二级) |
| 带物品 | `update --id {ID} --location-status "旅游中"` |
| 归物品 | `search --status "旅游中"` → 逐个 `update --id {ID} --location-status "在家"` |
| 统物品 | `stats --type summary` |
| 查高频 | `stats --type frequent --limit 20` |
| 查低频 | `stats --type dormant --limit 20` |
| 查过期 | `stats --type expiring [--days 30] [--expired-only] [--category-id N]` |
| 看标签 | `tag-list` |
| 合标签 | `tag-merge --from "旧" --to "新"` |
| 查快递 | `search --status "快递中"` |
| 推位置 | `suggest-locations --category-id N [--with-examples]` |
| 找位置 | `find-location --reference "XX"` |
| 查账号 | `account --action list` 或 `account --action show --platform "XX" --master-key "XX"` |
| 存账号 | `account --action add --platform "XX" --user "XX" --pass "XX" --master-key "XX"` |
| 改账号 | `account --action show --platform "XX" --master-key "XX"`（查看后重新录入） |
| 查异常 | 无 CLI，AI 执行 Lint 检查逻辑（见下方） |
| 查物品 | `search --name "XX"` 默认输出 HTML |
| 看物品 | `detail --id {ID}` 默认输出 HTML |
| 统物品 | `list` 默认输出 HTML |

---

## 安装与配置

**依赖**：Python 3.x

**环境变量**（可选）：
- `SKILLS_DB_PATH`：数据库目录
- `HOME_PHOTOS_DIR`：照片目录

**网页版**：[SkillBoard](https://featherhunter.github.io/StudyNotes/skillboard/) - 通过浏览器使用本系统，支持电脑和手机。使用时选择 `home.db` 文件即可。

**一键安装**：复制以下 prompt 给 AI：
```
帮我安装"居家管家"技能：
1. 检查 Python 环境
2. 引导我配置环境变量
3. 显示当前环境变量配置
4. 告诉我如何更改数据目录
```

---

## 功能概述

- **物品录入**：自然语言描述物品，AI 解析后写入数据库
- **物品查找**：按名称/位置/标签/分类/状态搜索
- **物品更新**：位置变动、状态变更、数量调整、标签修改
- **物品盘点**：按需盘点指定位置的所有物品
- **穿搭推荐**：根据天气+标签推荐今日穿搭
- **旅游归位**：出门带物+回家归位的完整流程
- **频率统计**：区分高频/低频物品，识别长期未用物品
- **标签管理**：合并相似标签
- **照片管理**：支持配置照片存储路径（环境变量 `HOME_PHOTOS_DIR`，默认为技能目录/photos）
- **🖼 单图架构**：一件物品 = 一张照片（`item.photo` 是单字段）。
  - **多图录入**：用户发多张图时，**第 1 张 = DB 主图（必须存 photos 目录）**，**后续图 = 只读不复制**（信息整合到 `tags` + `remark`，不再重复存档到文件系统）
  - **套装共享**：多件商品共用 1 张图时，每件复制一份并分别命名，各自 DB 存 1 个主图
  - **命名规范**：`YYYYMMDD_{ID}_{中文描述}.jpg`，无 `'` / `:` / `/` 等 Windows 非法字符；`add --photo` 会在内部拿到 ID 后复制为该规范名并写入 `item.photo`

## 快速导航

| 唤醒词 | 功能 | 参考文档 |
|--------|------|----------|
| 查物品 | 物品搜索 | features/search.md |
| 看物品 | 物品详情 | features/search.md |
| 录物品 | 物品录入 | features/add.md |
| 拍物品 | 拍照录入 | features/add.md |
| 改物品 | 通用更新 | features/update.md |
| 移物品 | 位置移动 | features/update.md |
| 补物品 | 数量增加 | features/update.md |
| 减物品 | 数量减少 | features/update.md |
| 标物品 | 标签更新 | features/update.md |
| 废物品 | 标记废弃 | features/update.md |
| 借物品 | 标记借出 | features/update.md |
| 修物品 | 标记维修 | features/update.md |
| 盘物品 | 按位置盘点 | features/inventory.md |
| 盘全部 | 全屋盘点 | features/inventory.md |
| 穿什么 | 穿搭推荐 | features/fashion.md |
| 带物品 | 出门标记 | features/travel.md |
| 归物品 | 回家归位 | features/travel.md |
| 统物品 | 总体统计 | features/stats.md |
| 查高频 | 高频物品 | features/stats.md |
| 查低频 | 低频物品 | features/stats.md |
| 查过期 | 过期检查 | features/stats.md |
| 看标签 | 列出标签 | features/tags.md |
| 合标签 | 合并标签 | features/tags.md |
| 查快递 | 快递查询 | features/search.md |
| 推位置 | 位置推荐 | features/add.md |
| 找位置 | 参考锚定 | features/add.md |
| 查账号 | 查看账号 | accounts.py |
| 存账号 | 新增账号 | accounts.py |
| 改账号 | 更新账号 | accounts.py |
| 查异常 | 数据健康检查 | SKILL.md（Lint 检查） |
| 查物品 | 物品搜索→HTML | features/search.md |
| 看物品 | 物品详情→HTML | features/search.md |
| 统物品 | 总体统计→HTML | features/search.md |

---

## ⚠️ 核心使用原则

1. **任何写操作前必须交互确认**：AI 先展示将要执行的操作，用户说"对"才执行
2. **多物品冲突时让用户选**：搜到多个同名物品，列出来让用户选，不默认选任何一个
3. **物品只增不删，可修改**：物品不会物理删除。item_locations 中 quantity=0 时自动删除该位置记录；位置状态为"已用完"或"已废弃"时需用户明确表态
4. **AI 不得自行推断**：当用户意图存在多种可能时，AI 必须询问确认，不得私自选择
5. **库存补充必须问**：搜索到名称相同的"已用完"或"已废弃"物品时，AI 必须询问用户是"补充到现有记录"还是"新建记录"，用户确认前不得写入数据库

---

## 联动说明

联动逻辑已集中到技能路由器（`图片路由/SKILL.md`），本技能不再单独维护联动规则。完成主操作后请检查路由器的联动规则表。

---

## Lint 检查（数据健康检查）

**唤醒词**：`查异常`

### 检查项

**1. 标签完整性**
- 物品是否缺少标签？标签太少（如少于2个）？
- 重要属性是否遗漏（如品牌、颜色、型号）？

**2. 表利用率**
- items 表：所有物品是否都有合理的分类、位置、状态？
- item_tags 表：是否有物品完全没有标签？
- item_locations 表：是否有相似位置路径未合并？（如 `卧室/东南角/小冰箱上/眼镜装扮抽屉` vs `卧室东南角/小冰箱上/眼镜装扮抽屉`）

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

---

## 错误处理

| 场景 | AI 处理方式 |
|------|------------|
| 搜不到物品 | 告知用户，询问是否换个关键词或新建物品 |
| 搜到多个同名物品 | 列出让用户选择，不默认选任何一个 |
| 录入时发现同名"已用完/已废弃"物品 | 列出选项让用户选择，不能自动决定 |
| 补充库存时原物品状态为"已用完/已废弃" | 询问用户新状态是什么（在家/备用/快递中/其他） |
| 用户输入模糊无法解析 | 追问确认 |
| 数据库写入失败 | 告知用户失败原因，询问重试 |
| 首次使用（无数据库） | 脚本自动建表，无需手动操作 |
| 盘点中途退出 | 已确认的已写入，未确认的保持原样 |
| 穿搭推荐无匹配 | 告知无匹配衣物，建议扩展标签或录入 |
| 天气数据获取失败 | 告知无法获取天气，改用纯标签筛选 |
| 标签合并不存在 | 脚本输出"标签不存在"，AI 告知用户 |
